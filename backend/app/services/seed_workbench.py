"""Seed script to populate Workbench Storage, Physical Schema Drift, Privacy, and SLA Issues."""
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, or_
from app.core.database import AsyncSessionLocal
from app.models.asset import AssetHead
from app.models.user import User
from app.models.compliance import (
    ComplianceIssue,
    IssueSeverityEnum,
    IssueStatusEnum,
)
from app.models.data_movement import (
    ApplicationProfile,
    ApplicationIntegration,
    IntegrationGovernanceStatusEnum,
    IntegrityPatternEnum,
    ISRClassificationEnum,
)
from app.models.storage_control import (
    StorageControl,
    StorageTypeEnum,
    EncryptionAlgorithmEnum,
    PurgeMechanismEnum,
)
from app.models.physical_schema import (
    PhysicalTable,
    PhysicalColumn,
    SchemaHarvestRun,
    DriftStatusEnum,
    MaskingStrategyEnum,
    HarvestStatusEnum,
)
from app.models.privacy_entitlement import UsageEntitlement


async def seed_workbench():
    print("Beginning Workbench & Control Planes Seed...")
    async with AsyncSessionLocal() as session:
        # 1. Fetch Core Banking Application & Users
        core_app_res = await session.execute(
            select(ApplicationProfile).where(ApplicationProfile.itsm_system_id == "APP-10921")
        )
        core_app = core_app_res.scalar_one_or_none()
        if not core_app:
            print("Core Banking profile not found. Run seed_data.py first.")
            return

        core_head_id = core_app.asset_head_id
        app_owner_id = core_app.app_owner_id

        # Fetch other apps for consumer entitlements
        fraud_app_res = await session.execute(
            select(ApplicationProfile).where(ApplicationProfile.itsm_system_id == "APP-20419")
        )
        fraud_app = fraud_app_res.scalar_one_or_none()

        reg_app_res = await session.execute(
            select(ApplicationProfile).where(ApplicationProfile.itsm_system_id == "APP-40881")
        )
        reg_app = reg_app_res.scalar_one_or_none()

        steward_res = await session.execute(select(User).where(User.email.like("%steward%")))
        steward = steward_res.scalars().first()
        steward_id = steward.id if steward else app_owner_id

        now = datetime.now(timezone.utc)

        # 2. Seed Storage Controls for Core Banking
        # Repo 1: PostgreSQL DB (Purge Overdue -> triggers STOR_001)
        pg_res = await session.execute(
            select(StorageControl).where(
                StorageControl.app_head_id == core_head_id,
                StorageControl.storage_name == "pg-core-ledger-db",
            )
        )
        pg_storage = pg_res.scalar_one_or_none()
        if not pg_storage:
            pg_storage = StorageControl(
                id=uuid.uuid7(),
                app_head_id=core_head_id,
                storage_name="pg-core-ledger-db",
                storage_type=StorageTypeEnum.POSTGRESQL,
                encryption_algorithm=EncryptionAlgorithmEnum.AWS_KMS_CMK,
                kms_key_arn="arn:aws:kms:us-east-1:109210001234:key/mrk-8921-prod-cmk",
                retention_period_days=90,
                purge_mechanism=PurgeMechanismEnum.CRYPTOGRAPHIC_ERASURE,
                legal_hold_active=False,
                last_purge_attestation_at=now - timedelta(days=104),  # 104 days ago > 90 days retention -> OVERDUE
                last_purge_attested_by=app_owner_id,
            )
            session.add(pg_storage)
            await session.flush()
            print("Seeded Storage: pg-core-ledger-db (Overdue purge)")

        # Repo 2: S3 Statements Vault (Healthy)
        s3_res = await session.execute(
            select(StorageControl).where(
                StorageControl.app_head_id == core_head_id,
                StorageControl.storage_name == "s3-ledger-daily-audit-vault",
            )
        )
        s3_storage = s3_res.scalar_one_or_none()
        if not s3_storage:
            s3_storage = StorageControl(
                id=uuid.uuid7(),
                app_head_id=core_head_id,
                storage_name="s3-ledger-daily-audit-vault",
                storage_type=StorageTypeEnum.S3_BUCKET,
                encryption_algorithm=EncryptionAlgorithmEnum.AWS_KMS_CMK,
                kms_key_arn="arn:aws:kms:us-east-1:109210001234:key/mrk-8922-vault-cmk",
                retention_period_days=365,
                purge_mechanism=PurgeMechanismEnum.HARD_DELETE_REMOVAL,
                legal_hold_active=False,
                last_purge_attestation_at=now - timedelta(days=28),
                last_purge_attested_by=app_owner_id,
            )
            session.add(s3_storage)
            await session.flush()
            print("Seeded Storage: s3-ledger-daily-audit-vault")

        # 3. Seed Physical Tables & Columns
        # Table 1: public.accounts
        tbl_acc_res = await session.execute(
            select(PhysicalTable).where(
                PhysicalTable.app_head_id == core_head_id,
                PhysicalTable.table_name == "accounts",
            )
        )
        tbl_acc = tbl_acc_res.scalar_one_or_none()
        if not tbl_acc:
            tbl_acc = PhysicalTable(
                id=uuid.uuid7(),
                app_head_id=core_head_id,
                storage_control_id=pg_storage.id,
                schema_name="public",
                table_name="accounts",
                row_count_estimate=1450000,
                is_active=True,
            )
            session.add(tbl_acc)
            await session.flush()

            cols = [
                ("account_id", "UUID", False, DriftStatusEnum.SYNCED, False, MaskingStrategyEnum.NONE, ISRClassificationEnum.INTERNAL, "Account Identifier"),
                ("customer_id", "UUID", False, DriftStatusEnum.SYNCED, False, MaskingStrategyEnum.NONE, ISRClassificationEnum.INTERNAL, "Customer Master ID"),
                ("account_type", "VARCHAR(32)", False, DriftStatusEnum.SYNCED, False, MaskingStrategyEnum.NONE, ISRClassificationEnum.INTERNAL, "Account Type"),
                ("routing_num", "VARCHAR(9)", False, DriftStatusEnum.ADDED_UNCLASSIFIED, False, MaskingStrategyEnum.NONE, ISRClassificationEnum.INTERNAL, None),
                ("balance_cents", "BIGINT", False, DriftStatusEnum.SYNCED, False, MaskingStrategyEnum.NONE, ISRClassificationEnum.RESTRICTED, "Current Balance"),
                ("created_at", "TIMESTAMP", False, DriftStatusEnum.SYNCED, False, MaskingStrategyEnum.NONE, ISRClassificationEnum.INTERNAL, None),
            ]
            for col_name, dtype, null, drift, pii, mask, isr, term in cols:
                session.add(PhysicalColumn(
                    id=uuid.uuid7(),
                    table_id=tbl_acc.id,
                    column_name=col_name,
                    data_type=dtype,
                    is_nullable=null,
                    drift_status=drift,
                    is_pii=pii,
                    masking_strategy=mask,
                    isr_classification=isr,
                    business_term_name=term,
                ))
            await session.flush()
            print("Seeded Table: public.accounts with columns")

        # Table 2: public.card_transactions
        tbl_tx_res = await session.execute(
            select(PhysicalTable).where(
                PhysicalTable.app_head_id == core_head_id,
                PhysicalTable.table_name == "card_transactions",
            )
        )
        tbl_tx = tbl_tx_res.scalar_one_or_none()
        if not tbl_tx:
            tbl_tx = PhysicalTable(
                id=uuid.uuid7(),
                app_head_id=core_head_id,
                storage_control_id=pg_storage.id,
                schema_name="public",
                table_name="card_transactions",
                row_count_estimate=24800000,
                is_active=True,
            )
            session.add(tbl_tx)
            await session.flush()

            cols = [
                ("transaction_id", "UUID", False, DriftStatusEnum.SYNCED, False, MaskingStrategyEnum.NONE, ISRClassificationEnum.INTERNAL, "Transaction ID"),
                ("card_pan", "VARCHAR(19)", False, DriftStatusEnum.ADDED_UNCLASSIFIED, True, MaskingStrategyEnum.NONE, ISRClassificationEnum.HIGHLY_RESTRICTED, None),
                ("amount_cents", "BIGINT", False, DriftStatusEnum.SYNCED, False, MaskingStrategyEnum.NONE, ISRClassificationEnum.RESTRICTED, "Transaction Amount"),
                ("merchant_name", "VARCHAR(128)", True, DriftStatusEnum.SYNCED, False, MaskingStrategyEnum.NONE, ISRClassificationEnum.INTERNAL, "Merchant Entity"),
                ("cvv_code", "VARCHAR(4)", True, DriftStatusEnum.ADDED_UNCLASSIFIED, True, MaskingStrategyEnum.NONE, ISRClassificationEnum.HIGHLY_RESTRICTED, None),
                ("settled_at", "TIMESTAMP", False, DriftStatusEnum.SYNCED, False, MaskingStrategyEnum.NONE, ISRClassificationEnum.INTERNAL, None),
            ]
            for col_name, dtype, null, drift, pii, mask, isr, term in cols:
                session.add(PhysicalColumn(
                    id=uuid.uuid7(),
                    table_id=tbl_tx.id,
                    column_name=col_name,
                    data_type=dtype,
                    is_nullable=null,
                    drift_status=drift,
                    is_pii=pii,
                    masking_strategy=mask,
                    isr_classification=isr,
                    business_term_name=term,
                ))
            await session.flush()
            print("Seeded Table: public.card_transactions with columns")

        # Table 3: public.customer_profiles
        tbl_cust_res = await session.execute(
            select(PhysicalTable).where(
                PhysicalTable.app_head_id == core_head_id,
                PhysicalTable.table_name == "customer_profiles",
            )
        )
        tbl_cust = tbl_cust_res.scalar_one_or_none()
        tax_col_id = None
        if not tbl_cust:
            tbl_cust = PhysicalTable(
                id=uuid.uuid7(),
                app_head_id=core_head_id,
                storage_control_id=pg_storage.id,
                schema_name="public",
                table_name="customer_profiles",
                row_count_estimate=890000,
                is_active=True,
            )
            session.add(tbl_cust)
            await session.flush()

            tax_col_id = uuid.uuid7()
            cols = [
                (uuid.uuid7(), "customer_id", "UUID", False, DriftStatusEnum.SYNCED, False, MaskingStrategyEnum.NONE, ISRClassificationEnum.INTERNAL, "Customer ID"),
                (uuid.uuid7(), "full_name", "VARCHAR(128)", False, DriftStatusEnum.SYNCED, True, MaskingStrategyEnum.PARTIAL_MASK, ISRClassificationEnum.RESTRICTED, "Legal Customer Name"),
                (tax_col_id, "national_tax_id", "VARCHAR(20)", False, DriftStatusEnum.SYNCED, True, MaskingStrategyEnum.NONE, ISRClassificationEnum.HIGHLY_RESTRICTED, "Social Security / Tax Number"),
                (uuid.uuid7(), "email_address", "VARCHAR(128)", False, DriftStatusEnum.SYNCED, True, MaskingStrategyEnum.PARTIAL_MASK, ISRClassificationEnum.RESTRICTED, "Contact Email"),
            ]
            for cid, col_name, dtype, null, drift, pii, mask, isr, term in cols:
                session.add(PhysicalColumn(
                    id=cid,
                    table_id=tbl_cust.id,
                    column_name=col_name,
                    data_type=dtype,
                    is_nullable=null,
                    drift_status=drift,
                    is_pii=pii,
                    masking_strategy=mask,
                    isr_classification=isr,
                    business_term_name=term,
                ))
            await session.flush()
            print("Seeded Table: public.customer_profiles with columns")
        else:
            tax_res = await session.execute(
                select(PhysicalColumn).where(
                    PhysicalColumn.table_id == tbl_cust.id,
                    PhysicalColumn.column_name == "national_tax_id",
                )
            )
            tax_col = tax_res.scalar_one_or_none()
            if tax_col:
                tax_col_id = tax_col.id

        # 4. Seed Harvest Run
        harvest_res = await session.execute(
            select(SchemaHarvestRun).where(SchemaHarvestRun.app_head_id == core_head_id)
        )
        if not harvest_res.scalar_one_or_none():
            hrun = SchemaHarvestRun(
                id=uuid.uuid7(),
                app_head_id=core_head_id,
                storage_control_id=pg_storage.id,
                status=HarvestStatusEnum.COMPLETED,
                drift_detected=True,
                drift_summary={
                    "tables_scanned": 3,
                    "columns_scanned": 16,
                    "added_unclassified": 3,
                    "dropped": 0,
                    "type_modified": 0,
                },
                harvested_at=now - timedelta(hours=3),
                harvested_by=app_owner_id,
            )
            session.add(hrun)
            print("Seeded SchemaHarvestRun")

        # 5. Seed Usage Entitlements
        if fraud_app:
            ent1_res = await session.execute(
                select(UsageEntitlement).where(
                    UsageEntitlement.app_head_id == core_head_id,
                    UsageEntitlement.consumer_app_head_id == fraud_app.asset_head_id,
                )
            )
            if not ent1_res.scalar_one_or_none():
                session.add(UsageEntitlement(
                    id=uuid.uuid7(),
                    app_head_id=core_head_id,
                    consumer_app_head_id=fraud_app.asset_head_id,
                    authorized_purpose="Real-time AML & Fraud Transaction Scoring",
                    allowed_geo_regions=["US", "EU"],
                    is_active=True,
                    approved_by=steward_id,
                    expires_at=now + timedelta(days=270),
                ))
                print("Seeded Entitlement for Fraud Engine")

        if reg_app:
            ent2_res = await session.execute(
                select(UsageEntitlement).where(
                    UsageEntitlement.app_head_id == core_head_id,
                    UsageEntitlement.consumer_app_head_id == reg_app.asset_head_id,
                )
            )
            if not ent2_res.scalar_one_or_none():
                session.add(UsageEntitlement(
                    id=uuid.uuid7(),
                    app_head_id=core_head_id,
                    consumer_app_head_id=reg_app.asset_head_id,
                    authorized_purpose="Daily Basel III & Dodd-Frank Capital Adequacy Calculation",
                    allowed_geo_regions=["US"],
                    is_active=True,
                    approved_by=steward_id,
                    expires_at=now + timedelta(days=180),
                ))
                print("Seeded Entitlement for Regulatory Reporting")

        # 6. Seed / Update Actionable Compliance Defects with Live SLA Timers
        # Find the ungoverned integration INT-009412
        integ_res = await session.execute(
            select(ApplicationIntegration).where(ApplicationIntegration.itsm_integration_id == "INT-009412")
        )
        integ_009412 = integ_res.scalar_one_or_none()

        # DEFECT 1: MOV_001 (CRITICAL - 2 days SLA remaining)
        m1_res = await session.execute(
            select(ComplianceIssue).where(
                ComplianceIssue.app_head_id == core_head_id,
                ComplianceIssue.rule_code == "MOV_001",
            )
        )
        m1 = m1_res.scalar_one_or_none()
        if not m1 and integ_009412:
            session.add(ComplianceIssue(
                id=uuid.uuid7(),
                target_asset_head_id=integ_009412.asset_head_id,
                app_head_id=core_head_id,
                rule_code="MOV_001",
                integration_id=integ_009412.id,
                title="MOV_001: Missing Certified Transfer Integrity Pattern on INT-009412",
                description="Kafka streaming integration INT-009412 to Enterprise Fraud Engine lacks a certified transfer integrity pattern (e.g. SHA-256 Checksum, Idempotent Deduplication).",
                severity=IssueSeverityEnum.CRITICAL,
                status=IssueStatusEnum.OPEN,
                remediation_deadline=now + timedelta(days=2, hours=3),
                app_owner_id=app_owner_id,
                created_by=steward_id,
            ))
            print("Seeded Defect MOV_001")

        # DEFECT 2: DRIFT_001 (HIGH - 4 days SLA remaining)
        d1_res = await session.execute(
            select(ComplianceIssue).where(
                ComplianceIssue.app_head_id == core_head_id,
                ComplianceIssue.rule_code == "DRIFT_001",
            )
        )
        if not d1_res.scalar_one_or_none():
            session.add(ComplianceIssue(
                id=uuid.uuid7(),
                target_asset_head_id=core_head_id,
                app_head_id=core_head_id,
                rule_code="DRIFT_001",
                title="DRIFT_001: Unclassified Physical Columns Harvested from Database",
                description="Schema harvest detected 3 unclassified physical columns (card_pan, routing_num, cvv_code). Requires PII tagging, masking policy, and ISR classification.",
                severity=IssueSeverityEnum.HIGH,
                status=IssueStatusEnum.OPEN,
                remediation_deadline=now + timedelta(days=4, hours=12),
                app_owner_id=app_owner_id,
                created_by=steward_id,
            ))
            print("Seeded Defect DRIFT_001")

        # DEFECT 3: STOR_001 (HIGH - 1 day SLA remaining - Breaching soon!)
        s1_res = await session.execute(
            select(ComplianceIssue).where(
                ComplianceIssue.app_head_id == core_head_id,
                ComplianceIssue.rule_code == "STOR_001",
            )
        )
        if not s1_res.scalar_one_or_none() and pg_storage:
            session.add(ComplianceIssue(
                id=uuid.uuid7(),
                target_asset_head_id=core_head_id,
                app_head_id=core_head_id,
                rule_code="STOR_001",
                storage_control_id=pg_storage.id,
                title="STOR_001: Retention Purge Attestation Overdue for pg-core-ledger-db",
                description="Storage repository pg-core-ledger-db has 90-day retention window, but last purge attestation occurred 104 days ago. Purge cycle must be certified.",
                severity=IssueSeverityEnum.HIGH,
                status=IssueStatusEnum.OPEN,
                remediation_deadline=now + timedelta(days=1, hours=5),
                app_owner_id=app_owner_id,
                created_by=steward_id,
            ))
            print("Seeded Defect STOR_001")

        # DEFECT 4: PRIV_001 (MEDIUM - 3 days SLA remaining)
        p1_res = await session.execute(
            select(ComplianceIssue).where(
                ComplianceIssue.app_head_id == core_head_id,
                ComplianceIssue.rule_code == "PRIV_001",
            )
        )
        if not p1_res.scalar_one_or_none() and tax_col_id:
            session.add(ComplianceIssue(
                id=uuid.uuid7(),
                target_asset_head_id=core_head_id,
                app_head_id=core_head_id,
                rule_code="PRIV_001",
                column_id=tax_col_id,
                title="PRIV_001: PII Column national_tax_id Lacks Masking Strategy",
                description="Column public.customer_profiles.national_tax_id is flagged as PII with HIGHLY_RESTRICTED tier but masking strategy is set to NONE.",
                severity=IssueSeverityEnum.MEDIUM,
                status=IssueStatusEnum.OPEN,
                remediation_deadline=now + timedelta(days=3, hours=8),
                app_owner_id=app_owner_id,
                created_by=steward_id,
            ))
            print("Seeded Defect PRIV_001")

        await session.commit()
        print("Workbench seed completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_workbench())
