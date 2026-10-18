"""Deriving applied controls from selectors, and keeping them current (FR-P3).

A control applies to every subject whose attributes satisfy the selector of its current rule
version. Derivation runs for one subject when its attributes change (an outbox event from
inventory) and for one control when its rule changes (a job). Both end in `_sync`, so the
outcome never depends on which got there first.
"""

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.outbox import publish
from app.modules.audit.service import AuditService
from app.modules.inventory.service import AttributeSpec, SubjectCatalog, SubjectFacts, SubjectType
from app.modules.policy.domain import (
    AppliedControlStatus,
    ControlStatus,
    Selector,
    matched_values,
    matches,
    selector_from_stored,
    why_applies,
    why_not,
)
from app.modules.policy.models import AppliedControl, Control
from app.modules.policy.repository import PolicyRepository

SYSTEM_ACTOR = "system:policy"

APPLIED_CONTROL_DERIVED = "policy.applied_control_derived"
APPLIED_CONTROL_RETIRED = "policy.applied_control_retired"
"""Outbox events for the evaluation engine. Payload: `applied_control_id`, `control_id`,
`subject_type`, `subject_id`."""


@dataclass
class DerivationSummary:
    created: int = 0
    updated: int = 0
    retired: int = 0

    def add(self, other: "DerivationSummary") -> None:
        self.created += other.created
        self.updated += other.updated
        self.retired += other.retired


class Derivation:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repository = PolicyRepository(session)
        self._audit = AuditService(session)
        self._catalog = SubjectCatalog(session)
        self._specs: dict[SubjectType, dict[str, AttributeSpec]] = {}

    def specs(self, subject_type: SubjectType) -> dict[str, AttributeSpec]:
        if subject_type not in self._specs:
            self._specs[subject_type] = {a.name: a for a in self._catalog.attributes(subject_type)}
        return self._specs[subject_type]

    # --- Entry points

    def recompute_control(self, control_id: uuid.UUID) -> DerivationSummary:
        """Re-derive one control for every subject; retire what no longer applies."""
        self._repository.lock_derivation()
        control = self._repository.get_control(control_id)
        summary = DerivationSummary()
        if control is None:
            return summary
        active = {a.subject_id: a for a in self._repository.active_for_control(control.id)}
        if control.status == ControlStatus.RETIRED:
            reason = f"The control was retired: {control.retired_reason}"
            for applied in active.values():
                self._retire(applied, reason, summary)
            return summary
        selector = selector_from_stored(control.current_version.selector)
        facts = self._catalog.facts(selector.subject)
        self._sync(control, selector, facts, active, summary)
        for applied in active.values():
            self._retire(applied, "The subject is no longer selectable by this control.", summary)
        return summary

    def derive_subject(self, subject_type: SubjectType, subject_id: uuid.UUID) -> DerivationSummary:
        """Re-derive every control for one subject whose attributes may have changed."""
        self._repository.lock_derivation()
        summary = DerivationSummary()
        facts = self._catalog.facts(subject_type, [subject_id])
        active = {
            a.control_id: a for a in self._repository.active_for_subject(subject_type, subject_id)
        }
        for control in self._repository.active_controls():
            selector = selector_from_stored(control.current_version.selector)
            if selector.subject != subject_type:
                continue
            existing = {subject_id: a} if (a := active.pop(control.id, None)) else {}
            self._sync(control, selector, facts, existing, summary)
            for applied in existing.values():
                self._retire(applied, "The subject no longer exists.", summary)
        return summary

    def recompute_all(self) -> DerivationSummary:
        summary = DerivationSummary()
        for control in self._repository.active_controls():
            summary.add(self.recompute_control(control.id))
        return summary

    # --- The shared step

    def _sync(
        self,
        control: Control,
        selector: Selector,
        facts: Iterable[SubjectFacts],
        active: dict[uuid.UUID, AppliedControl],
        summary: DerivationSummary,
    ) -> None:
        """Compare each subject with the selector. Subjects handled are removed from `active`,
        so what is left in it belongs to subjects that were not offered."""
        version = control.current_version
        specs = self.specs(selector.subject)
        for subject in facts:
            existing = active.pop(subject.subject_id, None)
            if not matches(selector, subject.attributes):
                if existing is not None:
                    self._retire(existing, why_not(selector, subject.attributes, specs), summary)
                continue
            reason = why_applies(selector, subject.attributes, specs)
            derived_from = {
                "rule_version": version.version,
                "attributes": matched_values(selector, subject.attributes),
            }
            if existing is None:
                self._create(control, version.id, subject, reason, derived_from, summary)
            else:
                self._refresh(existing, version.id, subject, reason, derived_from, summary)

    def _create(
        self,
        control: Control,
        version_id: uuid.UUID,
        subject: SubjectFacts,
        reason: str,
        derived_from: dict[str, Any],
        summary: DerivationSummary,
    ) -> None:
        applied = self._repository.add_applied(
            AppliedControl(
                control_id=control.id,
                rule_version_id=version_id,
                subject_type=subject.subject_type.value,
                subject_id=subject.subject_id,
                subject_name=subject.name,
                subject_domain_id=subject.domain_id,
                accountable_id=subject.accountable_id,
                responsible_id=subject.responsible_id,
                reason=reason,
                derived_from=derived_from,
            )
        )
        self._audit.record(
            actor=SYSTEM_ACTOR,
            action="applied_control.derived",
            subject_type="applied_control",
            subject_id=applied.id,
            reason=reason,
            after={
                "control": control.code,
                "subject_type": applied.subject_type,
                "subject_id": applied.subject_id,
                "rule_version": control.current_version.version,
            },
        )
        publish(self._session, APPLIED_CONTROL_DERIVED, _payload(applied))
        summary.created += 1

    def _refresh(
        self,
        applied: AppliedControl,
        version_id: uuid.UUID,
        subject: SubjectFacts,
        reason: str,
        derived_from: dict[str, Any],
        summary: DerivationSummary,
    ) -> None:
        """The control still applies: bring the row up to date (version, people, reason)."""
        fields: dict[str, Any] = {
            "rule_version_id": version_id,
            "subject_name": subject.name,
            "subject_domain_id": subject.domain_id,
            "accountable_id": subject.accountable_id,
            "responsible_id": subject.responsible_id,
            "reason": reason,
            "derived_from": derived_from,
        }
        changed = {k: v for k, v in fields.items() if getattr(applied, k) != v}
        if not changed:
            return
        for field, value in changed.items():
            setattr(applied, field, value)
        self._repository.flush_applied(applied)
        if "rule_version_id" in changed:
            # Re-derived under a new rule version: results of the old one no longer count.
            publish(self._session, APPLIED_CONTROL_DERIVED, _payload(applied))
        summary.updated += 1

    def _retire(self, applied: AppliedControl, reason: str, summary: DerivationSummary) -> None:
        applied.status = AppliedControlStatus.RETIRED.value
        applied.retired_at = datetime.now(UTC)
        applied.retired_reason = reason
        self._repository.flush_applied(applied)
        self._audit.record(
            actor=SYSTEM_ACTOR,
            action="applied_control.retired",
            subject_type="applied_control",
            subject_id=applied.id,
            reason=reason,
            before={"status": AppliedControlStatus.ACTIVE.value},
            after={"status": AppliedControlStatus.RETIRED.value},
        )
        publish(self._session, APPLIED_CONTROL_RETIRED, _payload(applied))
        summary.retired += 1


def _payload(applied: AppliedControl) -> dict[str, Any]:
    return {
        "applied_control_id": applied.id,
        "control_id": applied.control_id,
        "subject_type": applied.subject_type,
        "subject_id": applied.subject_id,
    }
