"""The transactional outbox: domain events written with a change, relayed by the worker.

See ADR 0009.

A module that changes something other modules react to calls `publish(session, type, payload)`
with the session that makes the change, so the event commits or rolls back with it. The worker
hands each event to the handlers registered for its type (`Registry.on_event`, wired in
`app/worker.py`). Each handler sees an event at most once: its delivery is recorded in
`outbox_delivery` in the same transaction as the handler's own writes.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic_core import to_jsonable_python
from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.db import Base, UUIDv7PrimaryKey


class OutboxEvent(UUIDv7PrimaryKey, Base):
    __tablename__ = "outbox_event"
    __table_args__ = (
        Index(
            "ix_outbox_event_pending", "available_at", postgresql_where=text("processed_at IS NULL")
        ),
        {"schema": "platform"},
    )

    # `<entity>.<verb>`, like audit actions, e.g. `application.created`.
    type: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Not before: pushed back after a handler fails.
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, server_default="0")
    last_error: Mapped[str | None] = mapped_column(Text)


class OutboxDelivery(Base):
    """A handler has processed an event. The dedupe record for at-most-once handling."""

    __tablename__ = "outbox_delivery"
    __table_args__ = ({"schema": "platform"},)

    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("platform.outbox_event.id", ondelete="CASCADE"), primary_key=True
    )
    handler: Mapped[str] = mapped_column(Text, primary_key=True)
    delivered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


@dataclass(frozen=True)
class Event:
    """What a handler receives. `id` is stable across retries: use it to key follow-up work."""

    id: uuid.UUID
    type: str
    payload: dict[str, Any]
    created_at: datetime


def publish(session: Session, type: str, payload: dict[str, Any]) -> uuid.UUID:
    """Write an event in the caller's transaction. Returns the event id."""
    event = OutboxEvent(type=type, payload=to_jsonable_python(payload))
    session.add(event)
    session.flush()
    return event.id
