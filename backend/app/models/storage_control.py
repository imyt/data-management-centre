"""SQLAlchemy 2.0 ORM models for Storage & Retention Controls."""
import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.asset import AssetHead
    from app.models.user import User


class StorageTypeEnum(str, enum.Enum):
    """Storage technology platform."""
    POSTGRESQL = "POSTGRESQL"
    S3_BUCKET = "S3_BUCKET"
    SNOWFLAKE = "SNOWFLAKE"
    DYNAMODB = "DYNAMODB"
    BIGQUERY = "BIGQUERY"
    KAFKA_TOPIC = "KAFKA_TOPIC"


class EncryptionAlgorithmEnum(str, enum.Enum):
    """Encryption at rest mechanism."""
    AWS_KMS_CMK = "AWS_KMS_CMK"
    AES_256_GCM = "AES_256_GCM"
    DATABASE_TDE = "DATABASE_TDE"
    PLAINTEXT_UNENCRYPTED = "PLAINTEXT_UNENCRYPTED"


class PurgeMechanismEnum(str, enum.Enum):
    """Cryptographic or physical data purging mechanism."""
    CRYPTOGRAPHIC_ERASURE = "CRYPTOGRAPHIC_ERASURE"
    HARD_DELETE_REMOVAL = "HARD_DELETE_REMOVAL"
    SOFT_DELETE_FLAG = "SOFT_DELETE_FLAG"
    PARTITION_DROP = "PARTITION_DROP"


class StorageControl(Base):
    """Storage and retention governance configuration for an application repository."""
    __tablename__ = "storage_controls"

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
    storage_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    storage_type: Mapped[StorageTypeEnum] = mapped_column(
        SQLEnum(StorageTypeEnum, name="storage_type_enum"),
        default=StorageTypeEnum.POSTGRESQL,
        nullable=False,
    )
    encryption_algorithm: Mapped[EncryptionAlgorithmEnum] = mapped_column(
        SQLEnum(EncryptionAlgorithmEnum, name="encryption_algorithm_enum"),
        default=EncryptionAlgorithmEnum.AWS_KMS_CMK,
        nullable=False,
    )
    kms_key_arn: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    retention_period_days: Mapped[int] = mapped_column(
        Integer,
        default=90,
        nullable=False,
    )
    purge_mechanism: Mapped[PurgeMechanismEnum] = mapped_column(
        SQLEnum(PurgeMechanismEnum, name="purge_mechanism_enum"),
        default=PurgeMechanismEnum.CRYPTOGRAPHIC_ERASURE,
        nullable=False,
    )
    legal_hold_active: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    legal_hold_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    last_purge_attestation_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_purge_attested_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    app_head: Mapped["AssetHead"] = relationship("AssetHead", foreign_keys=[app_head_id])
    attested_by_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[last_purge_attested_by])

    __table_args__ = (
        Index("idx_storage_controls_app", "app_head_id"),
        Index("idx_storage_controls_legal_hold", "legal_hold_active"),
    )

    def __repr__(self) -> str:
        return f"<StorageControl {self.storage_name} ({self.storage_type.value}) [App: {self.app_head_id}]>"
