"""Public interface of the policy module: the only file other modules import.

Governance maintains policies and the control library; everyone signed in may read them. Applied
controls are derived, never created by a person, and are filtered to the caller's domains.

For the evaluation engine: `PolicyService.active_applied_controls` lists what to evaluate (with
the rule version's params and selector), and the outbox events `APPLIED_CONTROL_DERIVED`,
`APPLIED_CONTROL_RETIRED` and `RULE_VERSION_PUBLISHED` say when that list changed.
"""

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.core.auth import Permission, Principal, Role, allowed_actions, require
from app.core.errors import ConflictError, InvalidInputError, NotFoundError, PermissionDeniedError
from app.core.jobs import Job, enqueue
from app.core.outbox import publish
from app.core.pagination import PageResult, decode_cursor, encode_cursor
from app.modules.audit.service import AuditService
from app.modules.identity.service import IdentityService, User
from app.modules.inventory.service import AttributeSpec, SubjectCatalog, SubjectType
from app.modules.policy.derivation import (
    APPLIED_CONTROL_DERIVED as APPLIED_CONTROL_DERIVED,
)
from app.modules.policy.derivation import (
    APPLIED_CONTROL_RETIRED as APPLIED_CONTROL_RETIRED,
)
from app.modules.policy.derivation import (
    Derivation,
    DerivationSummary,
)
from app.modules.policy.domain import (
    RULE_TYPES,
    AppliedControlStatus,
    ControlStatus,
    Selector,
    describe,
    matches,
    parse_selector,
    rule_type,
    selector_from_stored,
    validate_params,
)
from app.modules.policy.models import AppliedControl, Control, Policy, RuleVersion
from app.modules.policy.repository import PolicyRepository
from app.modules.policy.schemas import (
    AppliedControlRead,
    AttributeRead,
    ConditionRead,
    ControlCreate,
    ControlDetail,
    ControlRef,
    ControlSummary,
    ControlUpdate,
    ParamRead,
    PolicyCreate,
    PolicyRead,
    PolicyRef,
    PolicyUpdate,
    RuleTypeRead,
    RuleVersionRead,
    SelectorBody,
    SelectorPreview,
    SubjectRef,
    SubjectTypeRead,
    UserRef,
    ValueOptionRead,
    Vocabulary,
)

RULE_VERSION_PUBLISHED = "policy.rule_version_published"
"""Outbox event: a control has a new current rule version. Payload: `control_id`, `version`,
`rule_version_id`. Evaluations of the control are keyed by rule version, so they start afresh."""

RECOMPUTE_CONTROL = "policy.recompute_control"
"""Job kind: re-derive one control's applied controls (payload: `control_id`)."""

_GOVERNANCE = {Role.GOVERNANCE}
CREATE_POLICY = Permission("create_policy", _GOVERNANCE)
EDIT_POLICY = Permission("edit_policy", _GOVERNANCE)
CREATE_CONTROL = Permission("create_control", _GOVERNANCE)
EDIT_CONTROL = Permission("edit", _GOVERNANCE)
PUBLISH_RULE_VERSION = Permission("publish_rule_version", _GOVERNANCE)
RETIRE_CONTROL = Permission("retire", _GOVERNANCE)
RECOMPUTE = Permission("recompute", _GOVERNANCE)
_CONTROL_PERMISSIONS = (EDIT_CONTROL, PUBLISH_RULE_VERSION, RETIRE_CONTROL, RECOMPUTE)

_SUBJECT_LABELS = {
    SubjectType.ASSET: "Asset",
    SubjectType.DATA_STORE: "Data store",
    SubjectType.APPLICATION: "Application",
}


def policy_list_actions(principal: Principal) -> list[str]:
    return allowed_actions(principal, [CREATE_POLICY])


def policy_actions(principal: Principal) -> list[str]:
    return allowed_actions(principal, [EDIT_POLICY, CREATE_CONTROL])


def control_list_actions(principal: Principal) -> list[str]:
    return allowed_actions(principal, [CREATE_CONTROL])


def control_actions(principal: Principal, control: ControlSummary) -> list[str]:
    """`allowed_actions` on one control. A retired control can no longer change."""
    if control.status == ControlStatus.RETIRED:
        return []
    return allowed_actions(principal, _CONTROL_PERMISSIONS)


@dataclass(frozen=True)
class AppliedControlRef:
    """What the evaluation engine needs about an applied control: the rule to run, the version
    it came from, and the subject. Plain data, so evaluation never reads policy tables."""

    id: uuid.UUID
    control_id: uuid.UUID
    control_code: str
    rule_type: str
    rule_version_id: uuid.UUID
    rule_version: int
    params: dict[str, Any]
    selector: dict[str, Any]
    subject_type: SubjectType
    subject_id: uuid.UUID
    subject_name: str
    subject_domain_id: uuid.UUID
    accountable_id: uuid.UUID | None
    responsible_id: uuid.UUID | None
    reason: str
    is_active: bool


def _ref(applied: AppliedControl) -> AppliedControlRef:
    version = applied.rule_version
    return AppliedControlRef(
        id=applied.id,
        control_id=applied.control_id,
        control_code=applied.control.code,
        rule_type=applied.control.rule_type,
        rule_version_id=version.id,
        rule_version=version.version,
        params=version.params,
        selector=version.selector,
        subject_type=SubjectType(applied.subject_type),
        subject_id=applied.subject_id,
        subject_name=applied.subject_name,
        subject_domain_id=applied.subject_domain_id,
        accountable_id=applied.accountable_id,
        responsible_id=applied.responsible_id,
        reason=applied.reason,
        is_active=applied.status == AppliedControlStatus.ACTIVE.value,
    )


def _user_ref(users: dict[uuid.UUID, User], user_id: uuid.UUID | None) -> UserRef | None:
    if user_id is None:
        return None
    user = users.get(user_id)
    return UserRef(id=user_id, display_name=user.display_name if user else "Unknown user")


def _control_snapshot(control: Control) -> dict[str, Any]:
    return {
        "code": control.code,
        "name": control.name,
        "description": control.description,
        "policy_id": control.policy_id,
        "rule_type": control.rule_type,
        "control_owner_id": control.control_owner_id,
        "evidence_requirement": control.evidence_requirement,
        "status": control.status,
    }


def _policy_snapshot(policy: Policy) -> dict[str, Any]:
    return {
        "code": policy.code,
        "name": policy.name,
        "statement": policy.statement,
        "owner_id": policy.owner_id,
    }


def _decode_code_cursor(cursor: str) -> str:
    return decode_cursor(cursor)


class PolicyService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repository = PolicyRepository(session)
        self._audit = AuditService(session)
        self._identity = IdentityService(session)
        self._derivation = Derivation(session)
        self._catalog = SubjectCatalog(session)

    # --- Vocabulary

    def vocabulary(self) -> Vocabulary:
        """The rule types, and the attributes a selector may use for each subject type."""
        return Vocabulary(
            rule_types=[
                RuleTypeRead(
                    key=t.key,
                    label=t.label,
                    description=t.description,
                    subjects=[s.value for s in t.subjects],
                    params=[
                        ParamRead(
                            name=p.name,
                            label=p.label,
                            kind=p.kind,
                            default=p.default,
                            minimum=p.minimum,
                            choices=list(p.choices),
                        )
                        for p in t.params
                    ],
                )
                for t in RULE_TYPES.values()
            ],
            subject_types=[
                SubjectTypeRead(
                    type=subject.value,
                    label=_SUBJECT_LABELS[subject],
                    attributes=[
                        AttributeRead(
                            name=a.name,
                            label=a.label,
                            kind=a.kind,
                            options=[
                                ValueOptionRead(value=o.value, label=o.label) for o in a.options
                            ],
                        )
                        for a in self._catalog.attributes(subject)
                    ],
                )
                for subject in SubjectType
            ],
        )

    def _vocabulary_specs(self) -> dict[SubjectType, dict[str, AttributeSpec]]:
        return {s: self._derivation.specs(s) for s in SubjectType}

    def _parse_selector(self, body: SelectorBody) -> Selector:
        return parse_selector(body.model_dump(), self._vocabulary_specs())

    # --- Policies

    def list_policies(self) -> list[PolicyRead]:
        policies = self._repository.list_policies()
        counts = self._repository.control_counts_by_policy()
        users = self._identity.get_users({p.owner_id for p in policies if p.owner_id})
        return [self._policy_read(p, counts.get(p.id, 0), users) for p in policies]

    def get_policy(self, policy_id: uuid.UUID) -> PolicyRead:
        policy = self._policy(policy_id)
        counts = self._repository.control_counts_by_policy()
        users = self._identity.get_users({policy.owner_id} if policy.owner_id else set())
        return self._policy_read(policy, counts.get(policy.id, 0), users)

    def _policy(self, policy_id: uuid.UUID) -> Policy:
        policy = self._repository.get_policy(policy_id)
        if policy is None:
            raise NotFoundError(
                f"Policy {policy_id} does not exist.", details={"id": str(policy_id)}
            )
        return policy

    def _policy_read(
        self, policy: Policy, controls: int, users: dict[uuid.UUID, User]
    ) -> PolicyRead:
        return PolicyRead(
            id=policy.id,
            code=policy.code,
            name=policy.name,
            statement=policy.statement,
            owner=_user_ref(users, policy.owner_id),
            control_count=controls,
            created_at=policy.created_at,
            updated_at=policy.updated_at,
        )

    def create_policy(self, principal: Principal, data: PolicyCreate) -> PolicyRead:
        require(principal, CREATE_POLICY)
        if self._repository.policy_code_taken(data.code):
            raise ConflictError(
                f"A policy with the code {data.code} already exists.", details={"field": "code"}
            )
        self._require_user(data.owner_id, "owner_id")
        policy = self._repository.add_policy(Policy(**data.model_dump()))
        self._audit.record(
            actor=principal.actor,
            action="policy.created",
            subject_type="policy",
            subject_id=policy.id,
            after=_policy_snapshot(policy),
        )
        return self.get_policy(policy.id)

    def update_policy(
        self, principal: Principal, policy_id: uuid.UUID, data: PolicyUpdate
    ) -> PolicyRead:
        require(principal, EDIT_POLICY)
        policy = self._policy(policy_id)
        changes = data.model_dump(exclude_unset=True)
        for required in ("name", "statement"):
            if required in changes and changes[required] is None:
                raise InvalidInputError(f"{required} cannot be empty.", details={"field": required})
        if "owner_id" in changes:
            self._require_user(changes["owner_id"], "owner_id")
        before = _policy_snapshot(policy)
        for field, value in changes.items():
            setattr(policy, field, value)
        after = _policy_snapshot(policy)
        if after != before:
            self._repository.flush(policy)
            changed = sorted(k for k in after if after[k] != before[k])
            self._audit.record(
                actor=principal.actor,
                action="policy.updated",
                subject_type="policy",
                subject_id=policy.id,
                before={k: before[k] for k in changed},
                after={k: after[k] for k in changed},
            )
        return self.get_policy(policy.id)

    def _require_user(self, user_id: uuid.UUID | None, field: str) -> None:
        if user_id is not None and user_id not in self._identity.get_users({user_id}):
            raise InvalidInputError("Choose a user that exists.", details={"field": field})

    # --- Controls

    def list_controls(
        self,
        *,
        limit: int,
        cursor: str | None,
        policy_id: uuid.UUID | None = None,
        rule_type_key: str | None = None,
        status: ControlStatus | None = None,
        query: str | None = None,
    ) -> PageResult[ControlSummary]:
        """A page of the control library, ordered by code."""
        after = _decode_code_cursor(cursor) if cursor else None
        query = query.strip() if query else None
        kind = status.value if status else None
        rows = self._repository.list_controls(
            after=after,
            limit=limit + 1,
            policy_id=policy_id,
            rule_type=rule_type_key,
            status=kind,
            query=query,
        )
        items = rows[:limit]
        next_cursor = encode_cursor(items[-1].code) if len(rows) > limit else None
        total = self._repository.count_controls(
            policy_id=policy_id, rule_type=rule_type_key, status=kind, query=query
        )
        return PageResult(items=self._summaries(items), next_cursor=next_cursor, total=total)

    def get_control(self, control_id: uuid.UUID) -> ControlDetail:
        return self._detail(self._control(control_id))

    def _control(self, control_id: uuid.UUID) -> Control:
        control = self._repository.get_control(control_id)
        if control is None:
            raise NotFoundError(
                f"Control {control_id} does not exist.", details={"id": str(control_id)}
            )
        return control

    def _users_for(self, controls: list[Control]) -> dict[uuid.UUID, User]:
        ids = {c.control_owner_id for c in controls if c.control_owner_id}
        ids |= {v.created_by_id for c in controls for v in c.versions}
        return self._identity.get_users(ids)

    def _version_read(self, version: RuleVersion, users: dict[uuid.UUID, User]) -> RuleVersionRead:
        selector = selector_from_stored(version.selector)
        specs = self._derivation.specs(selector.subject)
        conditions = []
        for c in selector.conditions:
            spec = specs[c.attribute]
            conditions.append(
                ConditionRead(
                    attribute=c.attribute,
                    attribute_label=spec.label,
                    operator=c.operator.value,
                    values=[
                        ValueOptionRead(value=str(v), label=spec.label_for(v)) for v in c.values
                    ],
                    text=describe(c, spec),
                )
            )
        return RuleVersionRead(
            id=version.id,
            version=version.version,
            params=version.params,
            selector=SelectorBody(**version.selector),
            conditions=conditions,
            change_reason=version.change_reason,
            created_by=_user_ref(users, version.created_by_id),
            created_at=version.created_at,
        )

    def _summary(
        self,
        control: Control,
        users: dict[uuid.UUID, User],
        counts: dict[uuid.UUID, int],
    ) -> ControlSummary:
        current = control.current_version
        policy = control.policy
        return ControlSummary(
            id=control.id,
            code=control.code,
            name=control.name,
            description=control.description,
            policy=PolicyRef(id=policy.id, code=policy.code, name=policy.name),
            rule_type=control.rule_type,
            rule_type_label=rule_type(control.rule_type).label,
            subject_type=current.selector["subject"],
            control_owner=_user_ref(users, control.control_owner_id),
            evidence_requirement=control.evidence_requirement,
            status=ControlStatus(control.status),
            retired_reason=control.retired_reason,
            current_version=self._version_read(current, users),
            applied_count=counts.get(control.id, 0),
            updated_at=control.updated_at,
        )

    def _summaries(self, controls: list[Control]) -> list[ControlSummary]:
        users = self._users_for(controls)
        counts = self._repository.active_counts_by_control()
        return [self._summary(c, users, counts) for c in controls]

    def _detail(self, control: Control) -> ControlDetail:
        users = self._users_for([control])
        summary = self._summary(control, users, self._repository.active_counts_by_control())
        return ControlDetail(
            **summary.model_dump(),
            versions=[self._version_read(v, users) for v in control.versions],
        )

    def create_control(self, principal: Principal, data: ControlCreate) -> ControlDetail:
        """Add a control to the library with its first rule version, and queue its derivation."""
        require(principal, CREATE_CONTROL)
        if self._repository.get_policy(data.policy_id) is None:
            raise InvalidInputError("Choose a policy that exists.", details={"field": "policy_id"})
        if self._repository.control_code_taken(data.code):
            raise ConflictError(
                f"A control with the code {data.code} already exists.", details={"field": "code"}
            )
        self._require_user(data.control_owner_id, "control_owner_id")
        rule = rule_type(data.rule_type)
        params = validate_params(rule, data.params)
        selector = self._checked_selector(rule.key, data.selector)
        control = self._repository.add_control(
            Control(
                policy_id=data.policy_id,
                code=data.code,
                name=data.name,
                description=data.description,
                rule_type=rule.key,
                control_owner_id=data.control_owner_id,
                evidence_requirement=data.evidence_requirement,
            ),
            RuleVersion(
                version=1,
                params=params,
                selector=selector.to_json(),
                created_by_id=principal.user_id,
            ),
        )
        self._repository.flush(control)
        self._audit.record(
            actor=principal.actor,
            action="control.created",
            subject_type="control",
            subject_id=control.id,
            after={**_control_snapshot(control), "params": params, "selector": selector.to_json()},
        )
        self._queue_derivation(control)
        return self.get_control(control.id)

    def update_control(
        self, principal: Principal, control_id: uuid.UUID, data: ControlUpdate
    ) -> ControlDetail:
        require(principal, EDIT_CONTROL)
        control = self._active_control(control_id)
        changes = data.model_dump(exclude_unset=True)
        if "name" in changes and changes["name"] is None:
            raise InvalidInputError("name cannot be empty.", details={"field": "name"})
        if "control_owner_id" in changes:
            self._require_user(changes["control_owner_id"], "control_owner_id")
        before = _control_snapshot(control)
        for field, value in changes.items():
            setattr(control, field, value)
        after = _control_snapshot(control)
        if after != before:
            self._repository.flush(control)
            changed = sorted(k for k in after if after[k] != before[k])
            self._audit.record(
                actor=principal.actor,
                action="control.updated",
                subject_type="control",
                subject_id=control.id,
                before={k: before[k] for k in changed},
                after={k: after[k] for k in changed},
            )
        return self.get_control(control.id)

    def publish_rule_version(
        self,
        principal: Principal,
        control_id: uuid.UUID,
        *,
        params: dict[str, Any],
        selector_body: SelectorBody,
        reason: str,
    ) -> ControlDetail:
        """Replace the control's rule with a new version (FR-P4). Versions are immutable, results
        are explained against the version that produced them, and a reason is required: a looser
        rule is a risk decision. Applied controls are re-derived by a job."""
        require(principal, PUBLISH_RULE_VERSION)
        control = self._active_control(control_id)
        rule = rule_type(control.rule_type)
        checked_params = validate_params(rule, params)
        selector = self._checked_selector(rule.key, selector_body)
        current = control.current_version
        if checked_params == current.params and selector.to_json() == current.selector:
            raise ConflictError(
                "The rule is the same as the current version.", details={"version": current.version}
            )
        version = self._repository.add_version(
            control,
            RuleVersion(
                control_id=control.id,
                version=current.version + 1,
                params=checked_params,
                selector=selector.to_json(),
                change_reason=reason.strip(),
                created_by_id=principal.user_id,
            ),
        )
        self._audit.record(
            actor=principal.actor,
            action="rule_version.published",
            subject_type="control",
            subject_id=control.id,
            reason=reason,
            reason_required=True,
            before={
                "version": current.version,
                "params": current.params,
                "selector": current.selector,
            },
            after={
                "version": version.version,
                "params": checked_params,
                "selector": selector.to_json(),
            },
        )
        publish(
            self._session,
            RULE_VERSION_PUBLISHED,
            {"control_id": control.id, "version": version.version, "rule_version_id": version.id},
        )
        self._queue_derivation(control)
        return self.get_control(control.id)

    def retire_control(
        self, principal: Principal, control_id: uuid.UUID, reason: str
    ) -> ControlDetail:
        """Take a control out of the library. Its applied controls are retired by a job; nothing
        is deleted."""
        require(principal, RETIRE_CONTROL)
        control = self._active_control(control_id)
        before = _control_snapshot(control)
        control.status = ControlStatus.RETIRED.value
        control.retired_reason = reason.strip() if reason else None
        # Refuses without a reason, which rolls the whole request back.
        self._audit.record(
            actor=principal.actor,
            action="control.retired",
            subject_type="control",
            subject_id=control.id,
            reason=reason,
            reason_required=True,
            before={"status": before["status"]},
            after={"status": control.status},
        )
        self._repository.flush(control)
        self._queue_derivation(control)
        return self.get_control(control.id)

    def recompute(self, principal: Principal, control_id: uuid.UUID) -> Job:
        """Queue a fresh derivation of one control, e.g. after something went wrong."""
        require(principal, RECOMPUTE)
        control = self._active_control(control_id)
        return enqueue(
            self._session,
            RECOMPUTE_CONTROL,
            {"control_id": control.id},
            created_by=principal.actor,
        )

    def preview_selector(self, principal: Principal, body: SelectorBody) -> SelectorPreview:
        """How many subjects a selector matches now, so a rule can be checked before publishing."""
        require(principal, CREATE_CONTROL)
        selector = self._parse_selector(body)
        facts = self._catalog.facts(selector.subject)
        hits = [f for f in facts if matches(selector, f.attributes)]
        return SelectorPreview(count=len(hits), total=len(facts), sample=[f.name for f in hits[:5]])

    def _active_control(self, control_id: uuid.UUID) -> Control:
        control = self._control(control_id)
        if control.status == ControlStatus.RETIRED:
            raise ConflictError("This control is retired.", details={"id": str(control_id)})
        return control

    def _checked_selector(self, rule_key: str, body: SelectorBody) -> Selector:
        selector = self._parse_selector(body)
        if selector.subject not in rule_type(rule_key).subjects:
            allowed = ", ".join(s.value for s in rule_type(rule_key).subjects)
            raise InvalidInputError(
                f"{rule_type(rule_key).label} applies to: {allowed}.",
                details={"field": "selector.subject"},
            )
        return selector

    def _queue_derivation(self, control: Control) -> None:
        version = control.current_version.version
        enqueue(
            self._session,
            RECOMPUTE_CONTROL,
            {"control_id": control.id},
            idempotency_key=f"control:{control.id}:v{version}:{control.status}",
        )

    # --- Applied controls

    def list_applied_controls(
        self,
        principal: Principal,
        *,
        limit: int,
        cursor: str | None,
        control_id: uuid.UUID | None = None,
        subject_type: SubjectType | None = None,
        subject_id: uuid.UUID | None = None,
        status: AppliedControlStatus | None = AppliedControlStatus.ACTIVE,
        rule_type_key: str | None = None,
    ) -> PageResult[AppliedControlRead]:
        """A page of applied controls on subjects in the caller's domains, newest first."""
        after = _decode_id_cursor(cursor) if cursor else None
        filters: dict[str, Any] = {
            "control_id": control_id,
            "subject_type": subject_type.value if subject_type else None,
            "subject_id": subject_id,
            "status": status.value if status else None,
            "rule_type": rule_type_key,
            "scope": principal.domain_ids,
        }
        rows = self._repository.list_applied(after=after, limit=limit + 1, **filters)
        items = rows[:limit]
        next_cursor = encode_cursor(str(items[-1].id)) if len(rows) > limit else None
        total = self._repository.count_applied(**filters)
        return PageResult(items=self._applied_reads(items), next_cursor=next_cursor, total=total)

    def get_applied_control(
        self, principal: Principal, applied_control_id: uuid.UUID
    ) -> AppliedControlRead:
        applied = self._repository.get_applied(applied_control_id)
        if applied is None:
            raise NotFoundError(
                f"Applied control {applied_control_id} does not exist.",
                details={"id": str(applied_control_id)},
            )
        if not principal.in_scope(applied.subject_domain_id):
            raise PermissionDeniedError(
                "This applied control is outside the domains you are scoped to.",
                details={"id": str(applied_control_id)},
            )
        return self._applied_reads([applied])[0]

    def _applied_reads(self, rows: list[AppliedControl]) -> list[AppliedControlRead]:
        ids = {a.accountable_id for a in rows if a.accountable_id}
        ids |= {a.responsible_id for a in rows if a.responsible_id}
        users = self._identity.get_users(ids)
        return [
            AppliedControlRead(
                id=a.id,
                control=ControlRef(
                    id=a.control.id,
                    code=a.control.code,
                    name=a.control.name,
                    rule_type=a.control.rule_type,
                ),
                subject=SubjectRef(type=a.subject_type, id=a.subject_id, name=a.subject_name),
                accountable=_user_ref(users, a.accountable_id),
                responsible=_user_ref(users, a.responsible_id),
                status=AppliedControlStatus(a.status),
                reason=a.reason,
                rule_version=a.rule_version.version,
                derived_from=a.derived_from,
                derived_at=a.derived_at,
                retired_at=a.retired_at,
                retired_reason=a.retired_reason,
            )
            for a in rows
        ]

    # --- For the evaluation engine

    def active_applied_controls(
        self,
        *,
        rule_type_key: str | None = None,
        subject_type: SubjectType | None = None,
        subject_id: uuid.UUID | None = None,
    ) -> list[AppliedControlRef]:
        """Every applied control to evaluate, for the system (no caller, no scope)."""
        rows = self._repository.list_applied(
            after=None,
            limit=100_000,
            control_id=None,
            subject_type=subject_type.value if subject_type else None,
            subject_id=subject_id,
            status=AppliedControlStatus.ACTIVE.value,
            rule_type=rule_type_key,
            scope=None,
        )
        return [_ref(a) for a in rows]

    def find_applied_control(self, applied_control_id: uuid.UUID) -> AppliedControlRef | None:
        applied = self._repository.get_applied(applied_control_id)
        return _ref(applied) if applied else None

    # --- For jobs and event handlers

    def recompute_control(self, control_id: uuid.UUID) -> DerivationSummary:
        return self._derivation.recompute_control(control_id)

    def derive_subject(self, subject_type: SubjectType, subject_id: uuid.UUID) -> DerivationSummary:
        return self._derivation.derive_subject(subject_type, subject_id)

    def recompute_all(self) -> DerivationSummary:
        return self._derivation.recompute_all()


def _decode_id_cursor(cursor: str) -> uuid.UUID:
    try:
        return uuid.UUID(decode_cursor(cursor))
    except ValueError as exc:
        raise InvalidInputError("The cursor is not valid.", details={"cursor": cursor}) from exc
