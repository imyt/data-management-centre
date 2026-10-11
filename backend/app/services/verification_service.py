"""Service for Data Steward Two-Party Verification & Review Loop."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.compliance import (
    ComplianceExemption,
    ComplianceIssue,
    ComplianceIssueEvent,
    ExemptionStatusEnum,
    IssueStatusEnum,
)
from app.models.data_movement import (
    ApplicationIntegration,
    DataMovementScope,
    IntegrationGovernanceStatusEnum,
)
from app.models.asset import AssetHead
from app.models.user import User


class VerificationService:
    """Coordinates Data Steward reviews on App Owner attestations and compliance waivers."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_pending_verifications(self) -> Dict[str, Any]:
        """Fetch all items awaiting Data Steward sign-off."""
        # 1. Integrations awaiting transfer pattern verification
        integ_stmt = (
            select(ApplicationIntegration)
            .options(
                selectinload(ApplicationIntegration.source_app_head).selectinload(AssetHead.published_version),
                selectinload(ApplicationIntegration.target_app_head).selectinload(AssetHead.published_version),
                selectinload(ApplicationIntegration.movement_scopes).selectinload(DataMovementScope.dataset),
            )
            .where(
                ApplicationIntegration.governance_status == IntegrationGovernanceStatusEnum.PENDING_VERIFICATION
            )
            .order_by(ApplicationIntegration.created_at.desc())
        )
        integ_res = await self.session.execute(integ_stmt)
        integrations = integ_res.scalars().all()

        integration_items = []
        for integ in integrations:
            app_name = "Unknown App"
            app_ci = "CI-UNKNOWN"
            if integ.source_app_head and integ.source_app_head.published_version:
                app_name = integ.source_app_head.published_version.name
                app_ci = (integ.source_app_head.published_version.attributes_payload or {}).get("itsm_system_id", "CI-UNKNOWN")

            target_app_name = "External / Shared Target"
            if integ.target_app_head and integ.target_app_head.published_version:
                target_app_name = integ.target_app_head.published_version.name

            bound_datasets = [
                {
                    "id": str(scope.dataset.id),
                    "name": scope.dataset.name,
                    "isr_classification": scope.dataset.isr_classification.value if hasattr(scope.dataset.isr_classification, "value") else str(scope.dataset.isr_classification),
                }
                for scope in integ.movement_scopes
                if scope.dataset and not scope.dataset.is_archived
            ]

            integration_items.append({
                "id": str(integ.id),
                "itsm_integration_id": integ.itsm_integration_id,
                "app_head_id": str(integ.source_app_head_id),
                "app_name": app_name,
                "app_ci": app_ci,
                "partner_app_name": target_app_name,
                "direction": integ.direction.value,
                "transfer_type": integ.transfer_type.value,
                "frequency": integ.frequency.value,
                "integrity_pattern": integ.integrity_pattern.value,
                "integrity_pattern_details": integ.integrity_pattern_details,
                "governance_status": integ.governance_status.value,
                "bound_datasets": bound_datasets,
                "bound_datasets_count": len(bound_datasets),
                "submitted_at": integ.created_at.isoformat(),
            })

        # 2. Compliance exemption waivers awaiting review
        exemption_stmt = (
            select(ComplianceExemption)
            .options(
                selectinload(ComplianceExemption.issue)
                .selectinload(ComplianceIssue.application_head)
                .selectinload(AssetHead.published_version),
                selectinload(ComplianceExemption.issue).selectinload(ComplianceIssue.integration),
                selectinload(ComplianceExemption.issue).selectinload(ComplianceIssue.storage_control),
                selectinload(ComplianceExemption.issue).selectinload(ComplianceIssue.physical_column),
                selectinload(ComplianceExemption.requester),
            )
            .where(ComplianceExemption.status == ExemptionStatusEnum.REQUESTED)
            .order_by(ComplianceExemption.created_at.desc())
        )
        exemption_res = await self.session.execute(exemption_stmt)
        exemptions = exemption_res.scalars().all()

        waiver_items = []
        for ex in exemptions:
            issue = ex.issue
            app_name = "Unknown App"
            app_ci = "CI-UNKNOWN"
            if issue and issue.application_head and issue.application_head.published_version:
                app_name = issue.application_head.published_version.name
                app_ci = (issue.application_head.published_version.attributes_payload or {}).get("itsm_system_id", "CI-UNKNOWN")

            requester_name = ex.requester.full_name if ex.requester else "Application Owner"

            waiver_items.append({
                "id": str(ex.id),
                "issue_id": str(issue.id) if issue else None,
                "rule_code": issue.rule_code if issue else "UNKNOWN",
                "issue_title": issue.title if issue else "Unknown Issue",
                "severity": issue.severity.value if issue else "MEDIUM",
                "app_name": app_name,
                "app_ci": app_ci,
                "justification": ex.justification,
                "compensating_controls": ex.compensating_controls,
                "status": ex.status.value,
                "expires_at": ex.expires_at.isoformat(),
                "requested_by_name": requester_name,
                "requested_at": ex.created_at.isoformat(),
            })

        total_pending = len(integration_items) + len(waiver_items)
        return {
            "summary": {
                "total_pending": total_pending,
                "pending_integrations": len(integration_items),
                "pending_waivers": len(waiver_items),
            },
            "integrations": integration_items,
            "waivers": waiver_items,
        }

    async def review_integration(
        self,
        integration_id: uuid.UUID,
        approved: bool,
        decision_notes: str,
        steward_user_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Data Steward sign-off on Application Integration transfer integrity pattern."""
        stmt = (
            select(ApplicationIntegration)
            .options(selectinload(ApplicationIntegration.source_app_head))
            .where(ApplicationIntegration.id == integration_id)
        )
        res = await self.session.execute(stmt)
        integration = res.scalar_one_or_none()
        if not integration:
            raise ValueError(f"Integration {integration_id} not found.")

        now = datetime.now(timezone.utc)
        if approved:
            integration.governance_status = IntegrationGovernanceStatusEnum.COMPLIANT
            integration.certified_by = steward_user_id
            integration.governance_certified_at = now

            # Resolve associated MOV_001 defect
            issues_stmt = select(ComplianceIssue).where(
                ComplianceIssue.integration_id == integration.id,
                ComplianceIssue.status != IssueStatusEnum.RESOLVED,
            )
            issues_res = await self.session.execute(issues_stmt)
            for issue in issues_res.scalars().all():
                issue.status = IssueStatusEnum.RESOLVED
                issue.resolved_at = now
                event = ComplianceIssueEvent(
                    issue_id=issue.id,
                    actor_id=steward_user_id,
                    event_type="STEWARD_VERIFICATION_APPROVED",
                    from_status=IssueStatusEnum.PENDING_VERIFICATION,
                    to_status=IssueStatusEnum.RESOLVED,
                    notes=f"Data Steward certified pattern {integration.integrity_pattern.value}. Notes: {decision_notes}",
                )
                self.session.add(event)

            await self.session.commit()
            return {
                "status": "APPROVED",
                "message": f"Integration {integration.itsm_integration_id} certified as COMPLIANT.",
            }
        else:
            integration.governance_status = IntegrationGovernanceStatusEnum.IN_REMEDIATION

            # Re-open or keep defect in remediation
            issues_stmt = select(ComplianceIssue).where(
                ComplianceIssue.integration_id == integration.id
            )
            issues_res = await self.session.execute(issues_stmt)
            for issue in issues_res.scalars().all():
                issue.status = IssueStatusEnum.IN_REMEDIATION
                event = ComplianceIssueEvent(
                    issue_id=issue.id,
                    actor_id=steward_user_id,
                    event_type="STEWARD_VERIFICATION_REJECTED",
                    from_status=issue.status,
                    to_status=IssueStatusEnum.IN_REMEDIATION,
                    notes=f"Data Steward rejected pattern certification. Feedback: {decision_notes}",
                )
                self.session.add(event)

            await self.session.commit()
            return {
                "status": "REJECTED",
                "message": f"Integration {integration.itsm_integration_id} returned to IN_REMEDIATION.",
            }

    async def review_exemption(
        self,
        exemption_id: uuid.UUID,
        approved: bool,
        decision_notes: str,
        steward_user_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Data Steward review of requested compliance exemption waiver."""
        stmt = (
            select(ComplianceExemption)
            .options(selectinload(ComplianceExemption.issue))
            .where(ComplianceExemption.id == exemption_id)
        )
        res = await self.session.execute(stmt)
        exemption = res.scalar_one_or_none()
        if not exemption:
            raise ValueError(f"Exemption {exemption_id} not found.")

        now = datetime.now(timezone.utc)
        issue = exemption.issue

        if approved:
            exemption.status = ExemptionStatusEnum.APPROVED
            exemption.approved_by = steward_user_id

            if issue:
                issue.status = IssueStatusEnum.EXCEPTION_GRANTED
                event = ComplianceIssueEvent(
                    issue_id=issue.id,
                    actor_id=steward_user_id,
                    event_type="EXEMPTION_APPROVED",
                    from_status=issue.status,
                    to_status=IssueStatusEnum.EXCEPTION_GRANTED,
                    notes=f"Data Steward granted exemption until {exemption.expires_at.strftime('%Y-%m-%d')}. Decision Notes: {decision_notes}",
                )
                self.session.add(event)

            await self.session.commit()
            return {
                "status": "APPROVED",
                "message": f"Exemption waiver approved until {exemption.expires_at.strftime('%Y-%m-%d')}.",
            }
        else:
            exemption.status = ExemptionStatusEnum.REJECTED
            exemption.approved_by = steward_user_id

            if issue:
                issue.status = IssueStatusEnum.OPEN
                event = ComplianceIssueEvent(
                    issue_id=issue.id,
                    actor_id=steward_user_id,
                    event_type="EXEMPTION_REJECTED",
                    from_status=issue.status,
                    to_status=IssueStatusEnum.OPEN,
                    notes=f"Data Steward rejected exemption waiver. Reason: {decision_notes}",
                )
                self.session.add(event)

            await self.session.commit()
            return {
                "status": "REJECTED",
                "message": "Exemption waiver rejected. Compliance issue re-opened.",
            }
