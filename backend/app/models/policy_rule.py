"""Policy Rule Model for dynamic, manageable governance rules."""
import enum
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
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
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.models.compliance import IssueSeverityEnum


class PolicyRuleCategoryEnum(str, enum.Enum):
    """Categorization of policy governance rules."""
    DATA_MOVEMENT = "DATA_MOVEMENT"
    STORAGE_RETENTION = "STORAGE_RETENTION"
    PRIVACY_USAGE = "PRIVACY_USAGE"
    SCHEMA_DRIFT = "SCHEMA_DRIFT"
    CATALOG_METADATA = "CATALOG_METADATA"


class PolicyEnforcementModeEnum(str, enum.Enum):
    """Enforcement posture for a policy rule."""
    BLOCKING = "BLOCKING"      # Raises actionable defects with SLA countdown; prevents certification
    ADVISORY = "ADVISORY"      # Raises informational defect without blocking workflow / sign-offs
    DISABLED = "DISABLED"      # Completely bypassed from evaluation


class PolicyRule(Base):
    """Configurable governance rule definition evaluated across catalog and control planes."""
    __tablename__ = "policy_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=func.uuidv7()
    )
    rule_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    category: Mapped[PolicyRuleCategoryEnum] = mapped_column(
        SQLEnum(PolicyRuleCategoryEnum, name="policy_rule_category_enum"),
        nullable=False,
        index=True
    )
    severity: Mapped[IssueSeverityEnum] = mapped_column(
        SQLEnum(IssueSeverityEnum, name="issue_severity_enum"),
        default=IssueSeverityEnum.MEDIUM,
        nullable=False
    )
    enforcement_mode: Mapped[PolicyEnforcementModeEnum] = mapped_column(
        SQLEnum(PolicyEnforcementModeEnum, name="policy_enforcement_mode_enum"),
        default=PolicyEnforcementModeEnum.BLOCKING,
        nullable=False
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    default_sla_days: Mapped[int] = mapped_column(
        Integer,
        default=14,
        nullable=False
    )
    parameters: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        server_default="{}",
        default=dict,
        nullable=False
    )
    target_entity_type: Mapped[str] = mapped_column(
        String(50),
        default="ASSET",
        nullable=False
    )  # ASSET, INTEGRATION, STORAGE_CONTROL, PHYSICAL_COLUMN
    remediation_guidance: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
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
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    __table_args__ = (
        Index("idx_policy_rules_cat_enabled", "category", "is_enabled"),
    )

    def __repr__(self) -> str:
        return f"<PolicyRule {self.rule_code}: {self.name} [{self.enforcement_mode.value}]>"
