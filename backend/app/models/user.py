import uuid
from typing import TYPE_CHECKING, List
from sqlalchemy import Boolean, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.rbac import ResponsibilityAssignment
    from app.models.compliance import ComplianceIssue, RemediationSubmission
    from app.models.workflow import StageApprovalTask


class User(Base, TimestampMixin):
    """Platform user entity supporting JWT authentication and RACI role assignments."""
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=func.uuidv7()
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    # Relationships
    responsibilities: Mapped[List["ResponsibilityAssignment"]] = relationship(
        "ResponsibilityAssignment",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    compliance_issues_owned: Mapped[List["ComplianceIssue"]] = relationship(
        "ComplianceIssue",
        foreign_keys="ComplianceIssue.app_owner_id",
        back_populates="app_owner"
    )
    compliance_issues_created: Mapped[List["ComplianceIssue"]] = relationship(
        "ComplianceIssue",
        foreign_keys="ComplianceIssue.created_by",
        back_populates="creator"
    )
    remediation_submissions: Mapped[List["RemediationSubmission"]] = relationship(
        "RemediationSubmission",
        foreign_keys="RemediationSubmission.submitted_by",
        back_populates="submitter"
    )
    tasks_assigned: Mapped[List["StageApprovalTask"]] = relationship(
        "StageApprovalTask",
        foreign_keys="StageApprovalTask.assigned_user_id",
        back_populates="assigned_user"
    )
    tasks_decided: Mapped[List["StageApprovalTask"]] = relationship(
        "StageApprovalTask",
        foreign_keys="StageApprovalTask.decided_by",
        back_populates="decided_by_user"
    )

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.full_name})>"
