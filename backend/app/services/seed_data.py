import asyncio
import sys
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models import (
    User,
    GovernanceRole,
    Community,
    Domain,
    DomainTypeEnum,
    AssetType,
    AttributeType,
    AttributeDataType,
    AssetTypeAttributeAssignment,
    RelationType,
    WorkflowDefinition,
    WorkflowStage,
    AssetHead,
    AssetVersion,
    VersionStatusEnum,
    ApplicationProfile,
    DataSet,
    ApplicationIntegration,
    DataMovementScope,
    IntegrationDirectionEnum,
    TransferTypeEnum,
    TransferFrequencyEnum,
    IntegrityPatternEnum,
    ISRClassificationEnum,
    IntegrationGovernanceStatusEnum,
    ComplianceIssue,
    IssueSeverityEnum,
    IssueStatusEnum,
)
import uuid
from datetime import datetime, timezone, timedelta


async def seed_governance_roles(session: AsyncSession) -> dict[str, GovernanceRole]:
    roles_data = [
        ("PLATFORM_ADMIN", "Platform Administrator", "Global Administrative Superuser with full metamodel and system permissions."),
        ("DATA_STEWARD", "Data Steward", "Curates terminology, verifies compliance evidence, reviews proposals and metamodels."),
        ("BUSINESS_OWNER", "Business / Domain Owner", "Domain definition accountability, signs off on publication and exceptions."),
        ("APP_OWNER", "Application / System Owner", "Remediates compliance defects and manages registered applications."),
        ("DATA_CONSUMER", "Data Consumer", "Discovers approved assets, proposes terms, and flags compliance issues."),
    ]
    created = {}
    for code, name, desc in roles_data:
        res = await session.execute(select(GovernanceRole).where(GovernanceRole.code == code))
        role = res.scalar_one_or_none()
        if not role:
            role = GovernanceRole(code=code, name=name, description=desc)
            session.add(role)
            await session.flush()
        created[code] = role
    return created


async def seed_users(session: AsyncSession) -> dict[str, User]:
    default_password_hash = get_password_hash("password123")
    users_data = [
        ("admin@governance.com", "Alex Mercer (Admin)", True, default_password_hash),
        ("steward@governance.com", "Sarah Chen (Data Steward)", False, default_password_hash),
        ("business.owner@governance.com", "David Vance (Domain Owner)", False, default_password_hash),
        ("app.owner@governance.com", "Elena Rostova (System Owner)", False, default_password_hash),
        ("consumer@governance.com", "Jordan Patel (Data Consumer)", False, default_password_hash),
    ]
    created = {}
    for email, full_name, is_superuser, pwd_hash in users_data:
        res = await session.execute(select(User).where(User.email == email))
        user = res.scalar_one_or_none()
        if not user:
            user = User(
                email=email,
                full_name=full_name,
                hashed_password=pwd_hash,
                is_superuser=is_superuser,
                is_active=True,
            )
            session.add(user)
            await session.flush()
        created[email] = user
    return created


async def seed_metamodel(session: AsyncSession):
    # 1. Attribute Types
    attributes = [
        ("DEFINITION", "Definition / Description", AttributeDataType.MARKDOWN, None, "Authoritative markdown definition."),
        ("CRITICALITY", "Criticality Tier", AttributeDataType.ENUM, ["LOW", "MEDIUM", "HIGH", "CRITICAL"], "Operational criticality level."),
        ("CONFIDENTIALITY", "Confidentiality Classification", AttributeDataType.ENUM, ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"], "Information security confidentiality rating."),
        ("PII", "Contains PII", AttributeDataType.BOOLEAN, None, "Flag indicating Personally Identifiable Information presence."),
        ("DATA_OWNER", "Data Owner Name", AttributeDataType.STRING, None, "Designated business owner designation."),
    ]
    attr_map = {}
    for code, name, data_type, allowed, desc in attributes:
        res = await session.execute(select(AttributeType).where(AttributeType.code == code))
        attr = res.scalar_one_or_none()
        if not attr:
            attr = AttributeType(
                code=code,
                name=name,
                data_type=data_type,
                allowed_values=allowed,
                description=desc,
            )
            session.add(attr)
            await session.flush()
        attr_map[code] = attr

    # 2. Asset Types
    types_data = [
        ("BUSINESS_TERM", "Business Term", "Authoritative business vocabulary term and definition.", "BookOpen"),
        ("DATA_POLICY", "Data Policy", "Regulatory rule or enterprise governance mandate.", "ShieldCheck"),
        ("APPLICATION", "Application", "Core service, database, or software system.", "Server"),
        ("REPORT", "Report / Dashboard", "Analytical report, BI dataset, or executive dashboard.", "BarChart3"),
        ("METRIC", "Business Metric", "Standardized calculation KPI or scorecard metric.", "Activity"),
    ]
    type_map = {}
    for code, name, desc, icon in types_data:
        res = await session.execute(select(AssetType).where(AssetType.code == code))
        atype = res.scalar_one_or_none()
        if not atype:
            atype = AssetType(code=code, name=name, description=desc, icon=icon)
            session.add(atype)
            await session.flush()
        type_map[code] = atype

    # 3. Attribute Assignments to Asset Types
    assignments = [
        ("BUSINESS_TERM", "DEFINITION", True, 0),
        ("BUSINESS_TERM", "CONFIDENTIALITY", False, 1),
        ("BUSINESS_TERM", "PII", False, 2),
        ("APPLICATION", "CRITICALITY", True, 0),
        ("APPLICATION", "CONFIDENTIALITY", True, 1),
        ("APPLICATION", "DATA_OWNER", False, 2),
        ("DATA_POLICY", "DEFINITION", True, 0),
    ]
    for type_code, attr_code, is_req, order in assignments:
        atype = type_map[type_code]
        attr = attr_map[attr_code]
        res = await session.execute(
            select(AssetTypeAttributeAssignment).where(
                AssetTypeAttributeAssignment.asset_type_id == atype.id,
                AssetTypeAttributeAssignment.attribute_type_id == attr.id,
            )
        )
        if not res.scalar_one_or_none():
            assignment = AssetTypeAttributeAssignment(
                asset_type_id=atype.id,
                attribute_type_id=attr.id,
                is_required=is_req,
                display_order=order,
            )
            session.add(assignment)

    # 4. Relation Types
    relations = [
        ("CLASSIFIES", type_map["BUSINESS_TERM"].id, type_map["APPLICATION"].id, "Classifies", "Is Classified By", "Semantic classification of an application by a business term."),
        ("GOVERNS", type_map["DATA_POLICY"].id, type_map["APPLICATION"].id, "Governs", "Is Governed By", "Policy mandate compliance relationship."),
        ("DEPENDS_ON", type_map["APPLICATION"].id, type_map["APPLICATION"].id, "Depends On", "Is Dependency Of", "Technical dependency between applications."),
        ("CONSUMES", type_map["REPORT"].id, type_map["APPLICATION"].id, "Consumes", "Is Consumed By", "Downstream analytical reporting ingestion."),
    ]
    for code, src_id, tgt_id, role, co_role, desc in relations:
        res = await session.execute(select(RelationType).where(RelationType.code == code))
        if not res.scalar_one_or_none():
            rel = RelationType(
                code=code,
                source_asset_type_id=src_id,
                target_asset_type_id=tgt_id,
                role_name=role,
                co_role_name=co_role,
                description=desc,
            )
            session.add(rel)

    # 5. Workflow Definitions & Stages
    res = await session.execute(select(WorkflowDefinition).where(WorkflowDefinition.name == "Standard Business Term Approval"))
    wf_term = res.scalar_one_or_none()
    if not wf_term:
        wf_term = WorkflowDefinition(
            name="Standard Business Term Approval",
            asset_type_id=type_map["BUSINESS_TERM"].id,
            is_active=True,
        )
        session.add(wf_term)
        await session.flush()

        stages = [
            (1, "Technical Steward Review", "DATA_STEWARD", False, 24),
            (2, "Business Steward Review", "DATA_STEWARD", False, 48),
            (3, "Domain Owner Sign-Off", "BUSINESS_OWNER", False, 72),
        ]
        for order, name, role, is_consensus, sla in stages:
            stage = WorkflowStage(
                workflow_definition_id=wf_term.id,
                stage_order=order,
                name=name,
                required_role=role,
                is_consensus=is_consensus,
                sla_hours=sla,
            )
            session.add(stage)


async def seed_communities_and_domains(session: AsyncSession):
    # Root Community
    res = await session.execute(select(Community).where(Community.name == "Enterprise Data Governance"))
    root_comm = res.scalar_one_or_none()
    if not root_comm:
        root_comm = Community(
            name="Enterprise Data Governance",
            description="Root organizational scope for enterprise governance standards and taxonomy."
        )
        session.add(root_comm)
        await session.flush()

    # Division Community
    res = await session.execute(select(Community).where(Community.name == "Finance & Corporate Services"))
    fin_comm = res.scalar_one_or_none()
    if not fin_comm:
        fin_comm = Community(
            name="Finance & Corporate Services",
            description="Division governing financial definitions, general ledger systems, and compliance.",
            parent_community_id=root_comm.id
        )
        session.add(fin_comm)
        await session.flush()

    # Domains
    domains_data = [
        ("Finance Glossary", DomainTypeEnum.GLOSSARY, "Authoritative business terms for finance, accounting, and taxation."),
        ("Core Banking Systems", DomainTypeEnum.SYSTEMS_REGISTER, "Inventory of applications, payment engines, and ledger datastores."),
        ("Financial Compliance Policies", DomainTypeEnum.POLICY, "SOX, Basel III, and internal data retention policies."),
        ("Treasury KPI Metrics", DomainTypeEnum.METRIC_STORE, "Liquidity coverage, net interest margin, and capital adequacy metrics."),
    ]
    for dname, dtype, ddesc in domains_data:
        res = await session.execute(
            select(Domain).where(Domain.community_id == fin_comm.id, Domain.name == dname)
        )
        if not res.scalar_one_or_none():
            domain = Domain(
                community_id=fin_comm.id,
                name=dname,
                domain_type=dtype,
                description=ddesc,
            )
            session.add(domain)


async def seed_data_movement_controls(session: AsyncSession):
    """Seed authoritative CMDB Applications, Application Datasets, Integrations & Scopes."""
    # 1. Lookup App Owner & Steward
    res = await session.execute(select(User).where(User.email == "app.owner@governance.com"))
    app_owner = res.scalar_one_or_none()
    res = await session.execute(select(User).where(User.email == "steward@governance.com"))
    steward = res.scalar_one_or_none()

    # 2. Lookup Core Banking Systems Domain & APPLICATION AssetType
    res = await session.execute(select(Domain).where(Domain.name == "Core Banking Systems"))
    domain = res.scalar_one_or_none()
    res = await session.execute(select(AssetType).where(AssetType.code == "APPLICATION"))
    app_type = res.scalar_one_or_none()

    if not app_owner or not steward or not domain or not app_type:
        return

    now = datetime.now(timezone.utc)

    # 3. Create Applications
    apps_data = [
        ("APP-10921", "Core Banking Ledger", "TIER_1", "Central accounting ledger, deposit accounts, and settlement processing engine."),
        ("APP-20419", "Enterprise Fraud Detection Engine", "TIER_1", "Real-time AI/ML behavioral anomaly and payment fraud scoring."),
        ("APP-30112", "Global CRM & Client Portal", "TIER_2", "Customer master relationship management and omnichannel servicing."),
        ("APP-40881", "Regulatory Reporting Warehouse", "TIER_1", "Basel III, Dodd-Frank, and statutory reporting aggregation repository."),
    ]

    app_heads = {}
    for itsm_id, name, crit, desc in apps_data:
        res = await session.execute(select(ApplicationProfile).where(ApplicationProfile.itsm_system_id == itsm_id))
        existing_profile = res.scalar_one_or_none()
        if not existing_profile:
            head_id = uuid.uuid7()
            version_id = uuid.uuid7()
            head = AssetHead(
                id=head_id,
                domain_id=domain.id,
                asset_type_id=app_type.id,
                published_version_id=None,
                created_at=now,
            )
            session.add(head)
            await session.flush()

            version = AssetVersion(
                id=version_id,
                asset_head_id=head_id,
                version_number=1,
                status=VersionStatusEnum.PUBLISHED,
                name=name,
                description_markdown=f"# {name}\n\n{desc}",
                attributes_payload={"CRITICALITY": crit},
                relations_snapshot=[],
                created_by=app_owner.id,
                created_at=now,
                published_at=now,
            )
            session.add(version)
            await session.flush()

            head.published_version_id = version_id
            head.published_version = version
            await session.flush()

            profile = ApplicationProfile(
                id=uuid.uuid7(),
                asset_head_id=head_id,
                itsm_system_id=itsm_id,
                itsm_system_name=name,
                cmdb_criticality=crit,
                app_owner_id=app_owner.id,
                synced_at=now - timedelta(days=2),
            )
            session.add(profile)
            await session.flush()
            app_heads[itsm_id] = head_id
        else:
            app_heads[itsm_id] = existing_profile.asset_head_id

    core_app_head_id = app_heads.get("APP-10921")
    fraud_app_head_id = app_heads.get("APP-20419")
    crm_app_head_id = app_heads.get("APP-30112")
    reg_app_head_id = app_heads.get("APP-40881")

    if not core_app_head_id:
        return

    # 4. Create Datasets for Core Banking Ledger
    datasets_data = [
        (
            "Daily Settlement File",
            "End-of-day multi-currency clearing and settlement balances for retail and commercial accounts.",
            ISRClassificationEnum.RESTRICTED,
            ["CUSTOMER_PII", "FINANCIAL", "SETTLEMENT"],
        ),
        (
            "Branch Cash Ledger",
            "Physical cash intake, vault reserves, and teller balance sheets across branch networks.",
            ISRClassificationEnum.INTERNAL,
            ["FINANCIAL", "BRANCH_OPERATIONS"],
        ),
        (
            "Audit Reconciliation Log",
            "Internal and external auditor ledger trace entries and balance verification logs.",
            ISRClassificationEnum.INTERNAL,
            ["AUDIT", "COMPLIANCE"],
        ),
    ]

    dataset_objs = {}
    for dname, bcontext, isr, cats in datasets_data:
        res = await session.execute(
            select(DataSet).where(DataSet.app_head_id == core_app_head_id, DataSet.name == dname)
        )
        ds = res.scalar_one_or_none()
        if not ds:
            head_id = uuid.uuid7()
            version_id = uuid.uuid7()
            head = AssetHead(
                id=head_id,
                domain_id=domain.id,
                asset_type_id=app_type.id,
                published_version_id=None,
                created_at=now,
            )
            session.add(head)
            await session.flush()

            version = AssetVersion(
                id=version_id,
                asset_head_id=head_id,
                version_number=1,
                status=VersionStatusEnum.PUBLISHED,
                name=dname,
                description_markdown=f"# {dname}\n\n{bcontext}",
                attributes_payload={"ISR_CLASSIFICATION": isr.value, "DATA_CATEGORIES": cats},
                relations_snapshot=[],
                created_by=app_owner.id,
                created_at=now,
                published_at=now,
            )
            session.add(version)
            await session.flush()

            head.published_version_id = version_id
            head.published_version = version
            await session.flush()

            ds = DataSet(
                id=uuid.uuid7(),
                asset_head_id=head_id,
                app_head_id=core_app_head_id,
                name=dname,
                description=f"Curated dataset for {dname}",
                business_context=bcontext,
                isr_classification=isr,
                data_categories=cats,
                created_by=app_owner.id,
                updated_by=app_owner.id,
                created_at=now,
                updated_at=now,
            )
            session.add(ds)
            await session.flush()
        dataset_objs[dname] = ds

    # 5. Create Integrations
    # INT-009412: Core Banking -> Fraud Engine (OUTBOUND, Kafka, UNGOVERNED)
    res = await session.execute(select(ApplicationIntegration).where(ApplicationIntegration.itsm_integration_id == "INT-009412"))
    if not res.scalar_one_or_none() and fraud_app_head_id:
        head_id = uuid.uuid7()
        integ_id = uuid.uuid7()
        head = AssetHead(id=head_id, domain_id=domain.id, asset_type_id=app_type.id, created_at=now)
        session.add(head)
        await session.flush()

        integ = ApplicationIntegration(
            id=integ_id,
            asset_head_id=head_id,
            itsm_integration_id="INT-009412",
            source_app_head_id=core_app_head_id,
            target_app_head_id=fraud_app_head_id,
            direction=IntegrationDirectionEnum.OUTBOUND,
            transfer_type=TransferTypeEnum.EVENT_STREAM_KAFKA,
            frequency=TransferFrequencyEnum.STREAMING_REALTIME,
            governance_status=IntegrationGovernanceStatusEnum.UNGOVERNED,
            integrity_pattern=IntegrityPatternEnum.NONE_UNENFORCED,
            created_at=now - timedelta(days=2),
        )
        session.add(integ)

        # Open compliance issue
        issue = ComplianceIssue(
            id=uuid.uuid7(),
            target_asset_head_id=head_id,
            app_owner_id=app_owner.id,
            assigned_steward_id=steward.id,
            title="Ungoverned Data Movement: ITSM Integration INT-009412 missing Data Set & Integrity Control",
            description="Integration INT-009412 connects tier-1 Core Banking Ledger to Fraud Engine without governed dataset scope or certified integrity pattern.",
            severity=IssueSeverityEnum.CRITICAL,
            status=IssueStatusEnum.OPEN,
            remediation_deadline=now + timedelta(days=12),
            created_by=steward.id,
        )
        session.add(issue)

    # INT-008214: Core Banking -> Regulatory Warehouse (OUTBOUND, ETL, COMPLIANT)
    res = await session.execute(select(ApplicationIntegration).where(ApplicationIntegration.itsm_integration_id == "INT-008214"))
    if not res.scalar_one_or_none() and reg_app_head_id:
        head_id = uuid.uuid7()
        integ_id = uuid.uuid7()
        head = AssetHead(id=head_id, domain_id=domain.id, asset_type_id=app_type.id, created_at=now)
        session.add(head)
        await session.flush()

        integ = ApplicationIntegration(
            id=integ_id,
            asset_head_id=head_id,
            itsm_integration_id="INT-008214",
            source_app_head_id=core_app_head_id,
            target_app_head_id=reg_app_head_id,
            direction=IntegrationDirectionEnum.OUTBOUND,
            transfer_type=TransferTypeEnum.BATCH_ETL,
            frequency=TransferFrequencyEnum.DAILY,
            governance_status=IntegrationGovernanceStatusEnum.COMPLIANT,
            integrity_pattern=IntegrityPatternEnum.ROW_COUNT_RECONCILIATION,
            integrity_pattern_details="Automated control balancing row counts between source staging and target landing tables.",
            governance_certified_at=now - timedelta(days=5),
            certified_by=steward.id,
            created_at=now - timedelta(days=10),
        )
        session.add(integ)
        await session.flush()

        # Bind Daily Settlement File
        if "Daily Settlement File" in dataset_objs:
            scope = DataMovementScope(
                id=uuid.uuid7(),
                integration_id=integ_id,
                data_set_id=dataset_objs["Daily Settlement File"].id,
                retention_period_days=365,
                encryption_in_transit=True,
                created_by=app_owner.id,
                created_at=now - timedelta(days=5),
            )
            session.add(scope)

    # INT-007103: Global CRM -> Core Banking (INBOUND, REST_API, PENDING_VERIFICATION)
    res = await session.execute(select(ApplicationIntegration).where(ApplicationIntegration.itsm_integration_id == "INT-007103"))
    if not res.scalar_one_or_none() and crm_app_head_id:
        head_id = uuid.uuid7()
        integ_id = uuid.uuid7()
        head = AssetHead(id=head_id, domain_id=domain.id, asset_type_id=app_type.id, created_at=now)
        session.add(head)
        await session.flush()

        integ = ApplicationIntegration(
            id=integ_id,
            asset_head_id=head_id,
            itsm_integration_id="INT-007103",
            source_app_head_id=crm_app_head_id,
            target_app_head_id=core_app_head_id,
            direction=IntegrationDirectionEnum.INBOUND,
            transfer_type=TransferTypeEnum.REST_API,
            frequency=TransferFrequencyEnum.MICRO_BATCH_NEAR_REALTIME,
            governance_status=IntegrationGovernanceStatusEnum.PENDING_VERIFICATION,
            integrity_pattern=IntegrityPatternEnum.IDEMPOTENT_DEDUPLICATION,
            integrity_pattern_details="mTLS v1.3 encryption with client idempotent message deduplication keys.",
            created_at=now - timedelta(days=1),
        )
        session.add(integ)
        await session.flush()

        # Bind Daily Settlement File & Branch Cash Ledger
        if "Daily Settlement File" in dataset_objs:
            scope1 = DataMovementScope(
                id=uuid.uuid7(),
                integration_id=integ_id,
                data_set_id=dataset_objs["Daily Settlement File"].id,
                retention_period_days=90,
                encryption_in_transit=True,
                created_by=app_owner.id,
                created_at=now - timedelta(days=1),
            )
            session.add(scope1)
        if "Branch Cash Ledger" in dataset_objs:
            scope2 = DataMovementScope(
                id=uuid.uuid7(),
                integration_id=integ_id,
                data_set_id=dataset_objs["Branch Cash Ledger"].id,
                retention_period_days=90,
                encryption_in_transit=True,
                created_by=app_owner.id,
                created_at=now - timedelta(days=1),
            )
            session.add(scope2)


async def run_seed():
    print("Beginning database seed on PostgreSQL 18 with native uuidv7()...")
    async with AsyncSessionLocal() as session:
        async with session.begin():
            print("1. Seeding Governance Roles...")
            await seed_governance_roles(session)
            print("2. Seeding Personas & Users...")
            await seed_users(session)
            print("3. Seeding Metamodel & Workflows...")
            await seed_metamodel(session)
            print("4. Seeding Organization Communities & Domains...")
            await seed_communities_and_domains(session)
            print("5. Seeding Application Data Movement Controls...")
            await seed_data_movement_controls(session)
        print("Database seed successfully completed!")


if __name__ == "__main__":
    asyncio.run(run_seed())

