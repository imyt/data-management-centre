import enum
import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Enum as SQLEnum, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.asset import AssetHead
    from app.models.rbac import ResponsibilityAssignment


class DomainTypeEnum(str, enum.Enum):
    """Specialized governance domain types."""
    GLOSSARY = "GLOSSARY"
    DATA_PRODUCT = "DATA_PRODUCT"
    POLICY = "POLICY"
    SYSTEMS_REGISTER = "SYSTEMS_REGISTER"
    METRIC_STORE = "METRIC_STORE"


class Community(Base, TimestampMixin):
    """Recursive organizational community structure (Enterprise -> Division -> Department)."""
    __tablename__ = "communities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=func.uuidv7()
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    parent_community_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communities.id", ondelete="CASCADE"),
        nullable=True
    )

    # Relationships
    parent_community: Mapped[Optional["Community"]] = relationship(
        "Community",
        remote_side=[id],
        back_populates="sub_communities"
    )
    sub_communities: Mapped[List["Community"]] = relationship(
        "Community",
        back_populates="parent_community",
        cascade="all, delete-orphan"
    )
    domains: Mapped[List["Domain"]] = relationship(
        "Domain",
        back_populates="community",
        cascade="all, delete-orphan"
    )
    responsibilities: Mapped[List["ResponsibilityAssignment"]] = relationship(
        "ResponsibilityAssignment",
        back_populates="community",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_communities_parent", "parent_community_id"),
    )

    def __repr__(self) -> str:
        return f"<Community {self.name}>"


class Domain(Base, TimestampMixin):
    """Scoped container for assets within an organizational community."""
    __tablename__ = "domains"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=func.uuidv7()
    )
    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communities.id", ondelete="CASCADE"),
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
    domain_type: Mapped[DomainTypeEnum] = mapped_column(
        SQLEnum(DomainTypeEnum, name="domain_type_enum"),
        default=DomainTypeEnum.GLOSSARY,
        nullable=False
    )

    # Relationships
    community: Mapped["Community"] = relationship(
        "Community",
        back_populates="domains"
    )
    asset_heads: Mapped[List["AssetHead"]] = relationship(
        "AssetHead",
        back_populates="domain",
        cascade="all, delete-orphan"
    )
    responsibilities: Mapped[List["ResponsibilityAssignment"]] = relationship(
        "ResponsibilityAssignment",
        back_populates="domain",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("community_id", "name", name="uq_community_domain_name"),
        Index("idx_domains_community", "community_id"),
    )

    def __repr__(self) -> str:
        return f"<Domain {self.name} ({self.domain_type.value})>"
