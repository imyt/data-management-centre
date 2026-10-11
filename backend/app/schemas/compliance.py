"""Pydantic schemas for Compliance and Remediation API."""
from datetime import datetime
from typing import List, Optional
import uuid

from pydantic import BaseModel, ConfigDict

from app.domain.entities.compliance import IssueSeverity, IssueStatus


class ComplianceIssueRead(BaseModel):
    id: uuid.UUID
    target_asset_head_id: uuid.UUID
    app_owner_id: uuid.UUID
    assigned_steward_id: Optional[uuid.UUID] = None
    title: str
    description: str
    severity: IssueSeverity
    status: IssueStatus
    remediation_deadline: datetime
    created_by: uuid.UUID
    created_at: datetime
    resolved_at: Optional[datetime] = None
    asset_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ComplianceScanRequest(BaseModel):
    domain_id: Optional[uuid.UUID] = None


class ComplianceScanResponse(BaseModel):
    scanned_assets_count: int
    issues_detected_count: int
    new_issues_created_count: int
    existing_issues_count: int
    issues: List[ComplianceIssueRead]

    model_config = ConfigDict(from_attributes=True)


class RemediateIssueRequestBody(BaseModel):
    resolution_notes: Optional[str] = None
    auto_apply_fix: bool = True
    auto_fix_payload: Optional[dict] = None
