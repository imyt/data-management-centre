"""API Router for Data Steward Two-Party Verification Queue."""
from typing import Annotated, Any, Dict
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.verification_service import VerificationService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/verifications", tags=["Data Steward Verifications"])


def get_verification_service(db: Annotated[AsyncSession, Depends(get_db)]) -> VerificationService:
    return VerificationService(db)


class ReviewActionRequest(BaseModel):
    approved: bool
    decision_notes: str = Field(..., min_length=3, max_length=1000)


@router.get("")
async def list_pending_verifications(
    service: Annotated[VerificationService, Depends(get_verification_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Dict[str, Any]:
    """Retrieve all pending transfer pattern certifications and compliance waivers awaiting Steward review."""
    return await service.list_pending_verifications()


@router.post("/integrations/{integration_id}/review")
async def review_integration(
    integration_id: uuid.UUID,
    req: ReviewActionRequest,
    service: Annotated[VerificationService, Depends(get_verification_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Dict[str, Any]:
    """Data Steward review (Approve / Reject) on an integration transfer integrity pattern."""
    try:
        return await service.review_integration(
            integration_id=integration_id,
            approved=req.approved,
            decision_notes=req.decision_notes,
            steward_user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/exemptions/{exemption_id}/review")
async def review_exemption(
    exemption_id: uuid.UUID,
    req: ReviewActionRequest,
    service: Annotated[VerificationService, Depends(get_verification_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Dict[str, Any]:
    """Data Steward review (Approve / Reject) on a compliance risk exemption waiver."""
    try:
        return await service.review_exemption(
            exemption_id=exemption_id,
            approved=req.approved,
            decision_notes=req.decision_notes,
            steward_user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
