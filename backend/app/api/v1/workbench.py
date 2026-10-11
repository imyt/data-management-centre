"""API Router for Application Owner Workbench & Self-Service Remediation."""
import uuid
from typing import Annotated, Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_user, get_workbench_service
from app.models.data_movement import IntegrityPatternEnum
from app.models.physical_schema import MaskingStrategyEnum
from app.models.user import User
from app.services.workbench_service import WorkbenchService

router = APIRouter(prefix="/workbench", tags=["Application Owner Workbench"])


class RemediateIntegrityRequest(BaseModel):
    issue_id: uuid.UUID
    integration_id: uuid.UUID
    pattern: IntegrityPatternEnum
    pattern_details: str = Field(..., min_length=3)
    dataset_id: Optional[uuid.UUID] = None


class ColumnClassificationItem(BaseModel):
    column_id: str
    is_pii: bool = False
    masking_strategy: str = "NONE"
    isr_classification: str = "INTERNAL"
    business_term_name: Optional[str] = None


class RemediateSchemaDriftRequest(BaseModel):
    issue_id: uuid.UUID
    classifications: List[ColumnClassificationItem]


class RemediatePurgeRequest(BaseModel):
    issue_id: uuid.UUID
    storage_control_id: uuid.UUID
    attestation_notes: str = Field(..., min_length=3)


class RemediateMaskingRequest(BaseModel):
    issue_id: uuid.UUID
    column_id: uuid.UUID
    masking_strategy: MaskingStrategyEnum


class ExemptionRequest(BaseModel):
    issue_id: uuid.UUID
    justification: str = Field(..., min_length=10)
    compensating_controls: str = Field(..., min_length=10)
    duration_days: int = Field(default=30, ge=1, le=180)


@router.get("/{app_head_id}/summary")
async def get_workbench_summary(
    app_head_id: uuid.UUID,
    service: Annotated[WorkbenchService, Depends(get_workbench_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Dict[str, Any]:
    """Retrieve application governance health posture, SLA countdowns, and defect counters."""
    return await service.get_workbench_summary(app_head_id)


@router.get("/{app_head_id}/issues")
async def list_workbench_issues(
    app_head_id: uuid.UUID,
    service: Annotated[WorkbenchService, Depends(get_workbench_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    rule_code: Optional[str] = Query(None),
) -> List[Dict[str, Any]]:
    """List compliance defects for this application with linked technical entity context."""
    return await service.list_issues(
        app_head_id=app_head_id,
        status=status,
        severity=severity,
        rule_code=rule_code,
    )


@router.post("/remediate/integrity")
async def remediate_integrity(
    req: RemediateIntegrityRequest,
    service: Annotated[WorkbenchService, Depends(get_workbench_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Dict[str, Any]:
    """Remediate MOV_001: Certify transfer integrity pattern and bind dataset."""
    try:
        return await service.remediate_integrity_pattern(
            issue_id=req.issue_id,
            integration_id=req.integration_id,
            pattern=req.pattern,
            pattern_details=req.pattern_details,
            dataset_id=req.dataset_id,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/remediate/drift")
async def remediate_drift(
    req: RemediateSchemaDriftRequest,
    service: Annotated[WorkbenchService, Depends(get_workbench_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Dict[str, Any]:
    """Remediate DRIFT_001: Classify unclassified drifted columns and sync baseline."""
    try:
        return await service.remediate_schema_drift(
            issue_id=req.issue_id,
            classifications=[c.model_dump() for c in req.classifications],
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/remediate/purge")
async def remediate_purge(
    req: RemediatePurgeRequest,
    service: Annotated[WorkbenchService, Depends(get_workbench_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Dict[str, Any]:
    """Remediate STOR_001: Attest retention purge cycle completion."""
    try:
        return await service.remediate_storage_purge(
            issue_id=req.issue_id,
            storage_control_id=req.storage_control_id,
            attestation_notes=req.attestation_notes,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/remediate/masking")
async def remediate_masking(
    req: RemediateMaskingRequest,
    service: Annotated[WorkbenchService, Depends(get_workbench_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Dict[str, Any]:
    """Remediate PRIV_001: Configure masking strategy for sensitive physical column."""
    try:
        return await service.remediate_column_masking(
            issue_id=req.issue_id,
            column_id=req.column_id,
            masking_strategy=req.masking_strategy,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/exemptions/request")
async def request_exemption(
    req: ExemptionRequest,
    service: Annotated[WorkbenchService, Depends(get_workbench_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Dict[str, Any]:
    """Request compliance waiver with compensating security controls, pausing SLA."""
    try:
        return await service.request_exemption(
            issue_id=req.issue_id,
            justification=req.justification,
            compensating_controls=req.compensating_controls,
            duration_days=req.duration_days,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
