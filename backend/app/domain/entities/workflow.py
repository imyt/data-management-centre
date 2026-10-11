"""Domain Entities for Governance Workflow Engine, Multi-Stage Approvals, and SLA Tracking."""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional


class WorkflowInstanceStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class TaskDecision(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"


@dataclass
class WorkflowStageEntity:
    id: uuid.UUID
    workflow_definition_id: uuid.UUID
    stage_order: int
    name: str
    required_role: str
    is_consensus: bool = False
    sla_hours: int = 48


@dataclass
class WorkflowDefinitionEntity:
    id: uuid.UUID
    name: str
    asset_type_id: uuid.UUID
    is_active: bool = True
    created_at: Optional[datetime] = None
    stages: List[WorkflowStageEntity] = field(default_factory=list)


@dataclass
class StageApprovalTaskEntity:
    id: uuid.UUID
    workflow_instance_id: uuid.UUID
    stage_id: uuid.UUID
    assigned_role: str
    due_at: datetime
    assigned_user_id: Optional[uuid.UUID] = None
    decision: TaskDecision = TaskDecision.PENDING
    decision_notes: Optional[str] = None
    decided_by: Optional[uuid.UUID] = None
    decided_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    # Enriched context for inbox display
    stage_name: Optional[str] = None
    stage_order: Optional[int] = None
    asset_version_id: Optional[uuid.UUID] = None
    asset_head_id: Optional[uuid.UUID] = None
    asset_name: Optional[str] = None
    asset_domain_id: Optional[uuid.UUID] = None
    asset_version_number: Optional[int] = None
    proposer_name: Optional[str] = None
    proposer_id: Optional[uuid.UUID] = None

    def is_pending(self) -> bool:
        return self.decision == TaskDecision.PENDING

    def approve(self, decided_by: uuid.UUID, notes: Optional[str] = None, now: Optional[datetime] = None) -> None:
        self.decision = TaskDecision.APPROVED
        self.decided_by = decided_by
        self.decision_notes = notes
        self.decided_at = now or datetime.now(timezone.utc)

    def reject(self, decided_by: uuid.UUID, notes: Optional[str] = None, now: Optional[datetime] = None) -> None:
        self.decision = TaskDecision.REJECTED
        self.decided_by = decided_by
        self.decision_notes = notes
        self.decided_at = now or datetime.now(timezone.utc)


@dataclass
class WorkflowInstanceEntity:
    id: uuid.UUID
    workflow_definition_id: uuid.UUID
    asset_version_id: uuid.UUID
    initiated_by: uuid.UUID
    current_stage_order: int = 1
    status: WorkflowInstanceStatus = WorkflowInstanceStatus.RUNNING
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    tasks: List[StageApprovalTaskEntity] = field(default_factory=list)

    def is_running(self) -> bool:
        return self.status == WorkflowInstanceStatus.RUNNING

    def mark_completed(self, now: Optional[datetime] = None) -> None:
        self.status = WorkflowInstanceStatus.COMPLETED
        self.completed_at = now or datetime.now(timezone.utc)

    def mark_rejected(self, now: Optional[datetime] = None) -> None:
        self.status = WorkflowInstanceStatus.REJECTED
        self.completed_at = now or datetime.now(timezone.utc)
