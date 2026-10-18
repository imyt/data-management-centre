"""API shapes for evaluation results and runs."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas import Envelope, ListEnvelope
from app.modules.evaluation.domain import Outcome
from app.modules.inventory.service import SubjectType


class ResultControl(BaseModel):
    id: uuid.UUID
    code: str
    rule_type: str
    rule_version: int = Field(description="The version of the rule this result was judged by.")


class ResultSubject(BaseModel):
    type: SubjectType
    id: uuid.UUID
    name: str


class EvaluationResultRead(BaseModel):
    """What one rule said about one subject, with the facts it was judged on."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: uuid.UUID
    applied_control_id: uuid.UUID
    control: ResultControl
    subject: ResultSubject
    outcome: Outcome = Field(
        description="`error` means the rule could not be evaluated; it is not a failure."
    )
    measured: float | None = Field(description="What was measured, in `unit`, where relevant.")
    threshold: float | None = Field(description="The most the rule allows, in `unit`.")
    unit: str | None
    reason: str = Field(description="Plain language; shown by 'Why?'.")
    facts: dict[str, Any] = Field(description="The recorded facts and versions the verdict used.")
    evaluated_at: datetime
    stale_after: datetime
    is_stale: bool = Field(description="True once `stale_after` has passed: evaluate again.")
    previous_result_id: uuid.UUID | None
    transition: str = Field(
        description="`first`, `unchanged` (same outcome on new facts) or `<before>_to_<after>`."
    )
    run_id: uuid.UUID


class EvaluationRequest(BaseModel):
    """Which applied controls to evaluate: one, or every control on a subject."""

    model_config = ConfigDict(extra="forbid")

    applied_control_id: uuid.UUID | None = None
    subject_type: SubjectType | None = None
    subject_id: uuid.UUID | None = None


class EvaluationResultResponse(Envelope[EvaluationResultRead]):
    pass


class EvaluationResultPage(ListEnvelope[EvaluationResultRead]):
    pass
