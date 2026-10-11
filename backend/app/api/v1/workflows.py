"""Tier 1: Presentation / Driving HTTP REST Controller for Governance Workflow Engine."""
from typing import Annotated, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_user, get_workflow_service
from app.domain.entities.workflow import TaskDecision
from app.domain.exceptions import (
    DomainException,
    EntityNotFoundException,
    ValidationException,
    WorkflowExecutionException,
)
from app.models.user import User
from app.schemas.workflow import (
    StageApprovalTaskRead,
    TaskActionRequest,
    WorkflowInstanceRead,
)
from app.services.workflow_service import WorkflowService

router = APIRouter(prefix="/workflows", tags=["Governance Workflow Engine"])


def _handle_domain_exception(e: DomainException):
    """Map domain exceptions to HTTP status codes."""
    if isinstance(e, EntityNotFoundException):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    elif isinstance(e, (ValidationException, WorkflowExecutionException)):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.message)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)


@router.get("/tasks", response_model=List[StageApprovalTaskRead])
async def list_workflow_tasks(
    service: Annotated[WorkflowService, Depends(get_workflow_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    role: Optional[str] = Query(None, description="Filter by required governance role"),
    status_filter: Optional[str] = Query("PENDING", description="Filter by decision status (PENDING, APPROVED, REJECTED)"),
    limit: int = Query(50, ge=1, le=100),
):
    """Retrieve queue of workflow stage approval tasks."""
    return await service.list_tasks(
        user_id=current_user.id,
        role=role,
        status=status_filter,
        limit=limit,
    )


@router.post("/tasks/{task_id}/action", response_model=StageApprovalTaskRead)
async def action_workflow_task(
    task_id: uuid.UUID,
    action_in: TaskActionRequest,
    service: Annotated[WorkflowService, Depends(get_workflow_service)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Sign-off action (Approve or Reject) on a pending governance review task."""
    try:
        return await service.action_task(
            task_id=task_id,
            decision=action_in.decision,
            decided_by=current_user.id,
            decision_notes=action_in.decision_notes,
        )
    except DomainException as e:
        _handle_domain_exception(e)


@router.get("/instances/{instance_id}", response_model=WorkflowInstanceRead)
async def get_workflow_instance(
    instance_id: uuid.UUID,
    service: Annotated[WorkflowService, Depends(get_workflow_service)],
):
    """Retrieve full audit state and stage history for a governance workflow instance."""
    try:
        return await service.get_instance(instance_id)
    except DomainException as e:
        _handle_domain_exception(e)
