"""Tier 1: Presentation / Driving HTTP REST Controller for Compliance Scans and Remediation."""
from typing import Annotated, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_compliance_service
from app.core.config import settings
from app.core.database import get_db
from app.domain.entities.compliance import IssueSeverity, IssueStatus
from app.domain.exceptions import DomainException, EntityNotFoundException, ValidationException
from app.models.user import User
from app.schemas.compliance import (
    ComplianceIssueRead,
    ComplianceScanRequest,
    ComplianceScanResponse,
    RemediateIssueRequestBody,
)
from app.services.compliance_service import ComplianceService

router = APIRouter(prefix="/compliance", tags=["Compliance & Remediation"])

oauth2_optional_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False,
)


async def get_optional_current_user(
    token: Annotated[Optional[str], Depends(oauth2_optional_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Optional[User]:
    """Extract User if a valid token is present; returns None otherwise."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str: str = payload.get("sub")
        if not user_id_str:
            return None
        user_id = uuid.UUID(user_id_str)
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    except (JWTError, ValueError):
        return None


def _handle_domain_exception(e: DomainException):
    """Map domain exceptions to HTTP status codes."""
    if isinstance(e, EntityNotFoundException):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    elif isinstance(e, ValidationException):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.message)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)


@router.get("/issues", response_model=List[ComplianceIssueRead])
async def list_compliance_issues(
    service: Annotated[ComplianceService, Depends(get_compliance_service)],
    domain_id: Optional[uuid.UUID] = Query(None, description="Filter by Domain"),
    asset_id: Optional[uuid.UUID] = Query(None, description="Filter by specific asset head"),
    severity: Optional[IssueSeverity] = Query(None, description="Filter by severity (CRITICAL, HIGH, etc.)"),
    status_filter: Optional[IssueStatus] = Query(None, alias="status", description="Filter by issue status"),
    limit: int = Query(100, ge=1, le=500),
):
    """List compliance issues detected during automated scans."""
    return await service.list_issues(
        domain_id=domain_id,
        asset_id=asset_id,
        severity=severity,
        status=status_filter,
        limit=limit,
    )


@router.post("/scan", response_model=ComplianceScanResponse)
async def scan_policies(
    service: Annotated[ComplianceService, Depends(get_compliance_service)],
    scan_request: Optional[ComplianceScanRequest] = None,
    current_user: Annotated[Optional[User], Depends(get_optional_current_user)] = None,
):
    """Trigger automated policy scan across curated assets to detect data quality anomalies."""
    try:
        actor_id = current_user.id if current_user else None
        domain_id = scan_request.domain_id if scan_request else None
        return await service.scan_policies(actor_id=actor_id, domain_id=domain_id)
    except DomainException as e:
        _handle_domain_exception(e)


@router.post("/issues/{issue_id}/remediate", response_model=ComplianceIssueRead)
async def remediate_issue(
    issue_id: uuid.UUID,
    service: Annotated[ComplianceService, Depends(get_compliance_service)],
    current_user: Annotated[Optional[User], Depends(get_optional_current_user)] = None,
    body: Optional[RemediateIssueRequestBody] = None,
):
    """Mark a compliance issue as remediated with optional auto-fix payload applied to the asset."""
    try:
        actor_id = current_user.id if current_user else None
        auto_fix = body.auto_fix_payload if body else None
        return await service.remediate_issue(
            issue_id=issue_id,
            resolved_by_user_id=actor_id,
            auto_fix_payload=auto_fix,
        )
    except DomainException as e:
        _handle_domain_exception(e)
