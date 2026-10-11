"""API Router for Application-Level Data Movement & Integrity Controls."""
import uuid
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.deps import get_current_user, get_data_movement_service
from app.domain.exceptions import (
    DependencyConflictException,
    DomainException,
    EntityNotFoundException,
    ValidationException,
)
from app.models.data_movement import IntegrationDirectionEnum
from app.models.user import User
from app.schemas.data_movement import (
    ApplicationIntegrationRead,
    ApplicationProfileRead,
    BindScopeRequest,
    DataMovementScopeRead,
    DataSetCreate,
    DataSetDeleteBlockedResponse,
    DataSetRead,
    DataSetUpdate,
    DataSetUsageRead,
    SetIntegrityPatternRequest,
    SubmitCertificationRequest,
    VerifyCertificationRequest,
)
from app.services.data_movement_service import DataMovementService

router = APIRouter(tags=["Data Movement & Integrity Controls"])


def _handle_domain_exception(e: DomainException):
    """Map domain exceptions to standard HTTP status codes."""
    if isinstance(e, EntityNotFoundException):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    elif isinstance(e, DependencyConflictException):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": e.message,
                "blocking_integrations": [
                    b.model_dump() if hasattr(b, "model_dump") else b
                    for b in e.blocking_entities
                ],
            },
        )
    elif isinstance(e, ValidationException):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message)


# =============================================================================
# Application Profiles Endpoints
# =============================================================================

@router.get("/applications", response_model=List[ApplicationProfileRead])
async def list_applications(
    service: Annotated[DataMovementService, Depends(get_data_movement_service)],
):
    """List all synchronized application profiles with dataset and integration statistics."""
    return await service.list_applications()


@router.get("/applications/{app_head_id}", response_model=ApplicationProfileRead)
async def get_application(
    app_head_id: uuid.UUID,
    service: Annotated[DataMovementService, Depends(get_data_movement_service)],
):
    """Retrieve detailed application profile by asset head ID."""
    try:
        return await service.get_application_profile(app_head_id)
    except DomainException as e:
        _handle_domain_exception(e)


# =============================================================================
# Application-Scoped Datasets Endpoints
# =============================================================================

@router.get("/applications/{app_head_id}/datasets", response_model=List[DataSetRead])
async def list_application_datasets(
    app_head_id: uuid.UUID,
    service: Annotated[DataMovementService, Depends(get_data_movement_service)],
):
    """List all active datasets scoped to an application with active integration usage counts."""
    try:
        return await service.list_datasets(app_head_id)
    except DomainException as e:
        _handle_domain_exception(e)


@router.post(
    "/applications/{app_head_id}/datasets",
    response_model=DataSetRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_dataset(
    app_head_id: uuid.UUID,
    dataset_in: DataSetCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DataMovementService, Depends(get_data_movement_service)],
):
    """Create a new dataset scoped to the specified application with name uniqueness check."""
    try:
        return await service.create_dataset(
            app_head_id=app_head_id,
            dataset_in=dataset_in,
            user_id=current_user.id,
        )
    except DomainException as e:
        _handle_domain_exception(e)


@router.get("/applications/{app_head_id}/datasets/{dataset_id}", response_model=DataSetRead)
async def get_dataset(
    app_head_id: uuid.UUID,
    dataset_id: uuid.UUID,
    service: Annotated[DataMovementService, Depends(get_data_movement_service)],
):
    """Get dataset details including current ISR classification and data categories."""
    try:
        return await service.get_dataset(dataset_id)
    except DomainException as e:
        _handle_domain_exception(e)


@router.put("/applications/{app_head_id}/datasets/{dataset_id}", response_model=DataSetRead)
async def update_dataset(
    app_head_id: uuid.UUID,
    dataset_id: uuid.UUID,
    dataset_in: DataSetUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DataMovementService, Depends(get_data_movement_service)],
):
    """Update dataset metadata with automated Sensitivity Escalation Guardrail."""
    try:
        return await service.update_dataset(
            dataset_id=dataset_id,
            dataset_in=dataset_in,
            user_id=current_user.id,
        )
    except DomainException as e:
        _handle_domain_exception(e)


@router.get("/applications/{app_head_id}/datasets/{dataset_id}/usages", response_model=List[DataSetUsageRead])
async def get_dataset_usages(
    app_head_id: uuid.UUID,
    dataset_id: uuid.UUID,
    service: Annotated[DataMovementService, Depends(get_data_movement_service)],
):
    """Pre-flight dependency analysis: return all active integrations currently binding this dataset."""
    try:
        return await service.get_dataset_usages(dataset_id)
    except DomainException as e:
        _handle_domain_exception(e)


@router.delete("/applications/{app_head_id}/datasets/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    app_head_id: uuid.UUID,
    dataset_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DataMovementService, Depends(get_data_movement_service)],
):
    """Delete dataset with safety lock: returns 409 Conflict if bound to active integrations."""
    try:
        await service.delete_dataset(dataset_id=dataset_id, user_id=current_user.id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except DomainException as e:
        _handle_domain_exception(e)


# =============================================================================
# Integrations & Data Movement Governance Endpoints
# =============================================================================

@router.get("/applications/{app_head_id}/integrations", response_model=List[ApplicationIntegrationRead])
async def list_application_integrations(
    app_head_id: uuid.UUID,
    service: Annotated[DataMovementService, Depends(get_data_movement_service)],
    direction: Optional[IntegrationDirectionEnum] = Query(None, description="Optional filter by INBOUND / OUTBOUND"),
):
    """List directional integrations for an application with bound datasets, SLA timers, and partner systems."""
    try:
        return await service.list_integrations(app_head_id=app_head_id, direction=direction)
    except DomainException as e:
        _handle_domain_exception(e)


@router.get("/integrations/{integration_id}", response_model=ApplicationIntegrationRead)
async def get_integration(
    integration_id: uuid.UUID,
    service: Annotated[DataMovementService, Depends(get_data_movement_service)],
):
    """Retrieve integration details, bound datasets, and certified integrity pattern."""
    try:
        return await service.get_integration(integration_id)
    except DomainException as e:
        _handle_domain_exception(e)


@router.post("/integrations/{integration_id}/bind-scope", response_model=DataMovementScopeRead)
async def bind_scope(
    integration_id: uuid.UUID,
    scope_in: BindScopeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DataMovementService, Depends(get_data_movement_service)],
):
    """Bind a governed dataset to an integration with retention period and transit encryption."""
    try:
        return await service.bind_scope(
            integration_id=integration_id,
            scope_in=scope_in,
            user_id=current_user.id,
        )
    except DomainException as e:
        _handle_domain_exception(e)


@router.delete("/integrations/{integration_id}/unbind-scope/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unbind_scope(
    integration_id: uuid.UUID,
    dataset_id: uuid.UUID,
    service: Annotated[DataMovementService, Depends(get_data_movement_service)],
):
    """Remove a dataset from an integration scope. Triggers UNGOVERNED warning if 0 datasets remain."""
    try:
        await service.unbind_scope(integration_id=integration_id, dataset_id=dataset_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except DomainException as e:
        _handle_domain_exception(e)


@router.put("/integrations/{integration_id}/integrity-pattern", response_model=ApplicationIntegrationRead)
async def set_integrity_pattern(
    integration_id: uuid.UUID,
    pattern_in: SetIntegrityPatternRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DataMovementService, Depends(get_data_movement_service)],
):
    """Declare certified transfer integrity pattern and technical verification implementation notes."""
    try:
        return await service.set_integrity_pattern(
            integration_id=integration_id,
            pattern_in=pattern_in,
            user_id=current_user.id,
        )
    except DomainException as e:
        _handle_domain_exception(e)


@router.post("/integrations/{integration_id}/submit-certification", response_model=ApplicationIntegrationRead)
async def submit_certification(
    integration_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DataMovementService, Depends(get_data_movement_service)],
    body: Optional[SubmitCertificationRequest] = None,
):
    """Validate completeness (>=1 dataset and certified pattern) and transition to PENDING_VERIFICATION."""
    try:
        notes = body.certification_notes if body else None
        return await service.submit_certification(
            integration_id=integration_id,
            user_id=current_user.id,
            notes=notes,
        )
    except DomainException as e:
        _handle_domain_exception(e)


@router.post("/integrations/{integration_id}/verify-certification", response_model=ApplicationIntegrationRead)
async def verify_certification(
    integration_id: uuid.UUID,
    body: VerifyCertificationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DataMovementService, Depends(get_data_movement_service)],
):
    """Data Steward review: grant formal certification (COMPLIANT) or request remediation."""
    try:
        return await service.verify_certification(
            integration_id=integration_id,
            approved=body.approved,
            steward_user_id=current_user.id,
            notes=body.decision_notes,
        )
    except DomainException as e:
        _handle_domain_exception(e)
