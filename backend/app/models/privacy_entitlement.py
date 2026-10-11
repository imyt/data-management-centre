"""SQLAlchemy 2.0 ORM models for Privacy & Consumer Usage Entitlements."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.asset import AssetHead
    from app.models.user import User


class UsageEntitlement(Base):
    """Consumer application authorization to access data under purpose and geo-fencing constraints."""
    __tablename__ = "usage_entitlements"

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
    consumer_app_head_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asset_heads.id", ondelete="RESTRICT"),
        nullable=False,
    )
    authorized_purpose: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    allowed_geo_regions: Mapped[List[str]] = mapped_column(
        JSONB,
        default=list,
        server_default="[]",
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    app_head: Mapped["AssetHead"] = relationship("AssetHead", foreign_keys=[app_head_id])
    consumer_app_head: Mapped["AssetHead"] = relationship("AssetHead", foreign_keys=[consumer_app_head_id])
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by])

    __table_args__ = (
        Index("idx_usage_entitlements_app", "app_head_id"),
        Index("idx_usage_entitlements_consumer", "consumer_app_head_id"),
        Index("idx_usage_entitlements_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<UsageEntitlement App:{self.app_head_id} -> Consumer:{self.consumer_app_head_id}>"
