"""API Router for Storage & Retention Controls."""
import uuid
from typing import Annotated, Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_user, get_storage_service
from app.models.storage_control import (
    StorageTypeEnum,
    EncryptionAlgorithmEnum,
    PurgeMechanismEnum,
)
from app.models.user import User
from app.services.storage_service import StorageService

router = APIRouter(prefix="/storage", tags=["Storage & Retention Controls"])


class CreateStorageRequest(BaseModel):
    app_head_id: uuid.UUID
    storage_name: str = Field(..., min_length=2)
    storage_type: StorageTypeEnum
    encryption_algorithm: EncryptionAlgorithmEnum
    kms_key_arn: Optional[str] = None
    retention_period_days: int = Field(default=90, ge=1)
    purge_mechanism: PurgeMechanismEnum


class ToggleLegalHoldRequest(BaseModel):
    active: bool
    reason: Optional[str] = None


class AttestPurgeRequest(BaseModel):
    notes: Optional[str] = None


@router.get("/app/{app_head_id}")
async def list_app_storage_controls(
    app_head_id: uuid.UUID,
    service: Annotated[StorageService, Depends(get_storage_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> List[Dict[str, Any]]:
    """List storage repositories, KMS configurations, and purge status for an application."""
    return await service.list_by_app(app_head_id)


@router.post("")
async def create_storage_control(
    req: CreateStorageRequest,
    service: Annotated[StorageService, Depends(get_storage_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Dict[str, Any]:
    """Register a new storage repository under an application."""
    return await service.create_storage_control(
        app_head_id=req.app_head_id,
        storage_name=req.storage_name,
        storage_type=req.storage_type,
        encryption_algorithm=req.encryption_algorithm,
        kms_key_arn=req.kms_key_arn,
        retention_period_days=req.retention_period_days,
        purge_mechanism=req.purge_mechanism,
        user_id=current_user.id,
    )


@router.post("/{storage_id}/legal-hold")
async def toggle_legal_hold(
    storage_id: uuid.UUID,
    req: ToggleLegalHoldRequest,
    service: Annotated[StorageService, Depends(get_storage_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Dict[str, Any]:
    """Toggle legal hold freeze on a storage repository."""
    try:
        return await service.toggle_legal_hold(
            storage_id=storage_id,
            active=req.active,
            reason=req.reason,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{storage_id}/attest-purge")
async def attest_purge(
    storage_id: uuid.UUID,
    req: AttestPurgeRequest,
    service: Annotated[StorageService, Depends(get_storage_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Dict[str, Any]:
    """Attest completion of a retention purge cycle."""
    try:
        return await service.attest_purge(
            storage_id=storage_id,
            user_id=current_user.id,
            notes=req.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
