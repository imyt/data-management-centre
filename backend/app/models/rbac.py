import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.organization import Community, Domain
    from app.models.asset import AssetHead


class GovernanceRole(Base):
    """Standard RACI governance role definitions."""
    __tablename__ = "governance_roles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=func.uuidv7()
    )
    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Relationships
    responsibilities: Mapped[List["ResponsibilityAssignment"]] = relationship(
        "ResponsibilityAssignment",
        back_populates="role",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<GovernanceRole {self.code} ({self.name})>"


class ResponsibilityAssignment(Base):
    """Hierarchical RACI responsibility mapping scoped to a Community, Domain, or AssetHead."""
    __tablename__ = "responsibility_assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=func.uuidv7()
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("governance_roles.id", ondelete="CASCADE"),
        nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    community_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communities.id", ondelete="CASCADE"),
        nullable=True
    )
    domain_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("domains.id", ondelete="CASCADE"),
        nullable=True
    )
    asset_head_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asset_heads.id", ondelete="CASCADE"),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    role: Mapped["GovernanceRole"] = relationship(
        "GovernanceRole",
        back_populates="responsibilities"
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="responsibilities"
    )
    community: Mapped[Optional["Community"]] = relationship(
        "Community",
        back_populates="responsibilities"
    )
    domain: Mapped[Optional["Domain"]] = relationship(
        "Domain",
        back_populates="responsibilities"
    )
    asset_head: Mapped[Optional["AssetHead"]] = relationship(
        "AssetHead",
        back_populates="responsibilities"
    )

    __table_args__ = (
        CheckConstraint(
            "(community_id IS NOT NULL AND domain_id IS NULL AND asset_head_id IS NULL) OR "
            "(community_id IS NULL AND domain_id IS NOT NULL AND asset_head_id IS NULL) OR "
            "(community_id IS NULL AND domain_id IS NULL AND asset_head_id IS NOT NULL)",
            name="ck_single_assignment_scope"
        ),
        Index("idx_resp_asset", "asset_head_id"),
        Index("idx_resp_domain", "domain_id"),
        Index("idx_resp_comm", "community_id"),
    )

    def __repr__(self) -> str:
        return f"<ResponsibilityAssignment User {self.user_id} Role {self.role_id}>"
