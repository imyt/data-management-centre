"""Service Tier: Cohesive domain service managing Application-Level Data Movement & Integrity Controls."""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    and_,
    delete,
    func,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.exceptions import (
    DependencyConflictException,
    EntityNotFoundException,
    ValidationException,
)
from app.models.asset import AssetHead, AssetVersion, VersionStatusEnum
from app.models.compliance import (
    ComplianceIssue,
    IssueSeverityEnum,
    IssueStatusEnum,
)
from app.models.data_movement import (
    ApplicationIntegration,
    ApplicationProfile,
    DataMovementScope,
    DataSet,
    IntegrationDirectionEnum,
    IntegrationGovernanceStatusEnum,
    IntegrityPatternEnum,
    ISRClassificationEnum,
    TransferFrequencyEnum,
    TransferTypeEnum,
)
from app.models.metamodel import AssetType
from app.models.user import User
from app.schemas.data_movement import (
    ApplicationIntegrationRead,
    ApplicationProfileRead,
    BindScopeRequest,
    DataMovementScopeRead,
    DataSetCreate,
    DataSetRead,
    DataSetUpdate,
    DataSetUsageRead,
    SetIntegrityPatternRequest,
)

DEFAULT_SLA_DAYS = 14


class DataMovementService:
    """Consolidated business logic service for application data movement, datasets, and integrity contracts."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # -------------------------------------------------------------------------
    # Application Profiles (ITSM Synchronized)
    # -------------------------------------------------------------------------

    async def list_applications(self) -> List[ApplicationProfileRead]:
        """List all synchronized application profiles with dataset and integration rollups."""
        stmt = (
            select(ApplicationProfile)
            .options(
                selectinload(ApplicationProfile.asset_head),
                selectinload(ApplicationProfile.app_owner),
            )
            .order_by(ApplicationProfile.itsm_system_name.asc())
        )
        result = await self.db.execute(stmt)
        profiles = result.scalars().all()

        app_reads = []
        for p in profiles:
            # Active datasets count
            ds_stmt = select(func.count(DataSet.id)).where(
                DataSet.app_head_id == p.asset_head_id,
                DataSet.is_archived.is_(False),
            )
            ds_count = (await self.db.execute(ds_stmt)).scalar() or 0

            # Integrations count (inbound or outbound)
            int_stmt = select(func.count(ApplicationIntegration.id)).where(
                or_(
                    ApplicationIntegration.source_app_head_id == p.asset_head_id,
                    ApplicationIntegration.target_app_head_id == p.asset_head_id,
                )
            )
            int_count = (await self.db.execute(int_stmt)).scalar() or 0

            app_reads.append(
                ApplicationProfileRead(
                    id=p.id,
                    asset_head_id=p.asset_head_id,
                    itsm_system_id=p.itsm_system_id,
                    itsm_system_name=p.itsm_system_name,
                    cmdb_criticality=p.cmdb_criticality,
                    app_owner_id=p.app_owner_id,
                    app_owner_name=p.app_owner.full_name if p.app_owner else None,
                    synced_at=p.synced_at,
                    datasets_count=ds_count,
                    integrations_count=int_count,
                )
            )
        return app_reads

    async def get_application_profile(self, app_head_id: uuid.UUID) -> ApplicationProfileRead:
        """Fetch application profile by its asset head ID."""
        stmt = (
            select(ApplicationProfile)
            .options(
                selectinload(ApplicationProfile.asset_head),
                selectinload(ApplicationProfile.app_owner),
            )
            .where(ApplicationProfile.asset_head_id == app_head_id)
        )
        profile = (await self.db.execute(stmt)).scalar_one_or_none()
        if not profile:
            raise EntityNotFoundException(f"Application with head '{app_head_id}' was not found.")

        ds_stmt = select(func.count(DataSet.id)).where(
            DataSet.app_head_id == app_head_id,
            DataSet.is_archived.is_(False),
        )
        ds_count = (await self.db.execute(ds_stmt)).scalar() or 0

        int_stmt = select(func.count(ApplicationIntegration.id)).where(
            or_(
                ApplicationIntegration.source_app_head_id == app_head_id,
                ApplicationIntegration.target_app_head_id == app_head_id,
            )
        )
        int_count = (await self.db.execute(int_stmt)).scalar() or 0

        return ApplicationProfileRead(
            id=profile.id,
            asset_head_id=profile.asset_head_id,
            itsm_system_id=profile.itsm_system_id,
            itsm_system_name=profile.itsm_system_name,
            cmdb_criticality=profile.cmdb_criticality,
            app_owner_id=profile.app_owner_id,
            app_owner_name=profile.app_owner.full_name if profile.app_owner else None,
            synced_at=profile.synced_at,
            datasets_count=ds_count,
            integrations_count=int_count,
        )

    # -------------------------------------------------------------------------
    # Application-Scoped Datasets (Self-Service CRUD)
    # -------------------------------------------------------------------------

    async def list_datasets(self, app_head_id: uuid.UUID) -> List[DataSetRead]:
        """List active non-archived datasets for an application with active usage counts."""
        await self.get_application_profile(app_head_id)

        stmt = (
            select(DataSet)
            .where(
                DataSet.app_head_id == app_head_id,
                DataSet.is_archived.is_(False),
            )
            .order_by(DataSet.name.asc())
        )
        datasets = (await self.db.execute(stmt)).scalars().all()

        results = []
        for ds in datasets:
            usage_stmt = select(func.count(DataMovementScope.id)).where(
                DataMovementScope.data_set_id == ds.id
            )
            usage_count = (await self.db.execute(usage_stmt)).scalar() or 0

            results.append(
                DataSetRead(
                    id=ds.id,
                    asset_head_id=ds.asset_head_id,
                    app_head_id=ds.app_head_id,
                    name=ds.name,
                    description=ds.description,
                    business_context=ds.business_context,
                    isr_classification=ds.isr_classification,
                    data_categories=list(ds.data_categories or []),
                    is_archived=ds.is_archived,
                    archived_at=ds.archived_at,
                    created_by=ds.created_by,
                    updated_by=ds.updated_by,
                    created_at=ds.created_at,
                    updated_at=ds.updated_at,
                    usage_count=usage_count,
                )
            )
        return results

    async def get_dataset(self, dataset_id: uuid.UUID) -> DataSetRead:
        """Retrieve dataset details by ID."""
        stmt = select(DataSet).where(DataSet.id == dataset_id)
        ds = (await self.db.execute(stmt)).scalar_one_or_none()
        if not ds:
            raise EntityNotFoundException(f"Dataset '{dataset_id}' not found.")

        usage_stmt = select(func.count(DataMovementScope.id)).where(
            DataMovementScope.data_set_id == ds.id
        )
        usage_count = (await self.db.execute(usage_stmt)).scalar() or 0

        return DataSetRead(
            id=ds.id,
            asset_head_id=ds.asset_head_id,
            app_head_id=ds.app_head_id,
            name=ds.name,
            description=ds.description,
            business_context=ds.business_context,
            isr_classification=ds.isr_classification,
            data_categories=list(ds.data_categories or []),
            is_archived=ds.is_archived,
            archived_at=ds.archived_at,
            created_by=ds.created_by,
            updated_by=ds.updated_by,
            created_at=ds.created_at,
            updated_at=ds.updated_at,
            usage_count=usage_count,
        )

    async def create_dataset(
        self,
        app_head_id: uuid.UUID,
        dataset_in: DataSetCreate,
        user_id: uuid.UUID,
    ) -> DataSetRead:
        """Create a new dataset scoped to an application with domain name uniqueness validation."""
        app = await self.get_application_profile(app_head_id)

        clean_name = dataset_in.name.strip()
        if not clean_name:
            raise ValidationException("Dataset name cannot be blank.")

        # Check name uniqueness scoped to application (case-insensitive)
        uq_stmt = select(DataSet).where(
            DataSet.app_head_id == app_head_id,
            func.lower(DataSet.name) == clean_name.lower(),
            DataSet.is_archived.is_(False),
        )
        existing = (await self.db.execute(uq_stmt)).scalar_one_or_none()
        if existing:
            raise ValidationException(
                f"A dataset with name '{clean_name}' already exists for application '{app.itsm_system_name}'."
            )

        # Lookup or fallback Asset Type for Dataset
        type_stmt = select(AssetType).where(
            or_(AssetType.code == "DATASET", AssetType.code == "BUSINESS_TERM")
        )
        asset_type = (await self.db.execute(type_stmt)).scalars().first()
        if not asset_type:
            asset_type = (await self.db.execute(select(AssetType))).scalars().first()
            if not asset_type:
                raise ValidationException("No metamodel asset type configured.")

        # Lookup domain from parent application head
        app_head = (await self.db.execute(select(AssetHead).where(AssetHead.id == app_head_id))).scalar_one()

        # Create AssetHead and published version snapshot
        now = datetime.now(timezone.utc)
        head_id = uuid.uuid7()
        version_id = uuid.uuid7()

        head = AssetHead(
            id=head_id,
            domain_id=app_head.domain_id,
            asset_type_id=asset_type.id,
            published_version_id=None,
            created_at=now,
        )
        self.db.add(head)
        await self.db.flush()

        version = AssetVersion(
            id=version_id,
            asset_head_id=head_id,
            version_number=1,
            status=VersionStatusEnum.PUBLISHED,
            name=clean_name,
            description_markdown=dataset_in.description or f"# {clean_name}\n\n{dataset_in.business_context}",
            attributes_payload={
                "ISR_CLASSIFICATION": dataset_in.isr_classification.value,
                "DATA_CATEGORIES": dataset_in.data_categories,
                "BUSINESS_CONTEXT": dataset_in.business_context,
            },
            relations_snapshot=[],
            created_by=user_id,
            created_at=now,
            published_at=now,
        )
        self.db.add(version)
        await self.db.flush()

        head.published_version_id = version_id
        head.published_version = version
        await self.db.flush()

        dataset_id = uuid.uuid7()
        dataset = DataSet(
            id=dataset_id,
            asset_head_id=head_id,
            app_head_id=app_head_id,
            name=clean_name,
            description=dataset_in.description,
            business_context=dataset_in.business_context.strip(),
            isr_classification=dataset_in.isr_classification,
            data_categories=dataset_in.data_categories,
            created_by=user_id,
            updated_by=user_id,
            created_at=now,
            updated_at=now,
        )
        self.db.add(dataset)
        await self.db.commit()
        await self.db.refresh(dataset)

        return DataSetRead(
            id=dataset.id,
            asset_head_id=dataset.asset_head_id,
            app_head_id=dataset.app_head_id,
            name=dataset.name,
            description=dataset.description,
            business_context=dataset.business_context,
            isr_classification=dataset.isr_classification,
            data_categories=list(dataset.data_categories or []),
            is_archived=dataset.is_archived,
            archived_at=dataset.archived_at,
            created_by=dataset.created_by,
            updated_by=dataset.updated_by,
            created_at=dataset.created_at,
            updated_at=dataset.updated_at,
            usage_count=0,
        )

    async def update_dataset(
        self,
        dataset_id: uuid.UUID,
        dataset_in: DataSetUpdate,
        user_id: uuid.UUID,
    ) -> DataSetRead:
        """Update dataset attributes with automated Sensitivity Escalation Guardrail."""
        stmt = select(DataSet).where(DataSet.id == dataset_id, DataSet.is_archived.is_(False))
        dataset = (await self.db.execute(stmt)).scalar_one_or_none()
        if not dataset:
            raise EntityNotFoundException(f"Dataset '{dataset_id}' not found.")

        # Name uniqueness check if renamed
        if dataset_in.name is not None:
            clean_name = dataset_in.name.strip()
            if clean_name.lower() != dataset.name.lower():
                uq_stmt = select(DataSet).where(
                    DataSet.app_head_id == dataset.app_head_id,
                    func.lower(DataSet.name) == clean_name.lower(),
                    DataSet.id != dataset.id,
                    DataSet.is_archived.is_(False),
                )
                if (await self.db.execute(uq_stmt)).scalar_one_or_none():
                    raise ValidationException(f"A dataset with name '{clean_name}' already exists.")
                dataset.name = clean_name

        if dataset_in.description is not None:
            dataset.description = dataset_in.description

        if dataset_in.business_context is not None:
            dataset.business_context = dataset_in.business_context.strip()

        # Check for Sensitivity Escalation
        old_isr = dataset.isr_classification
        new_isr = dataset_in.isr_classification or old_isr
        old_categories = set(dataset.data_categories or [])
        new_categories = set(dataset_in.data_categories if dataset_in.data_categories is not None else old_categories)

        is_isr_escalated = (
            old_isr in (ISRClassificationEnum.PUBLIC, ISRClassificationEnum.INTERNAL)
            and new_isr in (ISRClassificationEnum.RESTRICTED, ISRClassificationEnum.HIGHLY_RESTRICTED)
        )
        is_pii_added = "CUSTOMER_PII" not in old_categories and "CUSTOMER_PII" in new_categories

        if dataset_in.isr_classification is not None:
            dataset.isr_classification = dataset_in.isr_classification

        if dataset_in.data_categories is not None:
            dataset.data_categories = dataset_in.data_categories

        now = datetime.now(timezone.utc)
        dataset.updated_at = now
        dataset.updated_by = user_id

        # Execute Sensitivity Escalation Guardrail across linked integrations
        if is_isr_escalated or is_pii_added:
            await self._evaluate_sensitivity_escalation_guardrail(dataset, new_isr, user_id)

        await self.db.commit()
        await self.db.refresh(dataset)

        return await self.get_dataset(dataset.id)

    async def _evaluate_sensitivity_escalation_guardrail(
        self,
        dataset: DataSet,
        new_isr: ISRClassificationEnum,
        actor_id: uuid.UUID,
    ) -> None:
        """Impact evaluation: Flag bound integrations as IN_REMEDIATION if transfer controls are non-compliant."""
        scopes_stmt = (
            select(DataMovementScope)
            .options(selectinload(DataMovementScope.integration))
            .where(DataMovementScope.data_set_id == dataset.id)
        )
        scopes = (await self.db.execute(scopes_stmt)).scalars().all()

        for scope in scopes:
            integration = scope.integration
            # If pattern is unenforced or unencrypted in transit -> trigger remediation
            if integration.integrity_pattern == IntegrityPatternEnum.NONE_UNENFORCED or not scope.encryption_in_transit:
                integration.governance_status = IntegrationGovernanceStatusEnum.IN_REMEDIATION

                # Query app profile to determine app owner for compliance issue
                app_prof = (
                    await self.db.execute(
                        select(ApplicationProfile).where(
                            ApplicationProfile.asset_head_id == integration.source_app_head_id
                        )
                    )
                ).scalar_one_or_none()
                owner_id = app_prof.app_owner_id if app_prof else actor_id

                # Create automated compliance issue
                issue = ComplianceIssue(
                    id=uuid.uuid7(),
                    target_asset_head_id=integration.asset_head_id,
                    app_owner_id=owner_id,
                    title=f"Sensitive Data Movement Policy Breach: Integration {integration.itsm_integration_id}",
                    description=(
                        f"Bound dataset '{dataset.name}' was escalated to {new_isr.value}. "
                        f"Integration '{integration.itsm_integration_id}' lacks certified integrity controls or in-transit encryption."
                    ),
                    severity=IssueSeverityEnum.CRITICAL if new_isr == ISRClassificationEnum.HIGHLY_RESTRICTED else IssueSeverityEnum.HIGH,
                    status=IssueStatusEnum.OPEN,
                    remediation_deadline=datetime.now(timezone.utc) + timedelta(days=DEFAULT_SLA_DAYS),
                    created_by=actor_id,
                )
                self.db.add(issue)

    async def get_dataset_usages(self, dataset_id: uuid.UUID) -> List[DataSetUsageRead]:
        """Pre-flight dependency analysis: return all active bound integrations."""
        dataset = (await self.db.execute(select(DataSet).where(DataSet.id == dataset_id))).scalar_one_or_none()
        if not dataset:
            raise EntityNotFoundException(f"Dataset '{dataset_id}' not found.")

        stmt = (
            select(DataMovementScope)
            .options(
                selectinload(DataMovementScope.integration).selectinload(ApplicationIntegration.source_app_head),
                selectinload(DataMovementScope.integration).selectinload(ApplicationIntegration.target_app_head),
            )
            .where(DataMovementScope.data_set_id == dataset_id)
        )
        scopes = (await self.db.execute(stmt)).scalars().all()

        usages = []
        for s in scopes:
            integ = s.integration
            # Partner app is the other end of the integration
            if integ.source_app_head_id == dataset.app_head_id:
                partner_head_id = integ.target_app_head_id
            else:
                partner_head_id = integ.source_app_head_id

            # Resolve partner app name
            profile_stmt = select(ApplicationProfile).where(ApplicationProfile.asset_head_id == partner_head_id)
            partner_profile = (await self.db.execute(profile_stmt)).scalar_one_or_none()
            partner_name = partner_profile.itsm_system_name if partner_profile else str(partner_head_id)[:8]

            usages.append(
                DataSetUsageRead(
                    integration_id=integ.id,
                    itsm_integration_id=integ.itsm_integration_id,
                    direction=integ.direction,
                    partner_app_head_id=partner_head_id,
                    partner_application_name=partner_name,
                    transfer_type=integ.transfer_type,
                    frequency=integ.frequency,
                    governance_status=integ.governance_status,
                )
            )
        return usages

    async def delete_dataset(self, dataset_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Delete dataset with safety lock: blocked with 409 Conflict if bound to active integrations."""
        dataset = (await self.db.execute(select(DataSet).where(DataSet.id == dataset_id))).scalar_one_or_none()
        if not dataset:
            raise EntityNotFoundException(f"Dataset '{dataset_id}' not found.")

        usages = await self.get_dataset_usages(dataset_id)
        if usages:
            raise DependencyConflictException(
                f"Cannot delete dataset '{dataset.name}': Bound to {len(usages)} active integration(s). Unbind integrations before deleting.",
                blocking_entities=usages,
            )

        # Audit-preserving soft-delete
        now = datetime.now(timezone.utc)
        dataset.is_archived = True
        dataset.archived_at = now
        dataset.updated_by = user_id
        await self.db.commit()

    # -------------------------------------------------------------------------
    # Integrations & Data Movement Scopes
    # -------------------------------------------------------------------------

    async def list_integrations(
        self,
        app_head_id: uuid.UUID,
        direction: Optional[IntegrationDirectionEnum] = None,
    ) -> List[ApplicationIntegrationRead]:
        """List integrations for an application with bound dataset scopes, SLA tracking, and partner names."""
        await self.get_application_profile(app_head_id)

        stmt = (
            select(ApplicationIntegration)
            .options(
                selectinload(ApplicationIntegration.source_app_head),
                selectinload(ApplicationIntegration.target_app_head),
                selectinload(ApplicationIntegration.certified_by_user),
                selectinload(ApplicationIntegration.movement_scopes).selectinload(DataMovementScope.dataset),
            )
            .where(
                or_(
                    ApplicationIntegration.source_app_head_id == app_head_id,
                    ApplicationIntegration.target_app_head_id == app_head_id,
                )
            )
            .order_by(ApplicationIntegration.itsm_integration_id.asc())
        )
        if direction:
            stmt = stmt.where(ApplicationIntegration.direction == direction)

        integrations = (await self.db.execute(stmt)).scalars().all()

        now = datetime.now(timezone.utc)
        results = []

        for integ in integrations:
            # Resolve app names
            src_profile = (
                await self.db.execute(
                    select(ApplicationProfile).where(ApplicationProfile.asset_head_id == integ.source_app_head_id)
                )
            ).scalar_one_or_none()
            tgt_profile = (
                await self.db.execute(
                    select(ApplicationProfile).where(ApplicationProfile.asset_head_id == integ.target_app_head_id)
                )
            ).scalar_one_or_none()

            src_name = src_profile.itsm_system_name if src_profile else "Source Application"
            tgt_name = tgt_profile.itsm_system_name if tgt_profile else "Target Application"

            # SLA calculation
            elapsed_days = (now - integ.created_at).days
            days_left = max(0, DEFAULT_SLA_DAYS - elapsed_days)
            is_breached = (
                elapsed_days > DEFAULT_SLA_DAYS
                and integ.governance_status in (
                    IntegrationGovernanceStatusEnum.UNGOVERNED,
                    IntegrationGovernanceStatusEnum.IN_REMEDIATION,
                )
            )

            # Bound datasets
            bound_reads = []
            for scope in integ.movement_scopes:
                ds = scope.dataset
                bound_reads.append(
                    DataMovementScopeRead(
                        id=scope.id,
                        integration_id=scope.integration_id,
                        data_set_id=scope.data_set_id,
                        dataset_name=ds.name if ds else "Unknown Dataset",
                        isr_classification=ds.isr_classification if ds else None,
                        data_categories=list(ds.data_categories or []) if ds else [],
                        retention_period_days=scope.retention_period_days,
                        encryption_in_transit=scope.encryption_in_transit,
                        created_at=scope.created_at,
                    )
                )

            results.append(
                ApplicationIntegrationRead(
                    id=integ.id,
                    asset_head_id=integ.asset_head_id,
                    itsm_integration_id=integ.itsm_integration_id,
                    source_app_head_id=integ.source_app_head_id,
                    source_app_name=src_name,
                    target_app_head_id=integ.target_app_head_id,
                    target_app_name=tgt_name,
                    direction=integ.direction,
                    transfer_type=integ.transfer_type,
                    frequency=integ.frequency,
                    itsm_last_synced_at=integ.itsm_last_synced_at,
                    is_active_in_itsm=integ.is_active_in_itsm,
                    governance_status=integ.governance_status,
                    integrity_pattern=integ.integrity_pattern,
                    integrity_pattern_details=integ.integrity_pattern_details,
                    governance_certified_at=integ.governance_certified_at,
                    certified_by=integ.certified_by,
                    certified_by_name=integ.certified_by_user.full_name if integ.certified_by_user else None,
                    created_at=integ.created_at,
                    bound_datasets=bound_reads,
                    sla_days_remaining=days_left,
                    sla_breached=is_breached,
                )
            )

        return results

    async def get_integration(self, integration_id: uuid.UUID) -> ApplicationIntegrationRead:
        """Fetch single integration with full details."""
        stmt = (
            select(ApplicationIntegration)
            .options(
                selectinload(ApplicationIntegration.source_app_head),
                selectinload(ApplicationIntegration.target_app_head),
                selectinload(ApplicationIntegration.certified_by_user),
                selectinload(ApplicationIntegration.movement_scopes).selectinload(DataMovementScope.dataset),
            )
            .where(ApplicationIntegration.id == integration_id)
        )
        integ = (await self.db.execute(stmt)).scalar_one_or_none()
        if not integ:
            raise EntityNotFoundException(f"Integration '{integration_id}' not found.")

        src_profile = (
            await self.db.execute(
                select(ApplicationProfile).where(ApplicationProfile.asset_head_id == integ.source_app_head_id)
            )
        ).scalar_one_or_none()
        tgt_profile = (
            await self.db.execute(
                select(ApplicationProfile).where(ApplicationProfile.asset_head_id == integ.target_app_head_id)
            )
        ).scalar_one_or_none()

        src_name = src_profile.itsm_system_name if src_profile else "Source Application"
        tgt_name = tgt_profile.itsm_system_name if tgt_profile else "Target Application"

        now = datetime.now(timezone.utc)
        elapsed_days = (now - integ.created_at).days
        days_left = max(0, DEFAULT_SLA_DAYS - elapsed_days)
        is_breached = (
            elapsed_days > DEFAULT_SLA_DAYS
            and integ.governance_status in (
                IntegrationGovernanceStatusEnum.UNGOVERNED,
                IntegrationGovernanceStatusEnum.IN_REMEDIATION,
            )
        )

        bound_reads = [
            DataMovementScopeRead(
                id=s.id,
                integration_id=s.integration_id,
                data_set_id=s.data_set_id,
                dataset_name=s.dataset.name if s.dataset else "Unknown Dataset",
                isr_classification=s.dataset.isr_classification if s.dataset else None,
                data_categories=list(s.dataset.data_categories or []) if s.dataset else [],
                retention_period_days=s.retention_period_days,
                encryption_in_transit=s.encryption_in_transit,
                created_at=s.created_at,
            )
            for s in integ.movement_scopes
        ]

        return ApplicationIntegrationRead(
            id=integ.id,
            asset_head_id=integ.asset_head_id,
            itsm_integration_id=integ.itsm_integration_id,
            source_app_head_id=integ.source_app_head_id,
            source_app_name=src_name,
            target_app_head_id=integ.target_app_head_id,
            target_app_name=tgt_name,
            direction=integ.direction,
            transfer_type=integ.transfer_type,
            frequency=integ.frequency,
            itsm_last_synced_at=integ.itsm_last_synced_at,
            is_active_in_itsm=integ.is_active_in_itsm,
            governance_status=integ.governance_status,
            integrity_pattern=integ.integrity_pattern,
            integrity_pattern_details=integ.integrity_pattern_details,
            governance_certified_at=integ.governance_certified_at,
            certified_by=integ.certified_by,
            certified_by_name=integ.certified_by_user.full_name if integ.certified_by_user else None,
            created_at=integ.created_at,
            bound_datasets=bound_reads,
            sla_days_remaining=days_left,
            sla_breached=is_breached,
        )

    async def bind_scope(
        self,
        integration_id: uuid.UUID,
        scope_in: BindScopeRequest,
        user_id: uuid.UUID,
    ) -> DataMovementScopeRead:
        """Bind a dataset to an integration with transit retention and encryption parameters."""
        integ = (
            await self.db.execute(select(ApplicationIntegration).where(ApplicationIntegration.id == integration_id))
        ).scalar_one_or_none()
        if not integ:
            raise EntityNotFoundException(f"Integration '{integration_id}' not found.")

        dataset = (
            await self.db.execute(
                select(DataSet).where(DataSet.id == scope_in.data_set_id, DataSet.is_archived.is_(False))
            )
        ).scalar_one_or_none()
        if not dataset:
            raise EntityNotFoundException(f"Dataset '{scope_in.data_set_id}' not found or archived.")

        # Check existing binding
        scope_stmt = select(DataMovementScope).where(
            DataMovementScope.integration_id == integration_id,
            DataMovementScope.data_set_id == scope_in.data_set_id,
        )
        existing = (await self.db.execute(scope_stmt)).scalar_one_or_none()

        now = datetime.now(timezone.utc)
        if existing:
            existing.retention_period_days = scope_in.retention_period_days
            existing.encryption_in_transit = scope_in.encryption_in_transit
            scope = existing
        else:
            scope = DataMovementScope(
                id=uuid.uuid7(),
                integration_id=integration_id,
                data_set_id=scope_in.data_set_id,
                retention_period_days=scope_in.retention_period_days,
                encryption_in_transit=scope_in.encryption_in_transit,
                created_by=user_id,
                created_at=now,
            )
            self.db.add(scope)

        # If UNGOVERNED, transition to IN_REMEDIATION as progress is made
        if integ.governance_status == IntegrationGovernanceStatusEnum.UNGOVERNED:
            integ.governance_status = IntegrationGovernanceStatusEnum.IN_REMEDIATION

        await self.db.commit()
        await self.db.refresh(scope)

        return DataMovementScopeRead(
            id=scope.id,
            integration_id=scope.integration_id,
            data_set_id=scope.data_set_id,
            dataset_name=dataset.name,
            isr_classification=dataset.isr_classification,
            data_categories=list(dataset.data_categories or []),
            retention_period_days=scope.retention_period_days,
            encryption_in_transit=scope.encryption_in_transit,
            created_at=scope.created_at,
        )

    async def unbind_scope(self, integration_id: uuid.UUID, dataset_id: uuid.UUID) -> None:
        """Remove a dataset from an integration scope with minimum cardinality protection."""
        integ = (
            await self.db.execute(select(ApplicationIntegration).where(ApplicationIntegration.id == integration_id))
        ).scalar_one_or_none()
        if not integ:
            raise EntityNotFoundException(f"Integration '{integration_id}' not found.")

        del_stmt = delete(DataMovementScope).where(
            DataMovementScope.integration_id == integration_id,
            DataMovementScope.data_set_id == dataset_id,
        )
        await self.db.execute(del_stmt)

        # Check remaining bound datasets
        rem_count = (
            await self.db.execute(
                select(func.count(DataMovementScope.id)).where(DataMovementScope.integration_id == integration_id)
            )
        ).scalar() or 0

        # Minimum cardinality protection: if 0 datasets remain, integration is ungoverned
        if rem_count == 0:
            integ.governance_status = IntegrationGovernanceStatusEnum.UNGOVERNED

        await self.db.commit()

    async def set_integrity_pattern(
        self,
        integration_id: uuid.UUID,
        pattern_in: SetIntegrityPatternRequest,
        user_id: uuid.UUID,
    ) -> ApplicationIntegrationRead:
        """Assign certified transfer integrity pattern and implementation notes."""
        integ = (
            await self.db.execute(select(ApplicationIntegration).where(ApplicationIntegration.id == integration_id))
        ).scalar_one_or_none()
        if not integ:
            raise EntityNotFoundException(f"Integration '{integration_id}' not found.")

        integ.integrity_pattern = pattern_in.integrity_pattern
        integ.integrity_pattern_details = pattern_in.integrity_pattern_details

        if integ.governance_status == IntegrationGovernanceStatusEnum.UNGOVERNED:
            integ.governance_status = IntegrationGovernanceStatusEnum.IN_REMEDIATION

        await self.db.commit()
        return await self.get_integration(integration_id)

    async def submit_certification(
        self,
        integration_id: uuid.UUID,
        user_id: uuid.UUID,
        notes: Optional[str] = None,
    ) -> ApplicationIntegrationRead:
        """Validate preconditions and transition integration to PENDING_VERIFICATION for Data Steward sign-off."""
        integ = (
            await self.db.execute(
                select(ApplicationIntegration)
                .options(selectinload(ApplicationIntegration.movement_scopes))
                .where(ApplicationIntegration.id == integration_id)
            )
        ).scalar_one_or_none()
        if not integ:
            raise EntityNotFoundException(f"Integration '{integration_id}' not found.")

        # Precondition 1: At least 1 active bound dataset
        scopes_count = (
            await self.db.execute(
                select(func.count(DataMovementScope.id)).where(DataMovementScope.integration_id == integration_id)
            )
        ).scalar() or 0
        if scopes_count == 0:
            raise ValidationException(
                "Cannot submit certification: Integration must have at least one (1) linked dataset."
            )

        # Precondition 2: Certified integrity pattern declared
        if integ.integrity_pattern == IntegrityPatternEnum.NONE_UNENFORCED:
            raise ValidationException(
                "Cannot submit certification: A certified Transfer Integrity Pattern must be declared (cannot be NONE_UNENFORCED)."
            )

        integ.governance_status = IntegrationGovernanceStatusEnum.PENDING_VERIFICATION
        await self.db.commit()
        return await self.get_integration(integration_id)

    async def verify_certification(
        self,
        integration_id: uuid.UUID,
        approved: bool,
        steward_user_id: uuid.UUID,
        notes: Optional[str] = None,
    ) -> ApplicationIntegrationRead:
        """Data Steward certification sign-off: marks COMPLIANT or returns to IN_REMEDIATION."""
        integ = (
            await self.db.execute(select(ApplicationIntegration).where(ApplicationIntegration.id == integration_id))
        ).scalar_one_or_none()
        if not integ:
            raise EntityNotFoundException(f"Integration '{integration_id}' not found.")

        now = datetime.now(timezone.utc)
        if approved:
            integ.governance_status = IntegrationGovernanceStatusEnum.COMPLIANT
            integ.governance_certified_at = now
            integ.certified_by = steward_user_id

            # Auto-resolve any open compliance issue for this integration
            issues = (
                await self.db.execute(
                    select(ComplianceIssue).where(
                        ComplianceIssue.target_asset_head_id == integ.asset_head_id,
                        ComplianceIssue.status == IssueStatusEnum.OPEN,
                    )
                )
            ).scalars().all()
            for issue in issues:
                issue.status = IssueStatusEnum.RESOLVED
                issue.resolved_at = now
        else:
            integ.governance_status = IntegrationGovernanceStatusEnum.IN_REMEDIATION

        await self.db.commit()
        return await self.get_integration(integration_id)
