"""Request bodies, read models and response envelopes for the inventory API."""

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.core.schemas import Envelope, ListEnvelope
from app.modules.inventory.domain import (
    Criticality,
    DataStoreType,
    EnvironmentType,
    HarvestStatus,
    Hosting,
    LifecycleStatus,
)

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Code = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{1,39}$"),
]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
# A reference into the secrets store, e.g. "vault:dmc/orders-db". Never a password or a DSN.
ConnectionRef = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, pattern=r"^[a-z][a-z0-9+.-]*:[^\s@]+$", max_length=500
    ),
]

# --- Reference data


class ReferenceItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str | None


class RetentionPolicyRead(ReferenceItemRead):
    retention_days: int


class ReferenceItemList(ListEnvelope[ReferenceItemRead]):
    pass


class RetentionPolicyList(ListEnvelope[RetentionPolicyRead]):
    pass


# --- Applications


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name
    code: Code = Field(description="Short unique code, e.g. `ORD`. Letters, digits, - and _.")
    description: Description | None = None
    domain_id: uuid.UUID
    criticality: Criticality
    hosting: Hosting
    lifecycle_status: LifecycleStatus = LifecycleStatus.PLANNED
    app_owner_id: uuid.UUID | None = None
    tech_owner_id: uuid.UUID | None = None


class ApplicationUpdate(BaseModel):
    """Only the fields sent are changed."""

    model_config = ConfigDict(extra="forbid")

    name: Name | None = None
    code: Code | None = None
    description: Description | None = None
    domain_id: uuid.UUID | None = None
    criticality: Criticality | None = None
    hosting: Hosting | None = None
    lifecycle_status: LifecycleStatus | None = None
    app_owner_id: uuid.UUID | None = None
    tech_owner_id: uuid.UUID | None = None


class EnvironmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name
    type: EnvironmentType
    region_id: uuid.UUID


class DataStoreCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name
    type: DataStoreType
    platform: Name = Field(description="The product, e.g. `PostgreSQL 18` or `Amazon S3`.")
    region_id: uuid.UUID
    connection_ref: ConnectionRef = Field(
        description="Where the secrets store keeps the credentials, e.g. `vault:dmc/orders-db`."
    )


class ReferenceRef(BaseModel):
    """A reference-data item embedded in another resource."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str


class DataStoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    environment_id: uuid.UUID
    name: str
    type: DataStoreType
    platform: str
    region: ReferenceRef
    connection_ref: str
    harvest_status: HarvestStatus
    last_harvested_at: datetime | None
    created_at: datetime


class EnvironmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    name: str
    type: EnvironmentType
    region: ReferenceRef
    created_at: datetime


class EnvironmentDetail(EnvironmentRead):
    data_stores: list[DataStoreRead]


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str
    description: str | None
    domain: ReferenceRef
    criticality: Criticality
    hosting: Hosting
    lifecycle_status: LifecycleStatus
    app_owner_id: uuid.UUID | None
    tech_owner_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class ApplicationDetail(ApplicationRead):
    environments: list[EnvironmentDetail]


class ApplicationPage(ListEnvelope[ApplicationRead]):
    pass


class ApplicationResponse(Envelope[ApplicationDetail]):
    pass


class EnvironmentResponse(Envelope[EnvironmentRead]):
    pass


class DataStoreResponse(Envelope[DataStoreRead]):
    pass
