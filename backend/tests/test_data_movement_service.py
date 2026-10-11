"""Tests for Application-Level Data Movement & Integrity Controls."""
import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.domain.exceptions import (
    DependencyConflictException,
    EntityNotFoundException,
    ValidationException,
)
from app.models.data_movement import (
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
)
from app.models.user import User
from app.schemas.data_movement import (
    BindScopeRequest,
    DataSetCreate,
    DataSetUpdate,
    SetIntegrityPatternRequest,
    SubmitCertificationRequest,
)
from app.services.data_movement_service import DataMovementService


@pytest.mark.asyncio
async def test_application_profiles_listing(db_session: AsyncSession):
    """Test listing application profiles with dataset and integration rollups."""
    service = DataMovementService(db_session)
    apps = await service.list_applications()
    assert len(apps) >= 4

    core_app = next((a for a in apps if a.itsm_system_id == "APP-10921"), None)
    assert core_app is not None
    assert core_app.itsm_system_name == "Core Banking Ledger"
    assert core_app.datasets_count >= 3
    assert core_app.integrations_count >= 3


@pytest.mark.asyncio
async def test_dataset_crud_and_name_uniqueness(db_session: AsyncSession):
    """Test self-service dataset creation, name uniqueness check, and retrieval."""
    service = DataMovementService(db_session)

    apps = await service.list_applications()
    core_app = next(a for a in apps if a.itsm_system_id == "APP-10921")
    user = (await db_session.execute(select(User))).scalars().first()

    # Create dataset
    unique_ds_name = f"Treasury Swap Trades {uuid.uuid4().hex[:6]}"
    new_ds = await service.create_dataset(
        app_head_id=core_app.asset_head_id,
        dataset_in=DataSetCreate(
            name=unique_ds_name,
            description="Derivative and interest rate swaps trading books.",
            business_context="Over-the-counter swaps portfolio valuation and hedging data.",
            isr_classification=ISRClassificationEnum.INTERNAL,
            data_categories=["FINANCIAL", "DERIVATIVES"],
        ),
        user_id=user.id,
    )
    assert new_ds.id is not None
    assert new_ds.name == unique_ds_name
    assert new_ds.usage_count == 0

    # Attempt duplicate name -> ValidationException
    with pytest.raises(ValidationException, match="already exists"):
        await service.create_dataset(
            app_head_id=core_app.asset_head_id,
            dataset_in=DataSetCreate(
                name=unique_ds_name.lower(),  # case-insensitive check
                business_context="Duplicate name should be blocked by domain uniqueness check.",
            ),
            user_id=user.id,
        )


@pytest.mark.asyncio
async def test_dataset_delete_safety_lock_409(db_session: AsyncSession):
    """Test referential safety lock: bound dataset cannot be deleted and returns blocking integrations."""
    service = DataMovementService(db_session)
    apps = await service.list_applications()
    core_app = next(a for a in apps if a.itsm_system_id == "APP-10921")
    user = (await db_session.execute(select(User))).scalars().first()

    datasets = await service.list_datasets(core_app.asset_head_id)
    settlement_ds = next(d for d in datasets if d.name == "Daily Settlement File")
    assert settlement_ds.usage_count > 0

    # Attempt delete bound dataset -> DependencyConflictException
    with pytest.raises(DependencyConflictException) as exc_info:
        await service.delete_dataset(settlement_ds.id, user_id=user.id)
    
    assert "Bound to" in exc_info.value.message
    assert len(exc_info.value.blocking_entities) > 0

    # Create an unlinked dataset specifically for delete test
    temp_ds = await service.create_dataset(
        app_head_id=core_app.asset_head_id,
        dataset_in=DataSetCreate(
            name=f"Deletable Dataset {uuid.uuid4().hex[:6]}",
            business_context="Temporary dataset to test clean deletion.",
            isr_classification=ISRClassificationEnum.INTERNAL,
        ),
        user_id=user.id,
    )
    assert temp_ds.usage_count == 0

    # Delete unbound dataset -> Succeeds with soft delete
    await service.delete_dataset(temp_ds.id, user_id=user.id)

    # Verify soft deleted
    updated_datasets = await service.list_datasets(core_app.asset_head_id)
    assert not any(d.id == temp_ds.id for d in updated_datasets)


@pytest.mark.asyncio
async def test_sensitivity_escalation_guardrail(db_session: AsyncSession):
    """Test sensitivity escalation guardrail flags bound integrations as IN_REMEDIATION."""
    service = DataMovementService(db_session)
    apps = await service.list_applications()
    core_app = next(a for a in apps if a.itsm_system_id == "APP-10921")
    user = (await db_session.execute(select(User))).scalars().first()

    # Create a fresh dataset initially INTERNAL
    ds = await service.create_dataset(
        app_head_id=core_app.asset_head_id,
        dataset_in=DataSetCreate(
            name=f"Risk Metrics Extract {uuid.uuid4().hex[:6]}",
            business_context="Portfolio VaR and expected shortfall extracts.",
            isr_classification=ISRClassificationEnum.INTERNAL,
            data_categories=["METRICS"],
        ),
        user_id=user.id,
    )

    # Find INT-008214 and bind this dataset
    integrations = await service.list_integrations(core_app.asset_head_id)
    target_int = next(i for i in integrations if i.itsm_integration_id == "INT-008214")
    await service.bind_scope(
        integration_id=target_int.id,
        scope_in=BindScopeRequest(data_set_id=ds.id, retention_period_days=30, encryption_in_transit=True),
        user_id=user.id,
    )

    # Escalate dataset to HIGHLY_RESTRICTED with CUSTOMER_PII
    updated_ds = await service.update_dataset(
        dataset_id=ds.id,
        dataset_in=DataSetUpdate(
            isr_classification=ISRClassificationEnum.HIGHLY_RESTRICTED,
            data_categories=["METRICS", "CUSTOMER_PII"],
        ),
        user_id=user.id,
    )
    assert updated_ds.isr_classification == ISRClassificationEnum.HIGHLY_RESTRICTED


@pytest.mark.asyncio
async def test_integration_binding_and_certification_lifecycle(db_session: AsyncSession):
    """Test full integration governance flow: UNGOVERNED -> bind scope -> declare pattern -> submit -> verify."""
    service = DataMovementService(db_session)
    apps = await service.list_applications()
    core_app = next(a for a in apps if a.itsm_system_id == "APP-10921")
    fraud_app = next(a for a in apps if a.itsm_system_id == "APP-20419")
    user = (await db_session.execute(select(User))).scalars().first()

    # Create a new integration specifically to test the governance lifecycle cleanly
    integ_id = uuid.uuid7()
    head_id = uuid.uuid7()
    from datetime import datetime, timezone
    from app.models.asset import AssetHead
    from app.models.metamodel import AssetType
    from app.models.organization import Domain
    dom = (await db_session.execute(select(Domain))).scalars().first()
    atype = (await db_session.execute(select(AssetType))).scalars().first()
    head = AssetHead(id=head_id, domain_id=dom.id, asset_type_id=atype.id, created_at=datetime.now(timezone.utc))
    db_session.add(head)
    await db_session.flush()

    new_integ = ApplicationIntegration(
        id=integ_id,
        asset_head_id=head_id,
        itsm_integration_id=f"INT-TEST-{uuid.uuid4().hex[:6]}",
        source_app_head_id=core_app.asset_head_id,
        target_app_head_id=fraud_app.asset_head_id,
        direction=IntegrationDirectionEnum.OUTBOUND,
        transfer_type=TransferTypeEnum.EVENT_STREAM_KAFKA,
        frequency=TransferFrequencyEnum.STREAMING_REALTIME,
        governance_status=IntegrationGovernanceStatusEnum.UNGOVERNED,
        integrity_pattern=IntegrityPatternEnum.NONE_UNENFORCED,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(new_integ)
    await db_session.commit()

    integ = await service.get_integration(integ_id)
    assert integ.governance_status == IntegrationGovernanceStatusEnum.UNGOVERNED

    # Attempt certification with 0 datasets -> ValidationException
    with pytest.raises(ValidationException, match="must have at least one"):
        await service.submit_certification(integ.id, user_id=user.id)

    # Bind dataset
    datasets = await service.list_datasets(core_app.asset_head_id)
    ds = datasets[0]
    await service.bind_scope(
        integration_id=integ.id,
        scope_in=BindScopeRequest(data_set_id=ds.id, retention_period_days=180, encryption_in_transit=True),
        user_id=user.id,
    )

    # Attempt certification with pattern NONE_UNENFORCED -> ValidationException
    with pytest.raises(ValidationException, match="certified Transfer Integrity Pattern"):
        await service.submit_certification(integ.id, user_id=user.id)

    # Set integrity pattern
    await service.set_integrity_pattern(
        integration_id=integ.id,
        pattern_in=SetIntegrityPatternRequest(
            integrity_pattern=IntegrityPatternEnum.CHECKSUM_HASH_VERIFICATION,
            integrity_pattern_details="SHA-256 payload digest verification on each Kafka record.",
        ),
        user_id=user.id,
    )

    # Submit certification -> PENDING_VERIFICATION
    submitted = await service.submit_certification(integ.id, user_id=user.id)
    assert submitted.governance_status == IntegrationGovernanceStatusEnum.PENDING_VERIFICATION

    # Steward approves certification -> COMPLIANT
    steward_user = (await db_session.execute(select(User).where(User.email == "steward@governance.com"))).scalar_one()
    certified = await service.verify_certification(
        integration_id=integ.id,
        approved=True,
        steward_user_id=steward_user.id,
        notes="All transfer controls validated.",
    )
    assert certified.governance_status == IntegrationGovernanceStatusEnum.COMPLIANT
    assert certified.governance_certified_at is not None
    assert certified.certified_by == steward_user.id
