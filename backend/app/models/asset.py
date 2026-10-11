import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional
from sqlalchemy import (
    CheckConstraint,
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

if TYPE_CHECKING:
    from app.models.organization import Domain
    from app.models.metamodel import AssetType, RelationType
    from app.models.user import User
    from app.models.rbac import ResponsibilityAssignment
    from app.models.workflow import WorkflowInstance
    from app.models.compliance import ComplianceIssue


class VersionStatusEnum(str, enum.Enum):
    """Lifecycle status for an asset version."""
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    PUBLISHED = "PUBLISHED"
    SUPERSEDED = "SUPERSEDED"
    REJECTED = "REJECTED"
    DEPRECATED = "DEPRECATED"


class AssetHead(Base):
    """Persistent logical identity of an asset pointing to active published and draft versions."""
    __tablename__ = "asset_heads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=func.uuidv7()
    )
    domain_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("domains.id", ondelete="RESTRICT"),
        nullable=False
    )
    asset_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asset_types.id", ondelete="RESTRICT"),
        nullable=False
    )
    published_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "asset_versions.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_head_published_version"
        ),
        nullable=True
    )
    active_draft_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "asset_versions.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_head_draft_version"
        ),
        nullable=True
    )
    locked_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    locked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    domain: Mapped["Domain"] = relationship(
        "Domain",
        back_populates="asset_heads"
    )
    asset_type: Mapped["AssetType"] = relationship(
        "AssetType",
        back_populates="asset_heads"
    )
    published_version: Mapped[Optional["AssetVersion"]] = relationship(
        "AssetVersion",
        foreign_keys=[published_version_id],
        post_update=True
    )
    active_draft_version: Mapped[Optional["AssetVersion"]] = relationship(
        "AssetVersion",
        foreign_keys=[active_draft_version_id],
        post_update=True
    )
    locked_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[locked_by_user_id]
    )
    versions: Mapped[List["AssetVersion"]] = relationship(
        "AssetVersion",
        foreign_keys="AssetVersion.asset_head_id",
        back_populates="asset_head",
        cascade="all, delete-orphan",
        order_by="desc(AssetVersion.version_number)"
    )
    outgoing_relations: Mapped[List["AssetRelation"]] = relationship(
        "AssetRelation",
        foreign_keys="AssetRelation.source_asset_head_id",
        back_populates="source_asset_head",
        cascade="all, delete-orphan"
    )
    incoming_relations: Mapped[List["AssetRelation"]] = relationship(
        "AssetRelation",
        foreign_keys="AssetRelation.target_asset_head_id",
        back_populates="target_asset_head",
        cascade="all, delete-orphan"
    )
    responsibilities: Mapped[List["ResponsibilityAssignment"]] = relationship(
        "ResponsibilityAssignment",
        back_populates="asset_head",
        cascade="all, delete-orphan"
    )
    compliance_issues: Mapped[List["ComplianceIssue"]] = relationship(
        "ComplianceIssue",
        foreign_keys="ComplianceIssue.target_asset_head_id",
        back_populates="target_asset_head",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_asset_heads_domain", "domain_id"),
        Index("idx_asset_heads_type", "asset_type_id"),
    )

    def __repr__(self) -> str:
        return f"<AssetHead {self.id} (Type: {self.asset_type_id})>"


class AssetVersion(Base):
    """Immutable version iteration of an asset head holding attributes, markdown, and relations snapshot."""
    __tablename__ = "asset_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=func.uuidv7()
    )
    asset_head_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asset_heads.id", ondelete="CASCADE"),
        nullable=False
    )
    version_number: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False
    )
    status: Mapped[VersionStatusEnum] = mapped_column(
        SQLEnum(VersionStatusEnum, name="version_status_enum"),
        default=VersionStatusEnum.DRAFT,
        nullable=False
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    description_markdown: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    attributes_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        server_default="{}",
        default=dict,
        nullable=False
    )
    relations_snapshot: Mapped[list[Any]] = mapped_column(
        JSONB,
        server_default="[]",
        default=list,
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
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    asset_head: Mapped["AssetHead"] = relationship(
        "AssetHead",
        foreign_keys=[asset_head_id],
        back_populates="versions"
    )
    creator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by]
    )
    workflow_instances: Mapped[List["WorkflowInstance"]] = relationship(
        "WorkflowInstance",
        back_populates="asset_version",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("asset_head_id", "version_number", name="uq_head_version"),
        Index(
            "idx_asset_versions_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"}
        ),
    )

    def __repr__(self) -> str:
        return f"<AssetVersion {self.name} v{self.version_number} [{self.status.value}]>"


class AssetRelation(Base):
    """Direct live semantic link between two asset heads."""
    __tablename__ = "asset_relations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=func.uuidv7()
    )
    relation_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("relation_types.id", ondelete="RESTRICT"),
        nullable=False
    )
    source_asset_head_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asset_heads.id", ondelete="CASCADE"),
        nullable=False
    )
    target_asset_head_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asset_heads.id", ondelete="CASCADE"),
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
    relation_type: Mapped["RelationType"] = relationship(
        "RelationType",
        back_populates="asset_relations"
    )
    source_asset_head: Mapped["AssetHead"] = relationship(
        "AssetHead",
        foreign_keys=[source_asset_head_id],
        back_populates="outgoing_relations"
    )
    target_asset_head: Mapped["AssetHead"] = relationship(
        "AssetHead",
        foreign_keys=[target_asset_head_id],
        back_populates="incoming_relations"
    )
    creator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by]
    )

    __table_args__ = (
        UniqueConstraint("relation_type_id", "source_asset_head_id", "target_asset_head_id", name="uq_source_target_relation"),
        CheckConstraint("source_asset_head_id <> target_asset_head_id", name="ck_no_self_relation"),
        Index("idx_relations_source", "source_asset_head_id"),
        Index("idx_relations_target", "target_asset_head_id"),
    )

    def __repr__(self) -> str:
        return f"<AssetRelation {self.source_asset_head_id} -> {self.target_asset_head_id}>"
