"""The `inventory` schema: reference data, applications, their environments and data stores."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, Timestamps, UUIDv7PrimaryKey
from app.modules.inventory.domain import (
    Criticality,
    DataStoreType,
    EnvironmentType,
    HarvestStatus,
    Hosting,
    LifecycleStatus,
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
