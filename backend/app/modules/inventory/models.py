"""The `inventory` schema: reference data, applications, their environments and data stores."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, Timestamps, UUIDv7PrimaryKey
from app.modules.inventory.domain import (
    AssetType,
    Criticality,
    DataStoreType,
    EnvironmentType,
    HarvestStatus,
    Hosting,
    LifecycleStatus,
    OwnershipRole,
    OwnershipStatus,
    check_in,
)

SCHEMA = "inventory"


# --- Reference data (FR-D2) ----------------------------------------------------------------------


class _ReferenceItem(UUIDv7PrimaryKey, Timestamps):
    code: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)


class Domain(_ReferenceItem, Base):
    __tablename__ = "domain"
    __table_args__ = ({"schema": SCHEMA},)


class DataCategory(_ReferenceItem, Base):
    __tablename__ = "data_category"
    __table_args__ = ({"schema": SCHEMA},)


class Region(_ReferenceItem, Base):
    __tablename__ = "region"
    __table_args__ = ({"schema": SCHEMA},)


class RetentionPolicy(_ReferenceItem, Base):
    __tablename__ = "retention_policy"
    __table_args__ = (
        CheckConstraint("retention_days > 0", name="retention_days_positive"),
        {"schema": SCHEMA},
    )

    retention_days: Mapped[int] = mapped_column(Integer)


class Purpose(_ReferenceItem, Base):
    __tablename__ = "purpose"
    __table_args__ = ({"schema": SCHEMA},)


# --- Applications (FR-K1, FR-K2) -----------------------------------------------------------------


class Application(UUIDv7PrimaryKey, Timestamps, Base):
    __tablename__ = "application"
    __table_args__ = (
        CheckConstraint(check_in("criticality", Criticality), name="criticality"),
        CheckConstraint(check_in("hosting", Hosting), name="hosting"),
        CheckConstraint(check_in("lifecycle_status", LifecycleStatus), name="lifecycle_status"),
        {"schema": SCHEMA},
    )

    name: Mapped[str] = mapped_column(Text, index=True)
    code: Mapped[str] = mapped_column(Text, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    # Users live in the identity module; ids only, no cross-schema foreign key.
    app_owner_id: Mapped[uuid.UUID | None]
    tech_owner_id: Mapped[uuid.UUID | None]
    domain_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{SCHEMA}.domain.id"), index=True)
    criticality: Mapped[str] = mapped_column(Text)
    hosting: Mapped[str] = mapped_column(Text)
    lifecycle_status: Mapped[str] = mapped_column(Text, index=True)

    domain: Mapped[Domain] = relationship(lazy="joined")
    environments: Mapped[list["AppEnvironment"]] = relationship(
        back_populates="application", order_by="AppEnvironment.id"
    )


class AppEnvironment(UUIDv7PrimaryKey, Timestamps, Base):
    __tablename__ = "app_environment"
    __table_args__ = (
        CheckConstraint(check_in("type", EnvironmentType), name="type"),
        {"schema": SCHEMA},
    )

    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA}.application.id"), index=True
    )
    name: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(Text)
    region_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{SCHEMA}.region.id"))

    application: Mapped[Application] = relationship(back_populates="environments")
    region: Mapped[Region] = relationship(lazy="joined")
    data_stores: Mapped[list["DataStore"]] = relationship(
        back_populates="environment", order_by="DataStore.id"
    )


class DataStore(UUIDv7PrimaryKey, Timestamps, Base):
    __tablename__ = "data_store"
    __table_args__ = (
        CheckConstraint(check_in("type", DataStoreType), name="type"),
        CheckConstraint(check_in("harvest_status", HarvestStatus), name="harvest_status"),
        {"schema": SCHEMA},
    )

    environment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA}.app_environment.id"), index=True
    )
    name: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(Text)
    platform: Mapped[str] = mapped_column(Text)
    region_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{SCHEMA}.region.id"))
    # A reference into the secrets store (e.g. "vault:dmc/orders-db"), never the secret itself.
    connection_ref: Mapped[str] = mapped_column(Text)
    harvest_status: Mapped[str] = mapped_column(Text, server_default=HarvestStatus.NEVER.value)
    last_harvested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    environment: Mapped[AppEnvironment] = relationship(back_populates="data_stores")
    region: Mapped[Region] = relationship(lazy="joined")


# --- Assets, data elements and ownership (FR-K5, FR-K6, FR-K10) ----------------------------------


class Asset(UUIDv7PrimaryKey, Timestamps, Base):
    __tablename__ = "asset"
    __table_args__ = (
        CheckConstraint(check_in("type", AssetType), name="type"),
        # A stored asset names its retention policy; one that is not stored has none.
        CheckConstraint(
            "(is_stored AND retention_policy_id IS NOT NULL) "
            "OR (NOT is_stored AND retention_policy_id IS NULL)",
            name="retention_when_stored",
        ),
        {"schema": SCHEMA},
    )

    name: Mapped[str] = mapped_column(Text, index=True)
    type: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    domain_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{SCHEMA}.domain.id"), index=True)
    data_category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA}.data_category.id")
    )
    business_context: Mapped[str | None] = mapped_column(Text)
    is_stored: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    retention_policy_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA}.retention_policy.id")
    )

    domain: Mapped[Domain] = relationship(lazy="joined")
    data_category: Mapped[DataCategory | None] = relationship(lazy="joined")
    retention_policy: Mapped[RetentionPolicy | None] = relationship(lazy="joined")
    data_elements: Mapped[list["DataElement"]] = relationship(
        back_populates="asset", order_by="DataElement.name, DataElement.id"
    )
    ownerships: Mapped[list["AssetOwnership"]] = relationship(
        back_populates="asset", order_by="AssetOwnership.role"
    )


class DataElement(UUIDv7PrimaryKey, Timestamps, Base):
    __tablename__ = "data_element"
    __table_args__ = (
        UniqueConstraint("asset_id", "name"),
        # Scanner findings arrive with harvest (slice 4); until then PII is declared.
        CheckConstraint("pii_source IN ('declared', 'scanner')", name="pii_source"),
        CheckConstraint("is_pii OR pii_source IS NULL", name="pii_source_needs_pii"),
        {"schema": SCHEMA},
    )

    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{SCHEMA}.asset.id"), index=True)
    name: Mapped[str] = mapped_column(Text)
    data_type: Mapped[str] = mapped_column(Text)
    is_pii: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    pii_source: Mapped[str | None] = mapped_column(Text)
    is_cde: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))

    asset: Mapped[Asset] = relationship(back_populates="data_elements")


class AssetOwnership(UUIDv7PrimaryKey, Timestamps, Base):
    """Who holds an accountability on an asset, and whether they have accepted it.

    One row per asset and role; the history of reassignments and disputes is in the audit trail.
    """

    __tablename__ = "asset_ownership"
    __table_args__ = (
        UniqueConstraint("asset_id", "role"),
        CheckConstraint(check_in("role", OwnershipRole), name="role"),
        CheckConstraint(check_in("status", OwnershipStatus), name="status"),
        CheckConstraint("status <> 'disputed' OR reason IS NOT NULL", name="dispute_has_reason"),
        {"schema": SCHEMA},
    )

    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{SCHEMA}.asset.id"), index=True)
    role: Mapped[str] = mapped_column(Text)
    # Users live in the identity module; ids only, no cross-schema foreign key.
    user_id: Mapped[uuid.UUID] = mapped_column(index=True)
    status: Mapped[str] = mapped_column(Text, server_default=OwnershipStatus.PENDING.value)
    assigned_by_id: Mapped[uuid.UUID]
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Why the assignee disputed, or why the last reassignment happened.
    reason: Mapped[str | None] = mapped_column(Text)

    asset: Mapped[Asset] = relationship(back_populates="ownerships")
