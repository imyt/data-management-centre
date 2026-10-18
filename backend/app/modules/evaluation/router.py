"""Evaluation API: results with their facts and freshness, and a request to evaluate now."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import JSONResponse

from app.core.auth import PrincipalDep
from app.core.db import SessionDep
from app.core.jobs.router import accepted
from app.core.jobs.schemas import JobResponse
from app.core.schemas import ListMeta, Meta, error_responses
from app.modules.evaluation.domain import Outcome
from app.modules.evaluation.schemas import (
    EvaluationRequest,
    EvaluationResultPage,
    EvaluationResultResponse,
)
from app.modules.evaluation.service import EvaluationService
from app.modules.inventory.service import SubjectType

router = APIRouter(tags=["evaluation"])


def get_service(session: SessionDep) -> EvaluationService:
    return EvaluationService(session)


Service = Annotated[EvaluationService, Depends(get_service)]


@router.get(
    "/evaluation-results",
    response_model=EvaluationResultPage,
    operation_id="listEvaluationResults",
    summary="List evaluation results",
    description="By default one result per applied control: its latest. Pass `latest_only=false` "
    "for the history. `allowed_actions` offers `run_evaluation` when the list is narrowed to one "
    "applied control or subject the caller may evaluate.",
    responses=error_responses(401, 422),
)
def list_results(
    service: Service,
    principal: PrincipalDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: str | None = None,
    applied_control_id: uuid.UUID | None = None,
    control_id: uuid.UUID | None = None,
    subject_type: SubjectType | None = None,
    subject_id: uuid.UUID | None = None,
    outcome: Outcome | None = None,
    latest_only: Annotated[bool, Query(description="false: every result, newest first.")] = True,
) -> EvaluationResultPage:
    page = service.list_results(
        principal,
        limit=limit,
        cursor=cursor,
        applied_control_id=applied_control_id,
        control_id=control_id,
        subject_type=subject_type,
        subject_id=subject_id,
        outcome=outcome,
        latest_only=latest_only,
    )
    return EvaluationResultPage(
        data=page.items,
        allowed_actions=service.actions_for(
            principal,
            applied_control_id=applied_control_id,
            subject_type=subject_type,
            subject_id=subject_id,
        ),
        meta=ListMeta(next_cursor=page.next_cursor, total=page.total),
    )


@router.get(
    "/evaluation-results/{result_id}",
    response_model=EvaluationResultResponse,
    operation_id="getEvaluationResult",
    summary="Get one evaluation result with its facts",
    responses=error_responses(401, 403, 404, 422),
)
def get_result(
    result_id: uuid.UUID, service: Service, principal: PrincipalDep
) -> EvaluationResultResponse:
    result = service.get_result(principal, result_id)
    return EvaluationResultResponse(
        data=result,
        meta=Meta(evaluated_at=result.evaluated_at, stale_after=result.stale_after),
    )


@router.post(
    "/evaluations",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="runEvaluation",
    summary="Evaluate an applied control, or every control on a subject, now",
    description="Queues the evaluation and returns the job. A result is written only if the "
    "facts or the rule version changed since the latest one.",
    responses=error_responses(400, 401, 403, 404, 422),
)
def run_evaluation(
    body: EvaluationRequest, request: Request, service: Service, principal: PrincipalDep
) -> JSONResponse:
    job = service.request_evaluation(
        principal,
        applied_control_id=body.applied_control_id,
        subject_type=body.subject_type,
        subject_id=body.subject_id,
    )
    return accepted(request, job)
