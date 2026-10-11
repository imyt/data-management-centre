import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.asset import AssetHead, AssetRelation
    from app.models.workflow import WorkflowDefinition


class AttributeDataType(str, enum.Enum):
    """Allowed attribute primitive and complex data types."""
    STRING = "STRING"
    MARKDOWN = "MARKDOWN"
    NUMBER = "NUMBER"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    ENUM = "ENUM"


class AssetType(Base):
    """Configurable Asset Type supporting single-inheritance metamodel hierarchies."""
    __tablename__ = "asset_types"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=func.uuidv7()
    )
    code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
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
    parent_asset_type_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asset_types.id", ondelete="SET NULL"),
        nullable=True
    )
    is_deprecated: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    icon: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    parent_asset_type: Mapped[Optional["AssetType"]] = relationship(
        "AssetType",
        remote_side=[id],
        back_populates="sub_asset_types"
    )
    sub_asset_types: Mapped[List["AssetType"]] = relationship(
        "AssetType",
        back_populates="parent_asset_type"
    )
    attribute_assignments: Mapped[List["AssetTypeAttributeAssignment"]] = relationship(
        "AssetTypeAttributeAssignment",
        back_populates="asset_type",
        cascade="all, delete-orphan",
        order_by="AssetTypeAttributeAssignment.display_order"
    )
    source_relation_types: Mapped[List["RelationType"]] = relationship(
        "RelationType",
        foreign_keys="RelationType.source_asset_type_id",
        back_populates="source_asset_type"
    )
    target_relation_types: Mapped[List["RelationType"]] = relationship(
        "RelationType",
        foreign_keys="RelationType.target_asset_type_id",
        back_populates="target_asset_type"
    )
    asset_heads: Mapped[List["AssetHead"]] = relationship(
        "AssetHead",
        back_populates="asset_type"
    )
    workflow_definitions: Mapped[List["WorkflowDefinition"]] = relationship(
        "WorkflowDefinition",
        back_populates="asset_type"
    )

    def __repr__(self) -> str:
        return f"<AssetType {self.code} ({self.name})>"


class AttributeType(Base):
    """Metamodel Attribute Type definition with data type constraints."""
    __tablename__ = "attribute_types"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=func.uuidv7()
    )
    code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    data_type: Mapped[AttributeDataType] = mapped_column(
        SQLEnum(AttributeDataType, name="attribute_data_type"),
        default=AttributeDataType.STRING,
        nullable=False
    )
    allowed_values: Mapped[Optional[Any]] = mapped_column(
        JSONB,
        nullable=True
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    is_deprecated: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    asset_type_assignments: Mapped[List["AssetTypeAttributeAssignment"]] = relationship(
        "AssetTypeAttributeAssignment",
        back_populates="attribute_type",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<AttributeType {self.code} ({self.data_type.value})>"


class AssetTypeAttributeAssignment(Base):
    """Association table linking Asset Types with Attribute Types and ordering constraints."""
    __tablename__ = "asset_type_attribute_assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=func.uuidv7()
    )
    asset_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asset_types.id", ondelete="CASCADE"),
        nullable=False
    )
    attribute_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("attribute_types.id", ondelete="CASCADE"),
        nullable=False
    )
    is_required: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    default_value: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    display_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    # Relationships
    asset_type: Mapped["AssetType"] = relationship(
        "AssetType",
        back_populates="attribute_assignments"
    )
    attribute_type: Mapped["AttributeType"] = relationship(
        "AttributeType",
        back_populates="asset_type_assignments"
    )

    __table_args__ = (
        UniqueConstraint("asset_type_id", "attribute_type_id", name="uq_type_attribute"),
    )

    def __repr__(self) -> str:
        return f"<Assignment {self.asset_type_id} -> {self.attribute_type_id}>"


class RelationType(Base):
    """Bidirectional semantic relationship definition between asset types."""
    __tablename__ = "relation_types"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=func.uuidv7()
    )
    code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False
    )
    source_asset_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asset_types.id", ondelete="RESTRICT"),
        nullable=False
    )
    target_asset_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asset_types.id", ondelete="RESTRICT"),
        nullable=False
    )
    role_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )  # Forward direction: "Classifies"
    co_role_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )  # Inverse direction: "Is Classified By"
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    is_deprecated: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    source_asset_type: Mapped["AssetType"] = relationship(
        "AssetType",
        foreign_keys=[source_asset_type_id],
        back_populates="source_relation_types"
    )
    target_asset_type: Mapped["AssetType"] = relationship(
        "AssetType",
        foreign_keys=[target_asset_type_id],
        back_populates="target_relation_types"
    )
    asset_relations: Mapped[List["AssetRelation"]] = relationship(
        "AssetRelation",
        back_populates="relation_type"
    )

    def __repr__(self) -> str:
        return f"<RelationType {self.code}: {self.role_name} / {self.co_role_name}>"
