"""Service Tier: Cohesive domain service managing governance workflow pipelines.

Coordinates multi-stage approval lifecycles, consensus decisions, role-routed tasks,
SLA enforcement windows, and automated asset promotion upon approval.
"""
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.entities.workflow import TaskDecision
from app.domain.exceptions import EntityNotFoundException, ValidationException
from app.models.asset import AssetHead, AssetVersion, VersionStatusEnum
from app.models.workflow import (
    StageApprovalTask,
    TaskDecisionEnum,
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowInstanceStatus,
    WorkflowStage,
)


class WorkflowService:
    """Cohesive business logic service for multi-persona governance workflows."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # -------------------------------------------------------------------------
    # Tasks & Queries
    # -------------------------------------------------------------------------

    async def get_task(self, task_id: uuid.UUID) -> StageApprovalTask:
        """Fetch task with associated workflow stage and instance."""
        stmt = (
            select(StageApprovalTask)
            .options(
                selectinload(StageApprovalTask.stage),
                selectinload(StageApprovalTask.decided_by_user),
            )
            .where(StageApprovalTask.id == task_id)
        )
        result = await self.db.execute(stmt)
        task = result.scalar_one_or_none()
        if not task:
            raise EntityNotFoundException(f"Approval task '{task_id}' not found.")
        return task

    async def list_tasks(
        self,
        user_id: Optional[uuid.UUID] = None,
        role: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[StageApprovalTask]:
        """List workflow tasks matching role, user, or status filters."""
        stmt = (
            select(StageApprovalTask)
            .options(
                selectinload(StageApprovalTask.stage),
                selectinload(StageApprovalTask.decided_by_user),
            )
            .join(StageApprovalTask.stage)
            .order_by(StageApprovalTask.created_at.desc())
        )

        if role:
            stmt = stmt.where(WorkflowStage.required_role == role.upper())

        if status:
            stmt = stmt.where(StageApprovalTask.decision == TaskDecisionEnum(status.upper()))

        if user_id:
            stmt = stmt.where(
                or_(
                    StageApprovalTask.assigned_user_id == user_id,
                    StageApprovalTask.assigned_user_id.is_(None),
                )
            )

        stmt = stmt.limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_instance(self, instance_id: uuid.UUID) -> WorkflowInstance:
        """Fetch workflow instance with eager tasks and definition."""
        stmt = (
            select(WorkflowInstance)
            .options(
                selectinload(WorkflowInstance.tasks).selectinload(StageApprovalTask.stage),
                selectinload(WorkflowInstance.workflow_definition).selectinload(WorkflowDefinition.stages),
            )
            .where(WorkflowInstance.id == instance_id)
        )
        result = await self.db.execute(stmt)
        inst = result.scalar_one_or_none()
        if not inst:
            raise EntityNotFoundException(f"Workflow instance '{instance_id}' not found.")
        return inst

    # -------------------------------------------------------------------------
    # Actions & Transitions
    # -------------------------------------------------------------------------

    async def action_task(
        self,
        task_id: uuid.UUID,
        decision: TaskDecision,
        decided_by: uuid.UUID,
        decision_notes: Optional[str] = None,
    ) -> StageApprovalTask:
        """Execute review sign-off (Approve or Reject), progressing stages or promoting asset."""
        task = await self.get_task(task_id)
        if task.decision != TaskDecisionEnum.PENDING:
            raise ValidationException(f"Task '{task_id}' has already been decided ({task.decision.value}).")

        instance = await self.get_instance(task.workflow_instance_id)
        if instance.status != WorkflowInstanceStatus.RUNNING:
            raise ValidationException(f"Workflow instance '{instance.id}' is not active ({instance.status.value}).")

        now = datetime.now(timezone.utc)

        # ----------------- REJECTION PATH -----------------
        if decision == TaskDecision.REJECTED:
            task.decision = TaskDecisionEnum.REJECTED
            task.decided_by = decided_by
            task.decided_at = now
            task.decision_notes = decision_notes

            instance.status = WorkflowInstanceStatus.REJECTED
            instance.completed_at = now

            # Mark asset version REJECTED & release lease
            ver_stmt = select(AssetVersion).where(AssetVersion.id == instance.asset_version_id)
            ver_res = await self.db.execute(ver_stmt)
            version = ver_res.scalar_one_or_none()
            if version:
                version.status = VersionStatusEnum.REJECTED
                if version.asset_head_id:
                    head_stmt = (
                        select(AssetHead)
                        .where(AssetHead.id == version.asset_head_id)
                        .with_for_update()
                    )
                    head_res = await self.db.execute(head_stmt)
                    head = head_res.scalar_one_or_none()
                    if head and head.active_draft_version_id == version.id:
                        head.active_draft_version_id = None
                        head.locked_by_user_id = None
                        head.locked_at = None

            await self.db.commit()
            await self.db.refresh(task)
            return task

        # ----------------- APPROVAL PATH ------------------
        task.decision = TaskDecisionEnum.APPROVED
        task.decided_by = decided_by
        task.decided_at = now
        task.decision_notes = decision_notes

        # Check stages of the workflow definition
        definition = instance.workflow_definition
        stages = sorted(definition.stages, key=lambda s: s.stage_order)
        current_stage = next((s for s in stages if s.id == task.stage_id), None)
        if not current_stage:
            current_stage = next((s for s in stages if s.stage_order == instance.current_stage_order), None)

        # Find next sequential stage
        next_stage = next((s for s in stages if s.stage_order > instance.current_stage_order), None)

        if next_stage:
            # Advance to next stage: create new pending task
            instance.current_stage_order = next_stage.stage_order
            due_at = now + timedelta(hours=next_stage.sla_hours or 48)
            next_task = StageApprovalTask(
                id=uuid.uuid7(),
                workflow_instance_id=instance.id,
                stage_id=next_stage.id,
                assigned_role=next_stage.required_role,
                decision=TaskDecisionEnum.PENDING,
                due_at=due_at,
            )
            self.db.add(next_task)
        else:
            # All stages approved! Complete workflow & promote asset
            instance.status = WorkflowInstanceStatus.COMPLETED
            instance.completed_at = now

            # Promote version to PUBLISHED
            ver_stmt = select(AssetVersion).where(AssetVersion.id == instance.asset_version_id)
            ver_res = await self.db.execute(ver_stmt)
            version = ver_res.scalar_one_or_none()
            if version:
                if version.asset_head_id:
                    head_stmt = (
                        select(AssetHead)
                        .where(AssetHead.id == version.asset_head_id)
                        .with_for_update()
                    )
                    head_res = await self.db.execute(head_stmt)
                    head = head_res.scalar_one_or_none()
                    if head:
                        # Supersede prior published version
                        if head.published_version_id and head.published_version_id != version.id:
                            old_ver_stmt = select(AssetVersion).where(
                                AssetVersion.id == head.published_version_id
                            )
                            old_res = await self.db.execute(old_ver_stmt)
                            old_ver = old_res.scalar_one_or_none()
                            if old_ver:
                                old_ver.status = VersionStatusEnum.SUPERSEDED

                        version.status = VersionStatusEnum.PUBLISHED
                        version.published_at = now
                        head.published_version_id = version.id
                        head.active_draft_version_id = None
                        head.locked_by_user_id = None
                        head.locked_at = None

        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def start_workflow(
        self,
        asset_head_id: uuid.UUID,
        workflow_definition_id: uuid.UUID,
        requested_by_user_id: uuid.UUID,
    ) -> WorkflowInstance:
        """Start a governance approval pipeline instance for an asset draft."""
        head_stmt = (
            select(AssetHead)
            .options(selectinload(AssetHead.active_draft_version))
            .where(AssetHead.id == asset_head_id)
        )
        head_res = await self.db.execute(head_stmt)
        head = head_res.scalar_one_or_none()
        if not head:
            raise EntityNotFoundException(f"Asset head '{asset_head_id}' not found.")
        if not head.active_draft_version_id:
            raise ValidationException("Cannot start workflow: No active draft version exists.")

        def_stmt = (
            select(WorkflowDefinition)
            .options(selectinload(WorkflowDefinition.stages))
            .where(WorkflowDefinition.id == workflow_definition_id)
        )
        def_res = await self.db.execute(def_stmt)
        definition = def_res.scalar_one_or_none()
        if not definition or not definition.stages:
            raise ValidationException("Workflow definition has no configured stages.")

        stages = sorted(definition.stages, key=lambda s: s.stage_order)
        first_stage = stages[0]

        now = datetime.now(timezone.utc)
        instance_id = uuid.uuid7()

        instance = WorkflowInstance(
            id=instance_id,
            workflow_definition_id=definition.id,
            asset_version_id=head.active_draft_version_id,
            current_stage_order=first_stage.stage_order,
            status=WorkflowInstanceStatus.RUNNING,
            initiated_by=requested_by_user_id,
        )
        self.db.add(instance)

        # Mark draft as UNDER_REVIEW
        draft = head.active_draft_version
        if draft:
            draft.status = VersionStatusEnum.UNDER_REVIEW

        # Create Task for first stage
        due_at = now + timedelta(hours=first_stage.sla_hours or 48)
        first_task = StageApprovalTask(
            id=uuid.uuid7(),
            workflow_instance_id=instance_id,
            stage_id=first_stage.id,
            assigned_role=first_stage.required_role,
            decision=TaskDecisionEnum.PENDING,
            due_at=due_at,
        )
        self.db.add(first_task)

        await self.db.commit()
        return await self.get_instance(instance_id)
