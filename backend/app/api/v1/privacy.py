"""API Router for Privacy & Consumer Usage Entitlements Controls."""
import uuid
from typing import Annotated, Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_user, get_privacy_service
from app.models.user import User
from app.services.privacy_service import PrivacyService

router = APIRouter(prefix="/privacy", tags=["Privacy & Usage Entitlements"])


class CreateEntitlementRequest(BaseModel):
    app_head_id: uuid.UUID
    consumer_app_head_id: uuid.UUID
    authorized_purpose: str = Field(..., min_length=5)
    allowed_geo_regions: List[str] = Field(default=["US", "EU"])
    duration_days: int = Field(default=365, ge=1)


@router.get("/app/{app_head_id}/entitlements")
async def list_app_entitlements(
    app_head_id: uuid.UUID,
    service: Annotated[PrivacyService, Depends(get_privacy_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> List[Dict[str, Any]]:
    """List approved consumer application entitlements, authorized purposes, and geo-fencing."""
    return await service.list_entitlements(app_head_id)


@router.post("/entitlements")
async def create_entitlement(
    req: CreateEntitlementRequest,
    service: Annotated[PrivacyService, Depends(get_privacy_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Dict[str, Any]:
    """Authorize a consumer application to access data under purpose and regional boundaries."""
    return await service.create_entitlement(
        app_head_id=req.app_head_id,
        consumer_app_head_id=req.consumer_app_head_id,
        authorized_purpose=req.authorized_purpose,
        allowed_geo_regions=req.allowed_geo_regions,
        duration_days=req.duration_days,
        user_id=current_user.id,
    )


@router.post("/entitlements/{entitlement_id}/revoke")
async def revoke_entitlement(
    entitlement_id: uuid.UUID,
    service: Annotated[PrivacyService, Depends(get_privacy_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Dict[str, Any]:
    """Revoke consumer application data entitlement immediately."""
    try:
        return await service.revoke_entitlement(entitlement_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
