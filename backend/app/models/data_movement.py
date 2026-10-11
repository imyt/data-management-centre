"""SQLAlchemy 2.0 ORM models for Application-Level Data Movement & Integrity Controls."""
import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    CheckConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.asset import AssetHead
    from app.models.user import User


# ============================================================================
# ENUM DEFINITIONS
# ============================================================================

class IntegrationDirectionEnum(str, enum.Enum):
    """Direction of data flow relative to the host application."""
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"


class TransferTypeEnum(str, enum.Enum):
    """Underlying protocol or transport architecture."""
    REST_API = "REST_API"
    EVENT_STREAM_KAFKA = "EVENT_STREAM_KAFKA"
    BATCH_ETL = "BATCH_ETL"
    CDC_STREAMING = "CDC_STREAMING"
    SFTP_FILE = "SFTP_FILE"
    DIRECT_DB_LINK = "DIRECT_DB_LINK"
    MESSAGE_QUEUE_MQ = "MESSAGE_QUEUE_MQ"


class TransferFrequencyEnum(str, enum.Enum):
    """Execution frequency synchronized from ITSM."""
    STREAMING_REALTIME = "STREAMING_REALTIME"
    MICRO_BATCH_NEAR_REALTIME = "MICRO_BATCH_NEAR_REALTIME"
    HOURLY = "HOURLY"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    ON_DEMAND = "ON_DEMAND"


class IntegrityPatternEnum(str, enum.Enum):
    """Certified transfer integrity patterns ensuring transit completeness and deduplication."""
    CHECKSUM_HASH_VERIFICATION = "CHECKSUM_HASH_VERIFICATION"
    IDEMPOTENT_DEDUPLICATION = "IDEMPOTENT_DEDUPLICATION"
    ROW_COUNT_RECONCILIATION = "ROW_COUNT_RECONCILIATION"
    CDC_WATERMARK_AUDIT = "CDC_WATERMARK_AUDIT"
    TRANSACTIONAL_TWO_PHASE_COMMIT = "TRANSACTIONAL_TWO_PHASE_COMMIT"
    CONTROL_RECORD_TRAILER = "CONTROL_RECORD_TRAILER"
    NONE_UNENFORCED = "NONE_UNENFORCED"


class ISRClassificationEnum(str, enum.Enum):
    """Information Security Risk (ISR) data classification tiers."""
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    RESTRICTED = "RESTRICTED"
    HIGHLY_RESTRICTED = "HIGHLY_RESTRICTED"


class IntegrationGovernanceStatusEnum(str, enum.Enum):
    """Lifecycle compliance governance states for technical integrations."""
    UNGOVERNED = "UNGOVERNED"
    IN_REMEDIATION = "IN_REMEDIATION"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    COMPLIANT = "COMPLIANT"
    EXEMPTION_GRANTED = "EXEMPTION_GRANTED"


# ============================================================================
# 1. APPLICATION PROFILES (Linked to ITSM CI)
# ============================================================================

class ApplicationProfile(Base):
    """Authoritative CMDB / ServiceNow Application CI synchronized into the Governance Center."""
    __tablename__ = "application_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=func.uuidv7()
    )
    asset_head_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asset_heads.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    itsm_system_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False
    )
    itsm_system_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    cmdb_criticality: Mapped[str] = mapped_column(
        String(50),
        default="TIER_2",
        nullable=False
    )
    app_owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    asset_head: Mapped["AssetHead"] = relationship("AssetHead", foreign_keys=[asset_head_id])
    app_owner: Mapped["User"] = relationship("User", foreign_keys=[app_owner_id])
    datasets: Mapped[List["DataSet"]] = relationship(
        "DataSet",
        primaryjoin="ApplicationProfile.asset_head_id == foreign(DataSet.app_head_id)",
        back_populates="application_profile"
    )

    __table_args__ = (
        Index("idx_application_itsm_id", "itsm_system_id"),
        Index("idx_application_owner", "app_owner_id"),
    )

    def __repr__(self) -> str:
        return f"<ApplicationProfile {self.itsm_system_id} ({self.itsm_system_name})>"


# ============================================================================
# 2. APPLICATION-SCOPED DATA SETS (Self-Service by App Owner)
# ============================================================================

class DataSet(Base):
    """Application-scoped dataset entity authored and managed directly by the Application Owner."""
    __tablename__ = "data_sets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=func.uuidv7()
    )
    asset_head_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asset_heads.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    app_head_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asset_heads.id", ondelete="CASCADE"),
        nullable=False
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    business_context: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    isr_classification: Mapped[ISRClassificationEnum] = mapped_column(
        SQLEnum(ISRClassificationEnum, name="isr_classification_enum"),
        default=ISRClassificationEnum.INTERNAL,
        nullable=False
    )
    data_categories: Mapped[List[str]] = mapped_column(
        JSONB,
        default=list,
        server_default="[]",
        nullable=False
    )
    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    updated_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    asset_head: Mapped["AssetHead"] = relationship("AssetHead", foreign_keys=[asset_head_id])
    application_head: Mapped["AssetHead"] = relationship(
        "AssetHead",
        foreign_keys=[app_head_id],
        overlaps="application_profile,datasets",
    )
    application_profile: Mapped[Optional["ApplicationProfile"]] = relationship(
        "ApplicationProfile",
        primaryjoin="foreign(DataSet.app_head_id) == ApplicationProfile.asset_head_id",
        back_populates="datasets",
        overlaps="application_head,datasets",
    )
    movement_scopes: Mapped[List["DataMovementScope"]] = relationship(
        "DataMovementScope",
        back_populates="dataset",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_datasets_app", "app_head_id"),
        Index("idx_datasets_isr", "isr_classification"),
        Index("idx_datasets_categories", "data_categories", postgresql_using="gin"),
        UniqueConstraint("app_head_id", "name", name="uq_app_dataset_name"),
    )

    def __repr__(self) -> str:
        return f"<DataSet {self.name} [{self.isr_classification.value}] (App: {self.app_head_id})>"


# ============================================================================
# 3. SYNCHRONIZED INTEGRATIONS (Mastered in ITSM)
# ============================================================================

class ApplicationIntegration(Base):
    """Directional integration mastered in ITSM / CMDB and enriched with governance contracts."""
    __tablename__ = "application_integrations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=func.uuidv7()
    )
    asset_head_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asset_heads.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    itsm_integration_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False
    )
    source_app_head_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asset_heads.id", ondelete="RESTRICT"),
        nullable=False
    )
    target_app_head_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asset_heads.id", ondelete="RESTRICT"),
        nullable=False
    )
    direction: Mapped[IntegrationDirectionEnum] = mapped_column(
        SQLEnum(IntegrationDirectionEnum, name="integration_direction_enum"),
        nullable=False
    )
    transfer_type: Mapped[TransferTypeEnum] = mapped_column(
        SQLEnum(TransferTypeEnum, name="transfer_type_enum"),
        nullable=False
    )
    frequency: Mapped[TransferFrequencyEnum] = mapped_column(
        SQLEnum(TransferFrequencyEnum, name="transfer_frequency_enum"),
        nullable=False
    )
    itsm_last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    is_active_in_itsm: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    # Governance State (Mastered in this Platform)
    governance_status: Mapped[IntegrationGovernanceStatusEnum] = mapped_column(
        SQLEnum(IntegrationGovernanceStatusEnum, name="integration_governance_status_enum"),
        default=IntegrationGovernanceStatusEnum.UNGOVERNED,
        nullable=False
    )
    integrity_pattern: Mapped[IntegrityPatternEnum] = mapped_column(
        SQLEnum(IntegrityPatternEnum, name="integrity_pattern_enum"),
        default=IntegrityPatternEnum.NONE_UNENFORCED,
        nullable=False
    )
    integrity_pattern_details: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    governance_certified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    certified_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    asset_head: Mapped["AssetHead"] = relationship("AssetHead", foreign_keys=[asset_head_id])
    source_app_head: Mapped["AssetHead"] = relationship("AssetHead", foreign_keys=[source_app_head_id])
    target_app_head: Mapped["AssetHead"] = relationship("AssetHead", foreign_keys=[target_app_head_id])
    certified_by_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[certified_by])
    movement_scopes: Mapped[List["DataMovementScope"]] = relationship(
        "DataMovementScope",
        back_populates="integration",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("source_app_head_id != target_app_head_id", name="ck_distinct_apps"),
        Index("idx_integrations_itsm_id", "itsm_integration_id"),
        Index("idx_integrations_gov_status", "governance_status"),
        Index("idx_integrations_source", "source_app_head_id"),
        Index("idx_integrations_target", "target_app_head_id"),
    )

    def __repr__(self) -> str:
        return f"<ApplicationIntegration {self.itsm_integration_id} [{self.governance_status.value}]>"


# ============================================================================
# 4. DATA MOVEMENT BINDINGS (Integrations <-> Data Sets)
# ============================================================================

class DataMovementScope(Base):
    """Association table linking Integrations with one or more governed Data Sets."""
    __tablename__ = "data_movement_scopes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=func.uuidv7()
    )
    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("application_integrations.id", ondelete="CASCADE"),
        nullable=False
    )
    data_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("data_sets.id", ondelete="RESTRICT"),
        nullable=False
    )
    retention_period_days: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    encryption_in_transit: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    integration: Mapped["ApplicationIntegration"] = relationship("ApplicationIntegration", back_populates="movement_scopes")
    dataset: Mapped["DataSet"] = relationship("DataSet", back_populates="movement_scopes")

    __table_args__ = (
        UniqueConstraint("integration_id", "data_set_id", name="uq_integration_dataset"),
        Index("idx_movement_integration", "integration_id"),
        Index("idx_movement_dataset", "data_set_id"),
    )

    def __repr__(self) -> str:
        return f"<DataMovementScope Integration:{self.integration_id} <-> DataSet:{self.data_set_id}>"
