"""Request bodies, read models and response envelopes for the policy API."""

import uuid
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.core.schemas import Envelope, ListEnvelope
from app.modules.policy.domain import AppliedControlStatus, ControlStatus

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Code = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{1,39}$"),
]
Text = Annotated[str, StringConstraints(strip_whitespace=True, max_length=4000)]
Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class UserRef(BaseModel):
    id: uuid.UUID
    display_name: str


# --- Policies


class PolicyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: Code = Field(description="Short unique code, e.g. `RET`. Letters, digits, `.`, - and _.")
    name: Name
    statement: Text = Field(min_length=1, description="What the organisation commits to.")
    owner_id: uuid.UUID | None = Field(default=None, description="The governance owner.")


class PolicyUpdate(BaseModel):
    """Only the fields sent are changed."""

    model_config = ConfigDict(extra="forbid")

    name: Name | None = None
    statement: Text | None = None
    owner_id: uuid.UUID | None = None


class PolicyRead(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    statement: str
    owner: UserRef | None
    control_count: int = Field(description="Active controls under this policy.")
    created_at: datetime
    updated_at: datetime


class PolicyResponse(Envelope[PolicyRead]):
    pass


class PolicyList(ListEnvelope[PolicyRead]):
    pass


# --- Selectors and rule versions


class SelectorBody(BaseModel):
    """Which subjects a control applies to, by attribute.

    `where` maps an attribute to a value (equals), or `attribute.in` / `attribute.not_in` to a
    list of values; every condition must hold. See `GET /policy/vocabulary` for the attributes.
    """

    model_config = ConfigDict(extra="forbid")

    subject: str = Field(description="`asset`, `data_store` or `application`.")
    where: dict[str, bool | str | list[str]] = Field(default_factory=dict)


class ValueOptionRead(BaseModel):
    value: str
    label: str


class ConditionRead(BaseModel):
    """One condition of a selector in words the UI can show."""

    attribute: str
    attribute_label: str
    operator: str = Field(description="`equals`, `in` or `not_in`.")
    values: list[ValueOptionRead]
    text: str = Field(description="The whole condition as a phrase.")


class RuleVersionRead(BaseModel):
    id: uuid.UUID
    version: int
    params: dict[str, Any]
    selector: SelectorBody
    conditions: list[ConditionRead]
    change_reason: str | None
    created_by: UserRef | None
    created_at: datetime


class RuleVersionCreate(BaseModel):
    """A new version of a control's rule. Replaces the current one for every subject."""

    model_config = ConfigDict(extra="forbid")

    params: dict[str, Any] = Field(default_factory=dict)
    selector: SelectorBody
    reason: Reason = Field(description="Why the rule changes. Recorded in the audit trail.")


# --- Controls


class PolicyRef(BaseModel):
    id: uuid.UUID
    code: str
    name: str


class ControlCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_id: uuid.UUID
    code: Code
    name: Name
    description: Text | None = None
    rule_type: str = Field(description="See `GET /policy/vocabulary`.")
    control_owner_id: uuid.UUID | None = None
    evidence_requirement: Text | None = Field(
        default=None, description="What evidence shows the control is met."
    )
    params: dict[str, Any] = Field(default_factory=dict)
    selector: SelectorBody


class ControlUpdate(BaseModel):
    """Only the fields sent are changed. The rule changes through a new version."""

    model_config = ConfigDict(extra="forbid")

    name: Name | None = None
    description: Text | None = None
    control_owner_id: uuid.UUID | None = None
    evidence_requirement: Text | None = None


class RetireControl(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: Reason = Field(description="Why the control is retired. Recorded in the audit trail.")


class ControlSummary(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None
    policy: PolicyRef
    rule_type: str
    rule_type_label: str
    subject_type: str = Field(description="What the control applies to.")
    control_owner: UserRef | None
    evidence_requirement: str | None
    status: ControlStatus
    retired_reason: str | None
    current_version: RuleVersionRead
    applied_count: int = Field(description="Active applied controls derived from this control.")
    updated_at: datetime


class ControlDetail(ControlSummary):
    versions: list[RuleVersionRead] = Field(description="Newest first.")


class ControlResponse(Envelope[ControlDetail]):
    pass


class ControlPage(ListEnvelope[ControlSummary]):
    pass


class SelectorPreview(BaseModel):
    count: int = Field(description="Subjects the selector matches right now.")
    total: int = Field(description="Subjects of that type.")
    sample: list[str] = Field(description="Names of a few of them.")


class SelectorPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    selector: SelectorBody


class SelectorPreviewResponse(Envelope[SelectorPreview]):
    pass


# --- Applied controls


class ControlRef(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    rule_type: str


class SubjectRef(BaseModel):
    type: str
    id: uuid.UUID
    name: str


class AppliedControlRead(BaseModel):
    id: uuid.UUID
    control: ControlRef
    subject: SubjectRef
    accountable: UserRef | None = Field(description="The Data Owner (assets) or Application Owner.")
    responsible: UserRef | None = Field(description="The Data Steward (assets) or technical owner.")
    status: AppliedControlStatus
    reason: str = Field(description="Why this control applies to this subject. Shown by `Why?`.")
    rule_version: int
    derived_from: dict[str, Any]
    derived_at: datetime
    retired_at: datetime | None
    retired_reason: str | None


class AppliedControlResponse(Envelope[AppliedControlRead]):
    pass


class AppliedControlPage(ListEnvelope[AppliedControlRead]):
    pass


# --- Vocabulary


class AttributeRead(BaseModel):
    name: str
    label: str
    kind: str = Field(description="`boolean` or `choice`.")
    options: list[ValueOptionRead]


class SubjectTypeRead(BaseModel):
    type: str
    label: str
    attributes: list[AttributeRead]


class ParamRead(BaseModel):
    name: str
    label: str
    kind: str = Field(description="`integer` or `choices`.")
    default: int | list[str]
    minimum: int
    choices: list[str]


class RuleTypeRead(BaseModel):
    key: str
    label: str
    description: str
    subjects: list[str]
    params: list[ParamRead]


class Vocabulary(BaseModel):
    """What policies and controls are written in: rule types, and the attributes selectors use."""

    rule_types: list[RuleTypeRead]
    subject_types: list[SubjectTypeRead]


class VocabularyResponse(Envelope[Vocabulary]):
    pass
