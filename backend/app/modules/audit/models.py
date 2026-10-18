"""The `audit` schema. Rows are never updated or deleted: a trigger rejects it (see migrations)."""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Identity, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UUIDv7PrimaryKey


class AuditEvent(UUIDv7PrimaryKey, Base):
    __tablename__ = "audit_event"
    __table_args__ = (
        Index("ix_audit_event_subject", "subject_type", "subject_id", "seq"),
        {"schema": "audit"},
    )

    # Chain order. Writers take an advisory lock first, so seq order is also commit order.
    seq: Mapped[int] = mapped_column(BigInteger, Identity(always=True), unique=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actor: Mapped[str] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text)
    subject_type: Mapped[str] = mapped_column(Text)
    subject_id: Mapped[str] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)
    before: Mapped[Any | None] = mapped_column(JSONB(none_as_null=True))
    after: Mapped[Any | None] = mapped_column(JSONB(none_as_null=True))
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64), unique=True)
