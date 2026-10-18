"""Public interface of the evaluation module: the only file other modules import.

Evaluation reads applied controls from policy, the facts they need from the modules that own
them, and writes results. It runs as jobs: on an event (an applied control derived, a subject
changed, a harvest stored), on a schedule and on demand. A result is never updated or deleted;
an evaluation whose rule version and facts match the latest result writes nothing, so running it
again is harmless. `error` (the rule could not be evaluated) is a result of its own, not a fail.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.auth import Permission, Principal, Role, allowed_actions, require
from app.core.errors import InvalidInputError, NotFoundError, PermissionDeniedError
from app.core.jobs import Job, enqueue
from app.core.outbox import publish
from app.core.pagination import PageResult, decode_cursor, encode_cursor
from app.modules.audit.service import AuditService
from app.modules.connectors.service import ConnectorsService
from app.modules.evaluation.domain import (
    EVALUATORS,
    Evaluator,
    FactReader,
    FactsUnavailableError,
    Outcome,
    Trigger,
    Verdict,
    fact_hash,
)
from app.modules.evaluation.facts import ModuleFacts
from app.modules.evaluation.models import EvaluationResult
from app.modules.evaluation.repository import EvaluationRepository
from app.modules.evaluation.schemas import (
    EvaluationResultRead,
    ResultControl,
    ResultSubject,
)
from app.modules.inventory.service import SubjectType
from app.modules.policy.service import AppliedControlRef, PolicyService

logger = logging.getLogger(__name__)

RUN_EVALUATION = "evaluation.run"
"""Job kind: evaluate some applied controls (payload: `applied_control_ids`, `trigger`,
`requested_by`)."""
SWEEP_EVALUATION = "evaluation.sweep"
"""Job kind, on a schedule: queue an evaluation of every active applied control."""
RESULT_RECORDED = "evaluation.result_recorded"
"""Outbox event: a result was written. Payload: `result_id`, `applied_control_id`, `outcome`,
`transition`. Actions (slice 7) react to a failing result and to one that verifies a fix."""

SYSTEM_ACTOR = "system:evaluation"
BATCH_SIZE = 50

# Whoever answers for a subject may ask for it to be checked again.
_RUNNERS = {Role.GOVERNANCE, Role.DATA_OWNER, Role.APPLICATION_OWNER, Role.DATA_STEWARD}
RUN_EVALUATION_PERMISSION = Permission("run_evaluation", _RUNNERS)


@dataclass(frozen=True)
class RunSummary:
    run_id: uuid.UUID
    counts: dict[str, int]


def _now() -> datetime:
    """The clock for evaluations and freshness; tests replace it to fix the day."""
    return datetime.now(UTC)


def _transition(previous: EvaluationResult | None, outcome: Outcome) -> str:
    if previous is None:
        return "first"
    if previous.outcome == outcome.value:
        return "unchanged"
    return f"{previous.outcome}_to_{outcome.value}"


def _read(result: EvaluationResult, now: datetime) -> EvaluationResultRead:
    return EvaluationResultRead(
        id=result.id,
        applied_control_id=result.applied_control_id,
        control=ResultControl(
            id=result.control_id,
            code=result.control_code,
            rule_type=result.rule_type,
            rule_version=result.rule_version,
        ),
        subject=ResultSubject(
            type=SubjectType(result.subject_type), id=result.subject_id, name=result.subject_name
        ),
        outcome=Outcome(result.outcome),
        measured=float(result.measured) if result.measured is not None else None,
        threshold=float(result.threshold) if result.threshold is not None else None,
        unit=result.unit,
        reason=result.reason,
        facts=result.facts,
        evaluated_at=result.evaluated_at,
        stale_after=result.stale_after,
        is_stale=now >= result.stale_after,
        previous_result_id=result.previous_result_id,
        transition=result.transition,
        run_id=result.run_id,
    )


class EvaluationService:
    def __init__(
        self,
        session: Session,
        *,
        facts: FactReader | None = None,
        connectors: ConnectorsService | None = None,
        evaluators: dict[str, Evaluator] | None = None,
    ) -> None:
        self._session = session
        self._repository = EvaluationRepository(session)
        self._audit = AuditService(session)
        self._policy = PolicyService(session)
        self._connectors = connectors or ConnectorsService(session)
        self._facts = facts or ModuleFacts(session, self._connectors)
        self._evaluators = evaluators if evaluators is not None else EVALUATORS

    # --- Reading results

    def list_results(
        self,
        principal: Principal,
        *,
        limit: int,
        cursor: str | None,
        applied_control_id: uuid.UUID | None = None,
        control_id: uuid.UUID | None = None,
        subject_type: SubjectType | None = None,
        subject_id: uuid.UUID | None = None,
        outcome: Outcome | None = None,
        latest_only: bool = True,
    ) -> PageResult[EvaluationResultRead]:
        """A page of results on subjects in the caller's domains, newest first. By default one
        per applied control: its latest."""
        after = _decode_id_cursor(cursor) if cursor else None
        filters: dict[str, Any] = {
            "applied_control_id": applied_control_id,
            "control_id": control_id,
            "subject_type": subject_type.value if subject_type else None,
            "subject_id": subject_id,
            "outcome": outcome.value if outcome else None,
            "latest_only": latest_only,
            "scope": principal.domain_ids,
        }
        rows = self._repository.list_results(after=after, limit=limit + 1, **filters)
        items = rows[:limit]
        next_cursor = encode_cursor(str(items[-1].id)) if len(rows) > limit else None
        total = self._repository.count_results(**filters)
        now = _now()
        return PageResult(
            items=[_read(r, now) for r in items], next_cursor=next_cursor, total=total
        )

    def get_result(self, principal: Principal, result_id: uuid.UUID) -> EvaluationResultRead:
        result = self._repository.get(result_id)
        if result is None:
            raise NotFoundError(
                f"Result {result_id} does not exist.", details={"id": str(result_id)}
            )
        if not principal.in_scope(result.subject_domain_id):
            raise PermissionDeniedError(
                "This result is outside the domains you are scoped to.",
                details={"id": str(result_id)},
            )
        return _read(result, _now())

    def actions_for(
        self,
        principal: Principal,
        *,
        applied_control_id: uuid.UUID | None,
        subject_type: SubjectType | None,
        subject_id: uuid.UUID | None,
    ) -> list[str]:
        """`allowed_actions` of a list narrowed to one applied control or subject: whether the
        caller may run its evaluation. A wider list offers nothing."""
        if applied_control_id is None and (subject_type is None or subject_id is None):
            return []
        targets = self._targets(applied_control_id, subject_type, subject_id, must_exist=False)
        if not targets:
            return []
        return allowed_actions(principal, [RUN_EVALUATION_PERMISSION], targets[0].subject_domain_id)

    # --- Asking for an evaluation

    def request_evaluation(
        self,
        principal: Principal,
        *,
        applied_control_id: uuid.UUID | None = None,
        subject_type: SubjectType | None = None,
        subject_id: uuid.UUID | None = None,
    ) -> Job:
        """Queue an evaluation of one applied control, or of every control on a subject."""
        targets = self._targets(applied_control_id, subject_type, subject_id, must_exist=True)
        for target in targets:
            require(principal, RUN_EVALUATION_PERMISSION, target.subject_domain_id)
        job = enqueue(
            self._session,
            RUN_EVALUATION,
            {
                "applied_control_ids": [t.id for t in targets],
                "trigger": Trigger.ON_DEMAND,
                "requested_by": principal.actor,
            },
            created_by=principal.actor,
            max_attempts=3,
        )
        self._audit.record(
            actor=principal.actor,
            action="evaluation.requested",
            subject_type="applied_control" if applied_control_id else targets[0].subject_type.value,
            subject_id=applied_control_id or targets[0].subject_id,
            after={"job_id": job.id, "applied_controls": len(targets)},
        )
        return job

    def _targets(
        self,
        applied_control_id: uuid.UUID | None,
        subject_type: SubjectType | None,
        subject_id: uuid.UUID | None,
        *,
        must_exist: bool,
    ) -> list[AppliedControlRef]:
        if applied_control_id is not None:
            if subject_type is not None or subject_id is not None:
                raise InvalidInputError("Name an applied control or a subject, not both.")
            found = self._policy.find_applied_control(applied_control_id)
            if found is None or not found.is_active:
                if must_exist:
                    raise NotFoundError(
                        f"Applied control {applied_control_id} does not exist or no longer "
                        "applies.",
                        details={"id": str(applied_control_id)},
                    )
                return []
            return [found] if found.rule_type in self._evaluators else []
        if subject_type is None or subject_id is None:
            raise InvalidInputError("Name an applied control, or a subject type and id.")
        refs = [
            r
            for r in self._policy.active_applied_controls(
                subject_type=subject_type, subject_id=subject_id
            )
            if r.rule_type in self._evaluators
        ]
        if not refs and must_exist:
            raise NotFoundError(
                "No control with an evaluator applies to this subject.",
                details={"subject_type": subject_type.value, "subject_id": str(subject_id)},
            )
        return refs

    # --- For jobs and event handlers: acting for the system

    def enqueue_run(
        self, applied_control_ids: list[uuid.UUID], trigger: Trigger, *, idempotency_key: str
    ) -> Job | None:
        """Queue an evaluation for the system. Nothing to do queues nothing."""
        if not applied_control_ids:
            return None
        return enqueue(
            self._session,
            RUN_EVALUATION,
            {
                "applied_control_ids": applied_control_ids,
                "trigger": trigger,
                "requested_by": None,
            },
            max_attempts=3,
            idempotency_key=idempotency_key,
        )

    def sweep(self, *, job_id: uuid.UUID) -> int:
        """The scheduled pass: queue an evaluation of every active applied control, in batches.
        Keyed by the sweep's job, so a retried sweep queues each batch once."""
        ids = [
            r.id
            for rule_type in self._evaluators
            for r in self._policy.active_applied_controls(rule_type_key=rule_type)
        ]
        for start in range(0, len(ids), BATCH_SIZE):
            self.enqueue_run(
                ids[start : start + BATCH_SIZE],
                Trigger.SCHEDULE,
                idempotency_key=f"sweep:{job_id}:{start}",
            )
        return len(ids)

    def applied_control_ids_for_subject(
        self, subject_type: SubjectType, subject_id: uuid.UUID
    ) -> list[uuid.UUID]:
        return [
            r.id
            for r in self._policy.active_applied_controls(
                subject_type=subject_type, subject_id=subject_id
            )
            if r.rule_type in self._evaluators
        ]

    def applied_control_ids_for_store(self, data_store_id: uuid.UUID) -> list[uuid.UUID]:
        """The applied controls on assets that have a table in the store."""
        ids: list[uuid.UUID] = []
        for asset_id in self._connectors.asset_ids_in_store(data_store_id):
            ids += self.applied_control_ids_for_subject(SubjectType.ASSET, asset_id)
        return ids

    def run(
        self,
        applied_control_ids: list[uuid.UUID],
        trigger: Trigger,
        *,
        requested_by: str | None,
    ) -> RunSummary:
        """Evaluate applied controls and write the results that are new. One that cannot be
        evaluated gets an `error` result; one that fails unexpectedly does not stop the others."""
        now = _now()
        run = self._repository.add_run(trigger.value, requested_by)
        counts: dict[str, int] = {"looked_at": 0, "written": 0, "unchanged": 0, "skipped": 0}
        for applied_control_id in dict.fromkeys(applied_control_ids):
            counts["looked_at"] += 1
            applied = self._policy.find_applied_control(applied_control_id)
            evaluator = self._evaluators.get(applied.rule_type) if applied else None
            if applied is None or not applied.is_active or evaluator is None:
                counts["skipped"] += 1
                continue
            result = self._evaluate(applied, evaluator, run.id, now)
            if result is None:
                counts["unchanged"] += 1
            else:
                counts["written"] += 1
                counts[result.outcome] = counts.get(result.outcome, 0) + 1
        self._repository.finish_run(run, counts)
        return RunSummary(run.id, counts)

    def _evaluate(
        self, applied: AppliedControlRef, evaluator: Evaluator, run_id: uuid.UUID, now: datetime
    ) -> EvaluationResult | None:
        self._repository.lock_applied_control(applied.id)
        facts, verdict = self._judge(applied, evaluator, now)
        digest = fact_hash(facts)
        previous = self._repository.latest_for(applied.id)
        if (
            previous is not None
            and previous.rule_version_id == applied.rule_version_id
            and previous.fact_hash == digest
        ):
            return None
        result = self._repository.add_result(
            EvaluationResult(
                applied_control_id=applied.id,
                control_id=applied.control_id,
                control_code=applied.control_code,
                rule_type=applied.rule_type,
                rule_version_id=applied.rule_version_id,
                rule_version=applied.rule_version,
                subject_type=applied.subject_type.value,
                subject_id=applied.subject_id,
                subject_name=applied.subject_name,
                subject_domain_id=applied.subject_domain_id,
                run_id=run_id,
                evaluated_at=now,
                stale_after=now + evaluator.freshness,
                outcome=verdict.outcome.value,
                measured=_decimal(verdict.measured),
                threshold=_decimal(verdict.threshold),
                unit=verdict.unit,
                reason=verdict.reason,
                facts=facts,
                fact_hash=digest,
                previous_result_id=previous.id if previous else None,
                transition=_transition(previous, verdict.outcome),
            )
        )
        publish(
            self._session,
            RESULT_RECORDED,
            {
                "result_id": result.id,
                "applied_control_id": applied.id,
                "outcome": result.outcome,
                "transition": result.transition,
            },
        )
        if result.transition != "unchanged":
            self._audit.record(
                actor=SYSTEM_ACTOR,
                action="evaluation.result_recorded",
                subject_type="applied_control",
                subject_id=applied.id,
                reason=result.reason,
                before={"outcome": previous.outcome if previous else None},
                after={"outcome": result.outcome, "result_id": result.id},
            )
        return result

    def _judge(
        self, applied: AppliedControlRef, evaluator: Evaluator, now: datetime
    ) -> tuple[dict[str, Any], Verdict]:
        """The facts and the verdict, or the `error` that says why there are none. The facts of
        an error carry the day and the message, so one error is written per day, not per run."""
        today = now.date().isoformat()
        try:
            with self._session.begin_nested():
                facts = evaluator.gather(applied, self._facts, now.date())
                return facts, evaluator.evaluate(facts, applied.params)
        except FactsUnavailableError as exc:
            return {"as_of": today, "error": str(exc)}, Verdict(Outcome.ERROR, str(exc))
        except Exception:
            logger.exception("Evaluating %s failed", applied.id)
            message = "The evaluation failed unexpectedly."
            return {"as_of": today, "error": message}, Verdict(Outcome.ERROR, message)


def _decimal(value: float | None) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def _decode_id_cursor(cursor: str) -> uuid.UUID:
    try:
        return uuid.UUID(decode_cursor(cursor))
    except ValueError as exc:
        raise InvalidInputError("The cursor is not valid.", details={"cursor": cursor}) from exc
