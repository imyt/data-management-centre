"""The `connectors` schema: harvest snapshots, the physical objects in them, and their mappings."""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDv7PrimaryKey
from app.modules.connectors.domain import ObjectKind, SnapshotStatus, check_in

SCHEMA = "connectors"


class HarvestSnapshot(UUIDv7PrimaryKey, Timestamps, Base):
    """One harvest run of a data store: what it found, or why it failed."""

    __tablename__ = "harvest_snapshot"
    __table_args__ = (
        CheckConstraint(check_in("status", SnapshotStatus), name="status"),
        CheckConstraint("status <> 'failed' OR error IS NOT NULL", name="failure_has_error"),
        {"schema": SCHEMA},
    )

    # Data stores live in the inventory module; ids only, no cross-schema foreign key.
    data_store_id: Mapped[uuid.UUID] = mapped_column(index=True)
    status: Mapped[str] = mapped_column(Text)
    taken_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    error: Mapped[str | None] = mapped_column(Text)
    # Who asked for the run (an actor), or null for a scheduled or first harvest.
    requested_by: Mapped[str | None] = mapped_column(Text)


class PhysicalObject(UUIDv7PrimaryKey, Base):
    """A schema, table or column in a snapshot. `path` is dotted: `public.orders.id`."""

    __tablename__ = "physical_object"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "path"),
        CheckConstraint(check_in("kind", ObjectKind), name="kind"),
        {"schema": SCHEMA},
    )

    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA}.harvest_snapshot.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(Text)
    path: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    parent_path: Mapped[str | None] = mapped_column(Text)
    ordinal: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    data_type: Mapped[str | None] = mapped_column(Text)
    # Estimated from the database's statistics; harvest never reads rows.
    row_count: Mapped[int | None] = mapped_column(BigInteger)


class PhysicalObjectMapping(UUIDv7PrimaryKey, Timestamps, Base):
    """A table's asset, or a column's data element. Kept per path, not per snapshot, so a mapping
    survives the next harvest and an object with no mapping is what harvest flags as unmapped."""

    __tablename__ = "physical_object_mapping"
    __table_args__ = (
        UniqueConstraint("data_store_id", "path"),
        CheckConstraint(
            "(asset_id IS NOT NULL) <> (data_element_id IS NOT NULL)", name="asset_or_element"
        ),
        {"schema": SCHEMA},
    )

    data_store_id: Mapped[uuid.UUID]
    path: Mapped[str] = mapped_column(Text)
    # Assets and data elements live in the inventory module; ids only.
    asset_id: Mapped[uuid.UUID | None]
    data_element_id: Mapped[uuid.UUID | None]
    mapped_by_id: Mapped[uuid.UUID]
