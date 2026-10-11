import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.asset import AssetHead
    from app.models.data_movement import ApplicationIntegration
    from app.models.physical_schema import PhysicalColumn
    from app.models.storage_control import StorageControl
    from app.models.user import User


class IssueSeverityEnum(str, enum.Enum):
    """Compliance risk severity levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IssueStatusEnum(str, enum.Enum):
    """Compliance remediation lifecycle states."""
    OPEN = "OPEN"
    IN_REMEDIATION = "IN_REMEDIATION"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    RESOLVED = "RESOLVED"
    EXCEPTION_GRANTED = "EXCEPTION_GRANTED"


class ExemptionStatusEnum(str, enum.Enum):
    """Compliance exception/waiver approval state."""
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ComplianceIssue(Base):
    """Compliance deficiency flagged against an asset requiring owner remediation."""
    __tablename__ = "compliance_issues"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=func.uuidv7()
    )
    target_asset_head_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asset_heads.id", ondelete="CASCADE"),
        nullable=False
    )
    app_head_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asset_heads.id", ondelete="CASCADE"),
        nullable=True
    )
    rule_code: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )
    integration_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("application_integrations.id", ondelete="SET NULL"),
        nullable=True
    )
    storage_control_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("storage_controls.id", ondelete="SET NULL"),
        nullable=True
    )
    column_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("physical_columns.id", ondelete="SET NULL"),
        nullable=True
    )
    is_breached: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    app_owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    assigned_steward_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    severity: Mapped[IssueSeverityEnum] = mapped_column(
        SQLEnum(IssueSeverityEnum, name="issue_severity_enum"),
        default=IssueSeverityEnum.MEDIUM,
        nullable=False
    )
    status: Mapped[IssueStatusEnum] = mapped_column(
        SQLEnum(IssueStatusEnum, name="issue_status_enum"),
        default=IssueStatusEnum.OPEN,
        nullable=False
    )
    remediation_deadline: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    target_asset_head: Mapped["AssetHead"] = relationship(
        "AssetHead",
        foreign_keys=[target_asset_head_id],
        back_populates="compliance_issues"
    )
    application_head: Mapped[Optional["AssetHead"]] = relationship(
        "AssetHead",
        foreign_keys=[app_head_id]
    )
    integration: Mapped[Optional["ApplicationIntegration"]] = relationship(
        "ApplicationIntegration",
        foreign_keys=[integration_id]
    )
    storage_control: Mapped[Optional["StorageControl"]] = relationship(
        "StorageControl",
        foreign_keys=[storage_control_id]
    )
    physical_column: Mapped[Optional["PhysicalColumn"]] = relationship(
        "PhysicalColumn",
        foreign_keys=[column_id]
    )
    app_owner: Mapped["User"] = relationship(
        "User",
        foreign_keys=[app_owner_id],
        back_populates="compliance_issues_owned"
    )
    assigned_steward: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[assigned_steward_id]
    )
    creator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by],
        back_populates="compliance_issues_created"
    )
    submissions: Mapped[List["RemediationSubmission"]] = relationship(
        "RemediationSubmission",
        back_populates="issue",
        cascade="all, delete-orphan",
        order_by="desc(RemediationSubmission.created_at)"
    )
    events: Mapped[List["ComplianceIssueEvent"]] = relationship(
        "ComplianceIssueEvent",
        back_populates="issue",
        cascade="all, delete-orphan",
        order_by="desc(ComplianceIssueEvent.created_at)"
    )
    exemptions: Mapped[List["ComplianceExemption"]] = relationship(
        "ComplianceExemption",
        back_populates="issue",
        cascade="all, delete-orphan",
        order_by="desc(ComplianceExemption.created_at)"
    )

    __table_args__ = (
        Index("idx_issues_app_owner", "app_owner_id"),
        Index("idx_issues_app_head", "app_head_id"),
        Index("idx_issues_rule_code", "rule_code"),
        Index("idx_issues_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<ComplianceIssue {self.title} [{self.severity.value} / {self.status.value}]>"


class RemediationSubmission(Base):
    """Remediation evidence and explanation submitted by the Application Owner."""
    __tablename__ = "remediation_submissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=func.uuidv7()
    )
    issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compliance_issues.id", ondelete="CASCADE"),
        nullable=False
    )
    submitted_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    remediation_summary: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    evidence_urls: Mapped[list[Any]] = mapped_column(
        JSONB,
        server_default="[]",
        default=list,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    verified_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    steward_feedback: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Relationships
    issue: Mapped["ComplianceIssue"] = relationship(
        "ComplianceIssue",
        back_populates="submissions"
    )
    submitter: Mapped["User"] = relationship(
        "User",
        foreign_keys=[submitted_by],
        back_populates="remediation_submissions"
    )
    verifier: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[verified_by]
    )

    def __repr__(self) -> str:
        return f"<RemediationSubmission {self.id} (Issue: {self.issue_id})>"


class ComplianceIssueEvent(Base):
    """Immutable audit trail of compliance lifecycle status transitions and events."""
    __tablename__ = "compliance_issue_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=func.uuidv7()
    )
    issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compliance_issues.id", ondelete="CASCADE"),
        nullable=False
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )  # 'STATUS_CHANGE', 'SLA_EXTENSION', 'EVIDENCE_SUBMITTED'
    from_status: Mapped[Optional[IssueStatusEnum]] = mapped_column(
        SQLEnum(IssueStatusEnum, name="issue_status_enum", create_type=False),
        nullable=True
    )
    to_status: Mapped[Optional[IssueStatusEnum]] = mapped_column(
        SQLEnum(IssueStatusEnum, name="issue_status_enum", create_type=False),
        nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    issue: Mapped["ComplianceIssue"] = relationship(
        "ComplianceIssue",
        back_populates="events"
    )
    actor: Mapped["User"] = relationship(
        "User",
        foreign_keys=[actor_id]
    )

    def __repr__(self) -> str:
        return f"<ComplianceIssueEvent {self.event_type} on {self.issue_id}>"


class ComplianceExemption(Base):
    """Temporary compliance exemption or waiver requested by an Application Owner."""
    __tablename__ = "compliance_exemptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=func.uuidv7()
    )
    issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compliance_issues.id", ondelete="CASCADE"),
        nullable=False
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    justification: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    compensating_controls: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    status: Mapped[ExemptionStatusEnum] = mapped_column(
        SQLEnum(ExemptionStatusEnum, name="exemption_status_enum"),
        default=ExemptionStatusEnum.REQUESTED,
        nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    issue: Mapped["ComplianceIssue"] = relationship("ComplianceIssue", back_populates="exemptions")
    requester: Mapped["User"] = relationship("User", foreign_keys=[requested_by])
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by])

    __table_args__ = (
        Index("idx_exemptions_issue", "issue_id"),
        Index("idx_exemptions_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<ComplianceExemption {self.id} on Issue:{self.issue_id} [{self.status.value}]>"

