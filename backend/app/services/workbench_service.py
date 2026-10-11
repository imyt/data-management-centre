"""Service for Application Owner Workbench, SLA countdowns, and self-service remediation."""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.asset import AssetHead
from app.models.compliance import (
    ComplianceIssue,
    ComplianceIssueEvent,
    ComplianceExemption,
    IssueSeverityEnum,
    IssueStatusEnum,
    ExemptionStatusEnum,
)
from app.models.data_movement import (
    ApplicationProfile,
    ApplicationIntegration,
    DataSet,
    DataMovementScope,
    IntegrationGovernanceStatusEnum,
    IntegrityPatternEnum,
    ISRClassificationEnum,
)
from app.models.storage_control import StorageControl, StorageTypeEnum
from app.models.physical_schema import (
    PhysicalTable,
    PhysicalColumn,
    DriftStatusEnum,
    MaskingStrategyEnum,
    SchemaHarvestRun,
)
from app.models.privacy_entitlement import UsageEntitlement


class WorkbenchService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_workbench_summary(self, app_head_id: uuid.UUID) -> Dict[str, Any]:
        """Aggregate compliance posture, SLA deadlines, and health metrics for an application."""
        # 1. Fetch Application Profile
        app_res = await self.session.execute(
            select(ApplicationProfile)
            .options(selectinload(ApplicationProfile.app_owner))
            .where(ApplicationProfile.asset_head_id == app_head_id)
        )
        app_profile = app_res.scalar_one_or_none()

        # If not found by asset_head_id, try by id
        if not app_profile:
            app_res = await self.session.execute(
                select(ApplicationProfile)
                .options(selectinload(ApplicationProfile.app_owner))
                .where(ApplicationProfile.id == app_head_id)
            )
            app_profile = app_res.scalar_one_or_none()
            if app_profile:
                app_head_id = app_profile.asset_head_id

        # 2. Fetch Active Compliance Issues for this Application
        now = datetime.now(timezone.utc)
        issues_res = await self.session.execute(
            select(ComplianceIssue)
            .options(
                selectinload(ComplianceIssue.integration),
                selectinload(ComplianceIssue.storage_control),
                selectinload(ComplianceIssue.physical_column),
                selectinload(ComplianceIssue.exemptions),
            )
            .where(
                or_(
                    ComplianceIssue.app_head_id == app_head_id,
                    ComplianceIssue.target_asset_head_id == app_head_id,
                )
            )
            .order_by(ComplianceIssue.remediation_deadline.asc())
        )
        all_issues = issues_res.scalars().all()

        open_issues = [i for i in all_issues if i.status in (IssueStatusEnum.OPEN, IssueStatusEnum.IN_REMEDIATION)]
        resolved_issues = [i for i in all_issues if i.status == IssueStatusEnum.RESOLVED]
        exempted_issues = [i for i in all_issues if i.status == IssueStatusEnum.EXCEPTION_GRANTED]

        # Calculate SLA urgency metrics
        breached_count = 0
        breaching_soon_count = 0  # < 48 hours
        urgent_defects = []

        for issue in open_issues:
            deadline = issue.remediation_deadline
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
            seconds_remaining = (deadline - now).total_seconds()
            is_breached = seconds_remaining <= 0
            is_breaching_soon = 0 < seconds_remaining <= 172800  # 48 hours

            if is_breached:
                breached_count += 1
            elif is_breaching_soon:
                breaching_soon_count += 1

            urgent_defects.append({
                "id": str(issue.id),
                "title": issue.title,
                "rule_code": issue.rule_code or "DEF_GEN",
                "severity": issue.severity.value,
                "status": issue.status.value,
                "deadline": deadline.isoformat(),
                "seconds_remaining": int(seconds_remaining),
                "is_breached": is_breached,
                "is_breaching_soon": is_breaching_soon,
                "integration_id": str(issue.integration_id) if issue.integration_id else None,
                "integration_name": issue.integration.itsm_integration_id if issue.integration else None,
                "storage_control_id": str(issue.storage_control_id) if issue.storage_control_id else None,
                "storage_name": issue.storage_control.storage_name if issue.storage_control else None,
                "column_id": str(issue.column_id) if issue.column_id else None,
                "column_name": issue.physical_column.column_name if issue.physical_column else None,
            })

        # 3. Control Planes Stats
        # Plane 1: Integrations
        int_res = await self.session.execute(
            select(
                func.count().label("total"),
                func.count().filter(ApplicationIntegration.governance_status == IntegrationGovernanceStatusEnum.COMPLIANT).label("compliant"),
                func.count().filter(ApplicationIntegration.governance_status == IntegrationGovernanceStatusEnum.UNGOVERNED).label("ungoverned"),
            ).where(
                or_(
                    ApplicationIntegration.source_app_head_id == app_head_id,
                    ApplicationIntegration.target_app_head_id == app_head_id,
                )
            )
        )
        int_stats = int_res.one()

        # Plane 2: Storage Repos
        stor_res = await self.session.execute(
            select(
                func.count().label("total"),
                func.count().filter(StorageControl.legal_hold_active.is_(True)).label("legal_holds"),
            ).where(StorageControl.app_head_id == app_head_id)
        )
        stor_stats = stor_res.one()

        # Plane 3: Physical Columns & Drift
        col_res = await self.session.execute(
            select(
                func.count(PhysicalColumn.id).label("total_columns"),
                func.count().filter(PhysicalColumn.drift_status == DriftStatusEnum.ADDED_UNCLASSIFIED).label("unclassified_drift"),
                func.count().filter(PhysicalColumn.is_pii.is_(True)).label("pii_columns"),
                func.count().filter((PhysicalColumn.is_pii.is_(True)) & (PhysicalColumn.masking_strategy != MaskingStrategyEnum.NONE)).label("masked_pii"),
            )
            .join(PhysicalTable, PhysicalColumn.table_id == PhysicalTable.id)
            .where(PhysicalTable.app_head_id == app_head_id)
        )
        col_stats = col_res.one()

        # Plane 4: Entitlements
        ent_res = await self.session.execute(
            select(func.count()).select_from(UsageEntitlement).where(
                UsageEntitlement.app_head_id == app_head_id,
                UsageEntitlement.is_active.is_(True),
            )
        )
        ent_active_count = ent_res.scalar() or 0

        # Calculate Overall Health Score (0 - 100)
        # Deduct for open issues and unclassified drift
        total_checks = (int_stats.total or 1) + (stor_stats.total or 1) + (col_stats.total_columns or 1)
        defect_penalty = (len(open_issues) * 15) + (breached_count * 20) + (breaching_soon_count * 5)
        raw_score = max(10, 100 - defect_penalty)
        health_score = min(100, raw_score)

        return {
            "application": {
                "id": str(app_profile.id) if app_profile else None,
                "asset_head_id": str(app_head_id),
                "itsm_system_id": app_profile.itsm_system_id if app_profile else "UNKNOWN",
                "itsm_system_name": app_profile.itsm_system_name if app_profile else "Unregistered Application",
                "cmdb_criticality": app_profile.cmdb_criticality if app_profile else "TIER_2",
                "app_owner_name": app_profile.app_owner.full_name if (app_profile and app_profile.app_owner) else "Unassigned",
                "app_owner_email": app_profile.app_owner.email if (app_profile and app_profile.app_owner) else "",
                "synced_at": app_profile.synced_at.isoformat() if app_profile else None,
            },
            "posture": {
                "health_score": health_score,
                "total_defects": len(all_issues),
                "open_defects": len(open_issues),
                "resolved_defects": len(resolved_issues),
                "active_exemptions": len(exempted_issues),
                "breached_defects": breached_count,
                "breaching_soon_defects": breaching_soon_count,
            },
            "control_planes": {
                "data_movement": {
                    "total_integrations": int_stats.total or 0,
                    "compliant": int_stats.compliant or 0,
                    "ungoverned": int_stats.ungoverned or 0,
                },
                "storage_retention": {
                    "total_repositories": stor_stats.total or 0,
                    "legal_holds_active": stor_stats.legal_holds or 0,
                },
                "schema_harvest": {
                    "total_columns": col_stats.total_columns or 0,
                    "unclassified_drift": col_stats.unclassified_drift or 0,
                },
                "privacy_usage": {
                    "pii_columns": col_stats.pii_columns or 0,
                    "masked_columns": col_stats.masked_pii or 0,
                    "active_entitlements": ent_active_count,
                },
            },
            "urgent_defects": urgent_defects,
        }

    async def list_issues(
        self,
        app_head_id: uuid.UUID,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        rule_code: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List compliance defects with linked entity metadata for self-service remediation."""
        now = datetime.now(timezone.utc)
        query = (
            select(ComplianceIssue)
            .options(
                selectinload(ComplianceIssue.integration),
                selectinload(ComplianceIssue.storage_control),
                selectinload(ComplianceIssue.physical_column).selectinload(PhysicalColumn.table),
                selectinload(ComplianceIssue.exemptions),
            )
            .where(
                or_(
                    ComplianceIssue.app_head_id == app_head_id,
                    ComplianceIssue.target_asset_head_id == app_head_id,
                )
            )
        )

        if status:
            query = query.where(ComplianceIssue.status == status)
        if severity:
            query = query.where(ComplianceIssue.severity == severity)
        if rule_code:
            query = query.where(ComplianceIssue.rule_code == rule_code)

        query = query.order_by(ComplianceIssue.remediation_deadline.asc())
        res = await self.session.execute(query)
        issues = res.scalars().all()

        results = []
        for issue in issues:
            deadline = issue.remediation_deadline
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
            seconds_remaining = (deadline - now).total_seconds()

            active_exemption = next((e for e in issue.exemptions if e.status == ExemptionStatusEnum.APPROVED), None)
            pending_exemption = next((e for e in issue.exemptions if e.status == ExemptionStatusEnum.REQUESTED), None)

            results.append({
                "id": str(issue.id),
                "title": issue.title,
                "description": issue.description,
                "rule_code": issue.rule_code,
                "severity": issue.severity.value,
                "status": issue.status.value,
                "remediation_deadline": deadline.isoformat(),
                "seconds_remaining": int(seconds_remaining),
                "is_breached": seconds_remaining <= 0 and issue.status != IssueStatusEnum.RESOLVED,
                "created_at": issue.created_at.isoformat(),
                "resolved_at": issue.resolved_at.isoformat() if issue.resolved_at else None,
                "integration": {
                    "id": str(issue.integration.id),
                    "itsm_integration_id": issue.integration.itsm_integration_id,
                    "direction": issue.integration.direction.value,
                    "transfer_type": issue.integration.transfer_type.value,
                    "governance_status": issue.integration.governance_status.value,
                    "integrity_pattern": issue.integration.integrity_pattern.value,
                } if issue.integration else None,
                "storage_control": {
                    "id": str(issue.storage_control.id),
                    "storage_name": issue.storage_control.storage_name,
                    "storage_type": issue.storage_control.storage_type.value,
                    "retention_period_days": issue.storage_control.retention_period_days,
                    "last_purge_attestation_at": issue.storage_control.last_purge_attestation_at.isoformat() if issue.storage_control.last_purge_attestation_at else None,
                    "legal_hold_active": issue.storage_control.legal_hold_active,
                } if issue.storage_control else None,
                "physical_column": {
                    "id": str(issue.physical_column.id),
                    "table_name": issue.physical_column.table.table_name if issue.physical_column.table else None,
                    "column_name": issue.physical_column.column_name,
                    "data_type": issue.physical_column.data_type,
                    "drift_status": issue.physical_column.drift_status.value,
                    "is_pii": issue.physical_column.is_pii,
                    "masking_strategy": issue.physical_column.masking_strategy.value,
                    "isr_classification": issue.physical_column.isr_classification.value,
                } if issue.physical_column else None,
                "exemption": {
                    "id": str(active_exemption.id) if active_exemption else (str(pending_exemption.id) if pending_exemption else None),
                    "status": active_exemption.status.value if active_exemption else (pending_exemption.status.value if pending_exemption else None),
                    "justification": active_exemption.justification if active_exemption else (pending_exemption.justification if pending_exemption else None),
                    "compensating_controls": active_exemption.compensating_controls if active_exemption else (pending_exemption.compensating_controls if pending_exemption else None),
                    "expires_at": active_exemption.expires_at.isoformat() if active_exemption else (pending_exemption.expires_at.isoformat() if pending_exemption else None),
                } if (active_exemption or pending_exemption) else None,
            })
        return results

    async def remediate_integrity_pattern(
        self,
        issue_id: uuid.UUID,
        integration_id: uuid.UUID,
        pattern: IntegrityPatternEnum,
        pattern_details: str,
        dataset_id: Optional[uuid.UUID],
        user_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Certify transfer integrity pattern, bind dataset, and resolve MOV_001 defect."""
        int_res = await self.session.execute(
            select(ApplicationIntegration).where(ApplicationIntegration.id == integration_id)
        )
        integration = int_res.scalar_one_or_none()
        if not integration:
            raise ValueError(f"Integration {integration_id} not found.")

        # Update integration contract
        integration.integrity_pattern = pattern
        integration.integrity_pattern_details = pattern_details
        integration.governance_status = IntegrationGovernanceStatusEnum.COMPLIANT
        integration.governance_certified_at = datetime.now(timezone.utc)
        integration.certified_by = user_id

        # Bind dataset if provided
        if dataset_id:
            scope_res = await self.session.execute(
                select(DataMovementScope).where(
                    DataMovementScope.integration_id == integration_id,
                    DataMovementScope.data_set_id == dataset_id,
                )
            )
            existing_scope = scope_res.scalar_one_or_none()
            if not existing_scope:
                new_scope = DataMovementScope(
                    integration_id=integration_id,
                    data_set_id=dataset_id,
                    created_by=user_id,
                )
                self.session.add(new_scope)

        # Resolve the compliance defect
        issue_res = await self.session.execute(
            select(ComplianceIssue).where(ComplianceIssue.id == issue_id)
        )
        issue = issue_res.scalar_one_or_none()
        if issue:
            issue.status = IssueStatusEnum.RESOLVED
            issue.resolved_at = datetime.now(timezone.utc)
            event = ComplianceIssueEvent(
                issue_id=issue.id,
                actor_id=user_id,
                event_type="REMEDIATION_INTEGRITY_CERTIFIED",
                from_status=IssueStatusEnum.OPEN,
                to_status=IssueStatusEnum.RESOLVED,
                notes=f"Certified integrity pattern {pattern.value}: {pattern_details}",
            )
            self.session.add(event)

        await self.session.commit()
        return {"status": "SUCCESS", "message": f"Integration {integration.itsm_integration_id} certified and issue resolved."}

    async def remediate_schema_drift(
        self,
        issue_id: uuid.UUID,
        classifications: List[Dict[str, Any]],
        user_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Classify drifted columns, update drift_status to SYNCED, and resolve DRIFT_001 defect."""
        now = datetime.now(timezone.utc)
        for c in classifications:
            col_id = uuid.UUID(c["column_id"])
            col_res = await self.session.execute(
                select(PhysicalColumn).where(PhysicalColumn.id == col_id)
            )
            column = col_res.scalar_one_or_none()
            if column:
                column.drift_status = DriftStatusEnum.SYNCED
                column.is_pii = bool(c.get("is_pii", False))
                if "masking_strategy" in c:
                    column.masking_strategy = MaskingStrategyEnum(c["masking_strategy"])
                if "isr_classification" in c:
                    column.isr_classification = ISRClassificationEnum(c["isr_classification"])
                if "business_term_name" in c:
                    column.business_term_name = c["business_term_name"]
                column.updated_at = now

        # Resolve issue
        issue_res = await self.session.execute(
            select(ComplianceIssue).where(ComplianceIssue.id == issue_id)
        )
        issue = issue_res.scalar_one_or_none()
        if issue:
            issue.status = IssueStatusEnum.RESOLVED
            issue.resolved_at = now
            event = ComplianceIssueEvent(
                issue_id=issue.id,
                actor_id=user_id,
                event_type="REMEDIATION_DRIFT_CLASSIFIED",
                from_status=IssueStatusEnum.OPEN,
                to_status=IssueStatusEnum.RESOLVED,
                notes=f"Classified {len(classifications)} drifted columns to SYNCED baseline.",
            )
            self.session.add(event)

        await self.session.commit()
        return {"status": "SUCCESS", "message": f"Classified {len(classifications)} columns and resolved drift issue."}

    async def remediate_storage_purge(
        self,
        issue_id: uuid.UUID,
        storage_control_id: uuid.UUID,
        attestation_notes: str,
        user_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Attest storage retention purge cycle and resolve STOR_001 defect."""
        stor_res = await self.session.execute(
            select(StorageControl).where(StorageControl.id == storage_control_id)
        )
        storage = stor_res.scalar_one_or_none()
        if not storage:
            raise ValueError(f"Storage control {storage_control_id} not found.")

        now = datetime.now(timezone.utc)
        storage.last_purge_attestation_at = now
        storage.last_purge_attested_by = user_id

        issue_res = await self.session.execute(
            select(ComplianceIssue).where(ComplianceIssue.id == issue_id)
        )
        issue = issue_res.scalar_one_or_none()
        if issue:
            issue.status = IssueStatusEnum.RESOLVED
            issue.resolved_at = now
            event = ComplianceIssueEvent(
                issue_id=issue.id,
                actor_id=user_id,
                event_type="REMEDIATION_PURGE_ATTESTED",
                from_status=IssueStatusEnum.OPEN,
                to_status=IssueStatusEnum.RESOLVED,
                notes=f"Attested retention purge cycle: {attestation_notes}",
            )
            self.session.add(event)

        await self.session.commit()
        return {"status": "SUCCESS", "message": f"Storage purge attested for {storage.storage_name}."}

    async def remediate_column_masking(
        self,
        issue_id: uuid.UUID,
        column_id: uuid.UUID,
        masking_strategy: MaskingStrategyEnum,
        user_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Set column privacy masking strategy and resolve PRIV_001 defect."""
        col_res = await self.session.execute(
            select(PhysicalColumn).where(PhysicalColumn.id == column_id)
        )
        column = col_res.scalar_one_or_none()
        if not column:
            raise ValueError(f"Column {column_id} not found.")

        column.masking_strategy = masking_strategy
        column.updated_at = datetime.now(timezone.utc)

        issue_res = await self.session.execute(
            select(ComplianceIssue).where(ComplianceIssue.id == issue_id)
        )
        issue = issue_res.scalar_one_or_none()
        if issue:
            issue.status = IssueStatusEnum.RESOLVED
            issue.resolved_at = datetime.now(timezone.utc)
            event = ComplianceIssueEvent(
                issue_id=issue.id,
                actor_id=user_id,
                event_type="REMEDIATION_MASKING_APPLIED",
                from_status=IssueStatusEnum.OPEN,
                to_status=IssueStatusEnum.RESOLVED,
                notes=f"Applied masking strategy {masking_strategy.value} to column {column.column_name}.",
            )
            self.session.add(event)

        await self.session.commit()
        return {"status": "SUCCESS", "message": f"Masking strategy set to {masking_strategy.value}."}

    async def request_exemption(
        self,
        issue_id: uuid.UUID,
        justification: str,
        compensating_controls: str,
        duration_days: int,
        user_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Request formal exemption waiver, pausing SLA countdown pending approval."""
        issue_res = await self.session.execute(
            select(ComplianceIssue).where(ComplianceIssue.id == issue_id)
        )
        issue = issue_res.scalar_one_or_none()
        if not issue:
            raise ValueError(f"Compliance issue {issue_id} not found.")

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=duration_days)

        exemption = ComplianceExemption(
            issue_id=issue.id,
            requested_by=user_id,
            justification=justification,
            compensating_controls=compensating_controls,
            status=ExemptionStatusEnum.APPROVED,  # auto-granting for self-service workbench demo
            approved_by=user_id,
            expires_at=expires_at,
        )
        self.session.add(exemption)

        issue.status = IssueStatusEnum.EXCEPTION_GRANTED
        event = ComplianceIssueEvent(
            issue_id=issue.id,
            actor_id=user_id,
            event_type="EXEMPTION_GRANTED",
            from_status=issue.status,
            to_status=IssueStatusEnum.EXCEPTION_GRANTED,
            notes=f"Waiver granted for {duration_days} days. Justification: {justification}",
        )
        self.session.add(event)

        await self.session.commit()
        return {"status": "SUCCESS", "message": f"Exemption waiver active until {expires_at.strftime('%Y-%m-%d')}."}
