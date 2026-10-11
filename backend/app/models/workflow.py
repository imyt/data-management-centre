import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.metamodel import AssetType
    from app.models.asset import AssetVersion
    from app.models.user import User


class WorkflowInstanceStatus(str, enum.Enum):
    """Lifecycle execution status of a workflow instance."""
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class TaskDecisionEnum(str, enum.Enum):
    """Sign-off decision on an approval stage task."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"


class WorkflowDefinition(Base):
    """Workflow pipeline template attached to a specific Asset Type."""
    __tablename__ = "workflow_definitions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=func.uuidv7()
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    asset_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asset_types.id", ondelete="RESTRICT"),
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    asset_type: Mapped["AssetType"] = relationship(
        "AssetType",
        back_populates="workflow_definitions"
    )
    stages: Mapped[List["WorkflowStage"]] = relationship(
        "WorkflowStage",
        back_populates="workflow_definition",
        cascade="all, delete-orphan",
        order_by="WorkflowStage.stage_order"
    )
    instances: Mapped[List["WorkflowInstance"]] = relationship(
        "WorkflowInstance",
        back_populates="workflow_definition"
    )

    def __repr__(self) -> str:
        return f"<WorkflowDefinition {self.name}>"


class WorkflowStage(Base):
    """Ordered stage within a multi-stage workflow pipeline."""
    __tablename__ = "workflow_stages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=func.uuidv7()
    )
    workflow_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_definitions.id", ondelete="CASCADE"),
        nullable=False
    )
    stage_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    required_role: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    is_consensus: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    sla_hours: Mapped[int] = mapped_column(
        Integer,
        default=48,
        nullable=False
    )

    # Relationships
    workflow_definition: Mapped["WorkflowDefinition"] = relationship(
        "WorkflowDefinition",
        back_populates="stages"
    )
    tasks: Mapped[List["StageApprovalTask"]] = relationship(
        "StageApprovalTask",
        back_populates="stage",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("workflow_definition_id", "stage_order", name="uq_definition_stage_order"),
    )

    def __repr__(self) -> str:
        return f"<WorkflowStage {self.stage_order}: {self.name}>"


class WorkflowInstance(Base):
    """Runtime execution instance of a workflow for an asset version."""
    __tablename__ = "workflow_instances"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=func.uuidv7()
    )
    workflow_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_definitions.id", ondelete="RESTRICT"),
        nullable=False
    )
    asset_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asset_versions.id", ondelete="CASCADE"),
        nullable=False
    )
    current_stage_order: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False
    )
    status: Mapped[WorkflowInstanceStatus] = mapped_column(
        SQLEnum(WorkflowInstanceStatus, name="workflow_instance_status"),
        default=WorkflowInstanceStatus.RUNNING,
        nullable=False
    )
    initiated_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    workflow_definition: Mapped["WorkflowDefinition"] = relationship(
        "WorkflowDefinition",
        back_populates="instances"
    )
    asset_version: Mapped["AssetVersion"] = relationship(
        "AssetVersion",
        back_populates="workflow_instances"
    )
    initiator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[initiated_by]
    )
    tasks: Mapped[List["StageApprovalTask"]] = relationship(
        "StageApprovalTask",
        back_populates="workflow_instance",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<WorkflowInstance {self.id} [{self.status.value}]>"


class StageApprovalTask(Base):
    """Discrete review and sign-off task assigned to a user or role in a stage."""
    __tablename__ = "stage_approval_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=func.uuidv7()
    )
    workflow_instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_instances.id", ondelete="CASCADE"),
        nullable=False
    )
    stage_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_stages.id", ondelete="CASCADE"),
        nullable=False
    )
    assigned_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    assigned_role: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    decision: Mapped[TaskDecisionEnum] = mapped_column(
        SQLEnum(TaskDecisionEnum, name="task_decision_enum"),
        default=TaskDecisionEnum.PENDING,
        nullable=False
    )
    decision_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    decided_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    decided_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    due_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    workflow_instance: Mapped["WorkflowInstance"] = relationship(
        "WorkflowInstance",
        back_populates="tasks"
    )
    stage: Mapped["WorkflowStage"] = relationship(
        "WorkflowStage",
        back_populates="tasks"
    )
    assigned_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[assigned_user_id],
        back_populates="tasks_assigned"
    )
    decided_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[decided_by],
        back_populates="tasks_decided"
    )

    __table_args__ = (
        Index("idx_tasks_pending", "decision", postgresql_where=(decision == TaskDecisionEnum.PENDING)),
    )

    def __repr__(self) -> str:
        return f"<StageApprovalTask {self.id} [{self.decision.value}]>"
