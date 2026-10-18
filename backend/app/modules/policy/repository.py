"""Database access for policy. Only the service and the derivation use it."""

import uuid

from sqlalchemy import Select, func, or_, select, text
from sqlalchemy.orm import Session, selectinload

from app.modules.policy.domain import AppliedControlStatus, ControlStatus
from app.modules.policy.models import AppliedControl, Control, Policy, RuleVersion

# Derivation runs one at a time: a recompute job, an event handler and a second worker never
# interleave, so the one-active-row index is never the thing that arbitrates.
_DERIVATION_LOCK = 7_281_001


class PolicyRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def lock_derivation(self) -> None:
        self._session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": _DERIVATION_LOCK})

    # --- Policies

    def list_policies(self) -> list[Policy]:
        return list(self._session.scalars(select(Policy).order_by(Policy.name, Policy.id)))

    def get_policy(self, policy_id: uuid.UUID) -> Policy | None:
        return self._session.get(Policy, policy_id)

    def policy_code_taken(self, code: str) -> bool:
        return self._session.scalar(select(Policy.id).where(Policy.code == code)) is not None

    def control_counts_by_policy(self) -> dict[uuid.UUID, int]:
        rows = self._session.execute(
            select(Control.policy_id, func.count())
            .where(Control.status == ControlStatus.ACTIVE.value)
            .group_by(Control.policy_id)
        )
        return {row[0]: row[1] for row in rows}

    # --- Controls

    def _controls(
        self,
        policy_id: uuid.UUID | None,
        rule_type: str | None,
        status: str | None,
        query: str | None,
    ) -> Select[Control]:
        statement = select(Control)
        if policy_id is not None:
            statement = statement.where(Control.policy_id == policy_id)
        if rule_type is not None:
            statement = statement.where(Control.rule_type == rule_type)
        if status is not None:
            statement = statement.where(Control.status == status)
        if query:
            pattern = f"%{query}%"
            statement = statement.where(
                or_(Control.name.ilike(pattern), Control.code.ilike(pattern))
            )
        return statement

    def list_controls(
        self,
        *,
        after: str | None,
        limit: int,
        policy_id: uuid.UUID | None,
        rule_type: str | None,
        status: str | None,
        query: str | None,
    ) -> list[Control]:
        statement = self._controls(policy_id, rule_type, status, query).options(
            selectinload(Control.versions)
        )
        if after is not None:
            statement = statement.where(Control.code > after)
        return list(self._session.scalars(statement.order_by(Control.code).limit(limit)))

    def count_controls(
        self,
        *,
        policy_id: uuid.UUID | None,
        rule_type: str | None,
        status: str | None,
        query: str | None,
    ) -> int:
        subquery = self._controls(policy_id, rule_type, status, query).subquery()
        return self._session.scalar(select(func.count()).select_from(subquery)) or 0

    def get_control(self, control_id: uuid.UUID) -> Control | None:
        return self._session.scalar(
            select(Control)
            .where(Control.id == control_id)
            .options(selectinload(Control.versions))
            .execution_options(populate_existing=True)
        )

    def active_controls(self) -> list[Control]:
        return list(
            self._session.scalars(
                select(Control)
                .where(Control.status == ControlStatus.ACTIVE.value)
                .options(selectinload(Control.versions))
                .order_by(Control.code)
            )
        )

    def control_code_taken(self, code: str) -> bool:
        return self._session.scalar(select(Control.id).where(Control.code == code)) is not None

    def add_policy(self, policy: Policy) -> Policy:
        self._session.add(policy)
        self.flush(policy)
        return policy

    def add_control(self, control: Control, first_version: RuleVersion) -> Control:
        self._session.add(control)
        self._session.flush()
        first_version.control_id = control.id
        self._session.add(first_version)
        self._session.flush()
        self._session.expire(control, ["versions"])
        return control

    def add_version(self, control: Control, version: RuleVersion) -> RuleVersion:
        self._session.add(version)
        self._session.flush()
        self._session.expire(control, ["versions"])
        return version

    def flush(self, entity: Policy | Control) -> None:
        self._session.flush()
        self._session.refresh(entity)

    # --- Applied controls

    def active_counts_by_control(self) -> dict[uuid.UUID, int]:
        rows = self._session.execute(
            select(AppliedControl.control_id, func.count())
            .where(AppliedControl.status == AppliedControlStatus.ACTIVE.value)
            .group_by(AppliedControl.control_id)
        )
        return {row[0]: row[1] for row in rows}

    def active_for_control(self, control_id: uuid.UUID) -> list[AppliedControl]:
        return list(
            self._session.scalars(
                select(AppliedControl)
                .where(
                    AppliedControl.control_id == control_id,
                    AppliedControl.status == AppliedControlStatus.ACTIVE.value,
                )
                .execution_options(populate_existing=True)
            )
        )

    def active_for_subject(self, subject_type: str, subject_id: uuid.UUID) -> list[AppliedControl]:
        return list(
            self._session.scalars(
                select(AppliedControl)
                .where(
                    AppliedControl.subject_type == subject_type,
                    AppliedControl.subject_id == subject_id,
                    AppliedControl.status == AppliedControlStatus.ACTIVE.value,
                )
                .execution_options(populate_existing=True)
            )
        )

    def add_applied(self, applied: AppliedControl) -> AppliedControl:
        self._session.add(applied)
        self._session.flush()
        self._session.refresh(applied)
        return applied

    def flush_applied(self, applied: AppliedControl) -> None:
        self._session.flush()
        self._session.refresh(applied)

    def _applied(
        self,
        control_id: uuid.UUID | None,
        subject_type: str | None,
        subject_id: uuid.UUID | None,
        status: str | None,
        rule_type: str | None,
        scope: frozenset[uuid.UUID] | None,
    ) -> Select[AppliedControl]:
        statement = select(AppliedControl)
        if scope is not None:
            statement = statement.where(AppliedControl.subject_domain_id.in_(scope))
        if control_id is not None:
            statement = statement.where(AppliedControl.control_id == control_id)
        if subject_type is not None:
            statement = statement.where(AppliedControl.subject_type == subject_type)
        if subject_id is not None:
            statement = statement.where(AppliedControl.subject_id == subject_id)
        if status is not None:
            statement = statement.where(AppliedControl.status == status)
        if rule_type is not None:
            statement = statement.where(
                AppliedControl.control_id.in_(
                    select(Control.id).where(Control.rule_type == rule_type)
                )
            )
        return statement

    def list_applied(
        self,
        *,
        after: uuid.UUID | None,
        limit: int,
        control_id: uuid.UUID | None,
        subject_type: str | None,
        subject_id: uuid.UUID | None,
        status: str | None,
        rule_type: str | None,
        scope: frozenset[uuid.UUID] | None,
    ) -> list[AppliedControl]:
        """Newest first (ids are time-ordered)."""
        statement = self._applied(control_id, subject_type, subject_id, status, rule_type, scope)
        if after is not None:
            statement = statement.where(AppliedControl.id < after)
        return list(
            self._session.scalars(statement.order_by(AppliedControl.id.desc()).limit(limit))
        )

    def count_applied(
        self,
        *,
        control_id: uuid.UUID | None,
        subject_type: str | None,
        subject_id: uuid.UUID | None,
        status: str | None,
        rule_type: str | None,
        scope: frozenset[uuid.UUID] | None,
    ) -> int:
        subquery = self._applied(
            control_id, subject_type, subject_id, status, rule_type, scope
        ).subquery()
        return self._session.scalar(select(func.count()).select_from(subquery)) or 0

    def get_applied(self, applied_id: uuid.UUID) -> AppliedControl | None:
        return self._session.get(AppliedControl, applied_id)
