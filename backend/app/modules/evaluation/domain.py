"""Outcomes, the evaluator interface and the rule types' evaluators. Pure: no database.

An evaluator has two steps. `gather` reads the facts it needs from the modules that own them and
returns them as plain JSON; `evaluate` is a pure function from those facts and the rule's params
to a verdict. A result stores the facts, so it can always be explained and an identical set of
facts is never judged twice. To add a rule type: declare it in policy's `RULE_TYPES`, write an
evaluator here and add it to `EVALUATORS`.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Any, Protocol

from app.modules.connectors.service import OldestRecord
from app.modules.inventory.service import AssetRetention, SubjectType
from app.modules.policy.service import AppliedControlRef


class Outcome(StrEnum):
    """`error` means the rule could not be evaluated, which says nothing about compliance: it is
    never counted as `fail`."""

    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    NOT_APPLICABLE = "not_applicable"


class Trigger(StrEnum):
    EVENT = "event"
    SCHEDULE = "schedule"
    ON_DEMAND = "on_demand"


class FactsUnavailableError(Exception):
    """The facts a rule needs could not be read. The message is safe to show to users and becomes
    the reason of an `error` result."""


@dataclass(frozen=True)
class Verdict:
    outcome: Outcome
    reason: str
    measured: float | None = None
    threshold: float | None = None
    unit: str | None = None


class FactReader(Protocol):
    """Everything an evaluator may read. The service builds one over the modules' interfaces."""

    def asset_retention(self, asset_id: uuid.UUID) -> AssetRetention | None: ...

    def oldest_record(self, asset_id: uuid.UUID) -> OldestRecord:
        """Raises `FactsUnavailableError` if the record cannot be read."""
        ...


class Evaluator(Protocol):
    rule_type: str
    subject_type: SubjectType
    # How long a result stays current before it is flagged stale.
    freshness: timedelta

    def gather(
        self, subject: AppliedControlRef, reader: FactReader, today: date
    ) -> dict[str, Any]: ...

    def evaluate(self, facts: dict[str, Any], params: dict[str, Any]) -> Verdict: ...


def fact_hash(facts: dict[str, Any]) -> str:
    """The identity of a set of facts: the same facts always give the same hash."""
    canonical = json.dumps(facts, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


# --- retention_window -------------------------------------------------------------------------


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


class RetentionWindow:
    """The oldest record of a stored asset's table is within the asset's retention policy.

    Facts: the asset's declared retention, and the oldest value of the table's creation date,
    read from the store through its read-only connection. The limit is the policy's days plus the
    rule's `grace_days`; the age is whole days from that record to the day of the evaluation.
    """

    rule_type = "retention_window"
    subject_type = SubjectType.ASSET
    freshness = timedelta(hours=48)

    def gather(self, subject: AppliedControlRef, reader: FactReader, today: date) -> dict[str, Any]:
        retention = reader.asset_retention(subject.subject_id)
        if retention is None:
            raise FactsUnavailableError("The asset no longer exists.")
        facts: dict[str, Any] = {
            "as_of": today.isoformat(),
            "asset": {"id": str(retention.asset_id), "name": retention.asset_name},
            "retention": {
                "is_stored": retention.is_stored,
                "policy_code": retention.policy_code,
                "policy_name": retention.policy_name,
                "days": retention.retention_days,
            },
            "table": None,
        }
        if not retention.is_stored or retention.retention_days is None:
            return facts
        record = reader.oldest_record(subject.subject_id)
        facts["table"] = {
            "data_store_id": str(record.data_store_id),
            "data_store": record.data_store_name,
            "harvest_snapshot_id": str(record.snapshot_id),
            "harvest_taken_at": _iso(record.snapshot_taken_at),
            "path": record.table_path,
            "column": record.column,
            "oldest_record_at": _iso(record.oldest_at),
        }
        return facts

    def evaluate(self, facts: dict[str, Any], params: dict[str, Any]) -> Verdict:
        retention, table = facts["retention"], facts["table"]
        if table is None:
            return Verdict(
                Outcome.NOT_APPLICABLE,
                "The asset is not stored or declares no retention policy, so there is no "
                "retention window to measure.",
            )
        days, grace = int(retention["days"]), int(params.get("grace_days", 0))
        limit = days + grace
        policy = f"{retention['policy_name']} ({days:,} days)"
        window = f"{policy} plus {grace:,} grace days" if grace else policy
        if table["oldest_record_at"] is None:
            return Verdict(
                Outcome.PASS,
                f"{table['path']} holds no records, so nothing is kept past {window}.",
                measured=0,
                threshold=limit,
                unit="days",
            )
        oldest = datetime.fromisoformat(table["oldest_record_at"])
        age = max((date.fromisoformat(facts["as_of"]) - oldest.date()).days, 0)
        subject = f"The oldest record in {table['path']} ({table['column']}, {oldest:%d %b %Y})"
        if age > limit:
            return Verdict(
                Outcome.FAIL,
                f"{subject} is {age:,} days old, {age - limit:,} days past the {window} "
                "retention window.",
                measured=age,
                threshold=limit,
                unit="days",
            )
        return Verdict(
            Outcome.PASS,
            f"{subject} is {age:,} days old, within the {window} retention window.",
            measured=age,
            threshold=limit,
            unit="days",
        )


EVALUATORS: dict[str, Evaluator] = {e.rule_type: e for e in (RetentionWindow(),)}
