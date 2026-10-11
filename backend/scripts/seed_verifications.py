"""Setup pending Data Steward verification items for E2E testing."""
import asyncio
import sys
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

from app.core.database import AsyncSessionLocal
from app.models.data_movement import (
    ApplicationIntegration,
    IntegrationGovernanceStatusEnum,
    IntegrityPatternEnum,
    DataMovementScope,
    DataSet,
)
from app.models.compliance import (
    ComplianceIssue,
    ComplianceExemption,
    ExemptionStatusEnum,
    IssueStatusEnum,
    IssueSeverityEnum,
)
from app.models.user import User


async def setup_pending():
    async with AsyncSessionLocal() as session:
        now = datetime.now(timezone.utc)

        # 1. Find Elena Rostova (App Owner)
        app_owner_res = await session.execute(select(User).where(User.email == "elena.rostova@governance.local"))
        app_owner = app_owner_res.scalar_one_or_none()
        if not app_owner:
            app_owner_res = await session.execute(select(User).limit(1))
            app_owner = app_owner_res.scalar_one()

        # 2. Update INT-007103 to PENDING_VERIFICATION
        integ_res = await session.execute(
            select(ApplicationIntegration).where(ApplicationIntegration.itsm_integration_id == "INT-007103")
        )
        integ_7103 = integ_res.scalar_one_or_none()
        if integ_7103:
            integ_7103.governance_status = IntegrationGovernanceStatusEnum.PENDING_VERIFICATION
            integ_7103.integrity_pattern = IntegrityPatternEnum.IDEMPOTENT_DEDUPLICATION
            integ_7103.integrity_pattern_details = "mTLS v1.3 encryption with client idempotent message deduplication keys (128-bit sequence validation)."
            print("Updated INT-007103 to PENDING_VERIFICATION")

        # 3. Ensure a pending Exemption Waiver (REQUESTED status)
        # Find or create a defect for a pending waiver
        defect_res = await session.execute(
            select(ComplianceIssue).where(
                ComplianceIssue.rule_code == "STOR_001",
                ComplianceIssue.app_head_id.isnot(None),
            )
        )
        stor_issue = defect_res.scalar_one_or_none()
        if stor_issue:
            stor_issue.status = IssueStatusEnum.IN_REMEDIATION

            # Check if there is an exemption for this issue
            ex_res = await session.execute(
                select(ComplianceExemption).where(ComplianceExemption.issue_id == stor_issue.id)
            )
            ex = ex_res.scalar_one_or_none()
            if not ex:
                ex = ComplianceExemption(
                    id=uuid.uuid7(),
                    issue_id=stor_issue.id,
                    requested_by=app_owner.id,
                    justification="Enterprise database migration to AWS Aurora PostgreSQL scheduled for sprint 24. Full automated retention purge will be enabled in Aurora engine natively.",
                    compensating_controls="1. Daily snapshot backups archived to encrypted S3 Glacier vault.\n2. Splunk SIEM alerts on unpurged table volumes >25M rows.\n3. Restricted VPC security groups blocking external ingress.",
                    expires_at=now + timedelta(days=45),
                    status=ExemptionStatusEnum.REQUESTED,
                    created_at=now - timedelta(hours=2),
                )
                session.add(ex)
                print("Created new pending ComplianceExemption for STOR_001")
            else:
                ex.status = ExemptionStatusEnum.REQUESTED
                ex.justification = "Enterprise database migration to AWS Aurora PostgreSQL scheduled for sprint 24. Full automated retention purge will be enabled in Aurora engine natively."
                ex.compensating_controls = "1. Daily snapshot backups archived to encrypted S3 Glacier vault.\n2. Splunk SIEM alerts on unpurged table volumes >25M rows.\n3. Restricted VPC security groups blocking external ingress."
                ex.expires_at = now + timedelta(days=45)
                print("Reset existing ComplianceExemption to REQUESTED")

        await session.commit()
        print("Successfully prepared pending verification data!")


if __name__ == "__main__":
    asyncio.run(setup_pending())
