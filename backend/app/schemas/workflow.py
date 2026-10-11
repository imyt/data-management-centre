"""Pydantic Request and Response Schemas for Governance Workflow Engine."""
from datetime import datetime
from typing import List, Optional
import uuid

from pydantic import BaseModel, ConfigDict
from app.models.workflow import TaskDecisionEnum, WorkflowInstanceStatus


class WorkflowStageRead(BaseModel):
    id: uuid.UUID
    workflow_definition_id: uuid.UUID
    stage_order: int
    name: str
    required_role: str
    is_consensus: bool
    sla_hours: int

    model_config = ConfigDict(from_attributes=True)


class WorkflowDefinitionRead(BaseModel):
    id: uuid.UUID
    name: str
    asset_type_id: uuid.UUID
    is_active: bool
    created_at: Optional[datetime] = None
    stages: List[WorkflowStageRead] = []

    model_config = ConfigDict(from_attributes=True)


class StageApprovalTaskRead(BaseModel):
    id: uuid.UUID
    workflow_instance_id: uuid.UUID
    stage_id: uuid.UUID
    assigned_role: str
    assigned_user_id: Optional[uuid.UUID] = None
    decision: TaskDecisionEnum
    decision_notes: Optional[str] = None
    decided_by: Optional[uuid.UUID] = None
    decided_at: Optional[datetime] = None
    due_at: datetime
    created_at: Optional[datetime] = None

    # Enriched context
    stage_name: Optional[str] = None
    stage_order: Optional[int] = None
    asset_version_id: Optional[uuid.UUID] = None
    asset_head_id: Optional[uuid.UUID] = None
    asset_name: Optional[str] = None
    asset_domain_id: Optional[uuid.UUID] = None
    asset_version_number: Optional[int] = None
    proposer_name: Optional[str] = None
    proposer_id: Optional[uuid.UUID] = None

    model_config = ConfigDict(from_attributes=True)


class TaskActionRequest(BaseModel):
    decision: TaskDecisionEnum
    decision_notes: Optional[str] = None


class WorkflowInstanceRead(BaseModel):
    id: uuid.UUID
    workflow_definition_id: uuid.UUID
    asset_version_id: uuid.UUID
    current_stage_order: int
    status: WorkflowInstanceStatus
    initiated_by: uuid.UUID
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    tasks: List[StageApprovalTaskRead] = []

    model_config = ConfigDict(from_attributes=True)
