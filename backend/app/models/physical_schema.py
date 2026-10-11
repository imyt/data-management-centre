"""SQLAlchemy 2.0 ORM models for Physical Schema & Atomic Column Governance."""
import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
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
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.data_movement import ISRClassificationEnum

if TYPE_CHECKING:
    from app.models.asset import AssetHead
    from app.models.data_movement import DataSet
    from app.models.storage_control import StorageControl
    from app.models.user import User


class DriftStatusEnum(str, enum.Enum):
    """Schema drift detection state."""
    SYNCED = "SYNCED"
    ADDED_UNCLASSIFIED = "ADDED_UNCLASSIFIED"
    DROPPED = "DROPPED"
    TYPE_MODIFIED = "TYPE_MODIFIED"


class MaskingStrategyEnum(str, enum.Enum):
    """Column masking and privacy anonymization algorithms."""
    NONE = "NONE"
    FULL_REDACTION = "FULL_REDACTION"
    PARTIAL_MASK = "PARTIAL_MASK"
    TOKENIZE = "TOKENIZE"
    HASH_SHA256 = "HASH_SHA256"


class HarvestStatusEnum(str, enum.Enum):
    """Status of schema harvesting job."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PhysicalTable(Base):
    """Harvested physical database or warehouse table under an application."""
    __tablename__ = "physical_tables"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=func.uuidv7(),
    )
    app_head_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asset_heads.id", ondelete="CASCADE"),
        nullable=False,
    )
    storage_control_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("storage_controls.id", ondelete="SET NULL"),
        nullable=True,
    )
    schema_name: Mapped[str] = mapped_column(
        String(100),
        default="public",
        nullable=False,
    )
    table_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    row_count_estimate: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    app_head: Mapped["AssetHead"] = relationship("AssetHead", foreign_keys=[app_head_id])
    storage_control: Mapped[Optional["StorageControl"]] = relationship("StorageControl", foreign_keys=[storage_control_id])
    columns: Mapped[List["PhysicalColumn"]] = relationship(
        "PhysicalColumn",
        back_populates="table",
        cascade="all, delete-orphan",
        order_by="PhysicalColumn.column_name",
    )

    __table_args__ = (
        UniqueConstraint("app_head_id", "schema_name", "table_name", name="uq_app_physical_table"),
        Index("idx_physical_tables_app", "app_head_id"),
        Index("idx_physical_tables_storage", "storage_control_id"),
    )

    def __repr__(self) -> str:
        return f"<PhysicalTable {self.schema_name}.{self.table_name}>"


class PhysicalColumn(Base):
    """The atomic unit of data governance tying schemas to movement, masking, and ISR."""
    __tablename__ = "physical_columns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=func.uuidv7(),
    )
    table_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("physical_tables.id", ondelete="CASCADE"),
        nullable=False,
    )
    column_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    data_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    is_nullable: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    drift_status: Mapped[DriftStatusEnum] = mapped_column(
        SQLEnum(DriftStatusEnum, name="drift_status_enum"),
        default=DriftStatusEnum.SYNCED,
        nullable=False,
    )
    is_pii: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    masking_strategy: Mapped[MaskingStrategyEnum] = mapped_column(
        SQLEnum(MaskingStrategyEnum, name="masking_strategy_enum"),
        default=MaskingStrategyEnum.NONE,
        nullable=False,
    )
    isr_classification: Mapped[ISRClassificationEnum] = mapped_column(
        SQLEnum(ISRClassificationEnum, name="isr_classification_enum", create_type=False),
        default=ISRClassificationEnum.INTERNAL,
        nullable=False,
    )
    business_term_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    table: Mapped["PhysicalTable"] = relationship("PhysicalTable", back_populates="columns")
    dataset_mappings: Mapped[List["DataSetColumnMapping"]] = relationship(
        "DataSetColumnMapping",
        back_populates="column",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("table_id", "column_name", name="uq_table_column_name"),
        Index("idx_physical_columns_table", "table_id"),
        Index("idx_physical_columns_drift", "drift_status"),
        Index("idx_physical_columns_pii", "is_pii"),
    )

    def __repr__(self) -> str:
        return f"<PhysicalColumn {self.column_name} ({self.data_type}) [PII:{self.is_pii}]>"


class DataSetColumnMapping(Base):
    """Associates physical columns with application datasets for data movement governance."""
    __tablename__ = "dataset_column_mappings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=func.uuidv7(),
    )
    data_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("data_sets.id", ondelete="CASCADE"),
        nullable=False,
    )
    column_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("physical_columns.id", ondelete="CASCADE"),
        nullable=False,
    )
    transformation_rule: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # Relationships
    dataset: Mapped["DataSet"] = relationship("DataSet", foreign_keys=[data_set_id])
    column: Mapped["PhysicalColumn"] = relationship("PhysicalColumn", back_populates="dataset_mappings")

    __table_args__ = (
        UniqueConstraint("data_set_id", "column_id", name="uq_dataset_column"),
        Index("idx_dataset_column_ds", "data_set_id"),
        Index("idx_dataset_column_col", "column_id"),
    )


class SchemaHarvestRun(Base):
    """Audit log of automated or on-demand schema harvesting and drift detection."""
    __tablename__ = "schema_harvest_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=func.uuidv7(),
    )
    app_head_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asset_heads.id", ondelete="CASCADE"),
        nullable=False,
    )
    storage_control_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("storage_controls.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[HarvestStatusEnum] = mapped_column(
        SQLEnum(HarvestStatusEnum, name="harvest_status_enum"),
        default=HarvestStatusEnum.COMPLETED,
        nullable=False,
    )
    drift_detected: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    drift_summary: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}",
        nullable=False,
    )
    harvested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    harvested_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    app_head: Mapped["AssetHead"] = relationship("AssetHead", foreign_keys=[app_head_id])
    storage_control: Mapped[Optional["StorageControl"]] = relationship("StorageControl", foreign_keys=[storage_control_id])
    user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[harvested_by])

    __table_args__ = (
        Index("idx_harvest_runs_app", "app_head_id"),
        Index("idx_harvest_runs_at", "harvested_at"),
    )

    def __repr__(self) -> str:
        return f"<SchemaHarvestRun {self.id} on App:{self.app_head_id} [Drift:{self.drift_detected}]>"
