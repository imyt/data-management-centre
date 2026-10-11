"""Domain Entities for Compliance Anomaly Tracking and Policy Remediation."""
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid


class IssueSeverity(str, Enum):
    """Compliance risk severity levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IssueStatus(str, Enum):
    """Compliance remediation lifecycle states."""
    OPEN = "OPEN"
    IN_REMEDIATION = "IN_REMEDIATION"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    RESOLVED = "RESOLVED"
    EXCEPTION_GRANTED = "EXCEPTION_GRANTED"


@dataclass
class ComplianceIssueEntity:
    """Domain Entity representing a detected policy violation on an asset."""
    id: uuid.UUID
    target_asset_head_id: uuid.UUID
    app_owner_id: uuid.UUID
    title: str
    description: str
    severity: IssueSeverity
    status: IssueStatus
    remediation_deadline: datetime
    created_by: uuid.UUID
    created_at: datetime
    assigned_steward_id: Optional[uuid.UUID] = None
    resolved_at: Optional[datetime] = None
    asset_name: Optional[str] = None

    def is_open(self) -> bool:
        """Returns True if the issue requires remediation action."""
        return self.status in (IssueStatus.OPEN, IssueStatus.IN_REMEDIATION)

    def mark_resolved(self, resolved_at: Optional[datetime] = None) -> None:
        """Transitions issue into RESOLVED state with timestamp."""
        self.status = IssueStatus.RESOLVED
        self.resolved_at = resolved_at or datetime.now(timezone.utc)
