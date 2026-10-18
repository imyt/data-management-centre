"""The `policy` schema: policies, the control library, rule versions and applied controls."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, Timestamps, UUIDv7PrimaryKey
from app.modules.inventory.service import SubjectType
from app.modules.policy.domain import AppliedControlStatus, ControlStatus, check_in

SCHEMA = "policy"


class Policy(UUIDv7PrimaryKey, Timestamps, Base):
    """A statement of intent owned by the governance team. Controls make it enforceable."""

    __tablename__ = "policy"
    __table_args__ = ({"schema": SCHEMA},)

    code: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    statement: Mapped[str] = mapped_column(Text)
    # Users live in the identity module; ids only, no cross-schema foreign key.
    owner_id: Mapped[uuid.UUID | None]

    controls: Mapped[list["Control"]] = relationship(
        back_populates="policy", order_by="Control.code"
    )


class Control(UUIDv7PrimaryKey, Timestamps, Base):
    """A check in the control library. Its rule lives in versions; the latest one is current."""

    __tablename__ = "control"
    __table_args__ = (
        CheckConstraint(check_in("status", ControlStatus), name="status"),
        CheckConstraint("status <> 'retired' OR retired_reason IS NOT NULL", name="retired_reason"),
        {"schema": SCHEMA},
    )

    policy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{SCHEMA}.policy.id"), index=True)
    code: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    rule_type: Mapped[str] = mapped_column(Text, index=True)
    control_owner_id: Mapped[uuid.UUID | None]
    evidence_requirement: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, server_default=ControlStatus.ACTIVE.value)
    retired_reason: Mapped[str | None] = mapped_column(Text)

    policy: Mapped[Policy] = relationship(back_populates="controls", lazy="joined")
    versions: Mapped[list["RuleVersion"]] = relationship(
        back_populates="control", order_by="RuleVersion.version.desc()"
    )

    @property
    def current_version(self) -> "RuleVersion":
        return self.versions[0]


class RuleVersion(UUIDv7PrimaryKey, Base):
    """One version of a control's rule. Immutable (a trigger refuses updates and deletes), so a
    result can always be explained against the version that produced it (FR-P4)."""

    __tablename__ = "rule_version"
    __table_args__ = (
        UniqueConstraint("control_id", "version"),
        CheckConstraint("version > 0", name="version_positive"),
        {"schema": SCHEMA},
    )

    control_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{SCHEMA}.control.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    params: Mapped[dict[str, Any]] = mapped_column(JSONB)
    selector: Mapped[dict[str, Any]] = mapped_column(JSONB)
    # Why this version replaced the last one; empty for the first.
    change_reason: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[uuid.UUID]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    control: Mapped[Control] = relationship(back_populates="versions")


class AppliedControl(UUIDv7PrimaryKey, Timestamps, Base):
    """A control that applies to one subject, derived from the control's selector.

    Never deleted: when the subject stops matching it is retired, with the reason.
    """

    __tablename__ = "applied_control"
    __table_args__ = (
        CheckConstraint(check_in("subject_type", SubjectType), name="subject_type"),
        CheckConstraint(check_in("status", AppliedControlStatus), name="status"),
        CheckConstraint(
            "status <> 'retired' OR (retired_at IS NOT NULL AND retired_reason IS NOT NULL)",
            name="retired_has_reason",
        ),
        # A subject has a control at most once at a time; history keeps the retired rows.
        Index(
            "uq_applied_control_active",
            "control_id",
            "subject_type",
            "subject_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        Index("ix_applied_control_subject", "subject_type", "subject_id"),
        {"schema": SCHEMA},
    )

    control_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{SCHEMA}.control.id"), index=True)
    # The rule version the control was last derived under.
    rule_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{SCHEMA}.rule_version.id"))
    subject_type: Mapped[str] = mapped_column(Text)
    subject_id: Mapped[uuid.UUID]
    # Kept current at each derivation so lists need no call to inventory.
    subject_name: Mapped[str] = mapped_column(Text)
    subject_domain_id: Mapped[uuid.UUID] = mapped_column(index=True)
    accountable_id: Mapped[uuid.UUID | None]
    responsible_id: Mapped[uuid.UUID | None]
    status: Mapped[str] = mapped_column(Text, server_default=AppliedControlStatus.ACTIVE.value)
    # The "Why?": a sentence, and the attribute values behind it.
    reason: Mapped[str] = mapped_column(Text)
    derived_from: Mapped[dict[str, Any]] = mapped_column(JSONB)
    derived_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retired_reason: Mapped[str | None] = mapped_column(Text)

    control: Mapped[Control] = relationship(lazy="joined")
    rule_version: Mapped[RuleVersion] = relationship(lazy="joined")
