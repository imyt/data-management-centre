"""API shapes for harvest: status, physical objects and their mappings."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas import Envelope, ListEnvelope
from app.modules.connectors.domain import ObjectKind, SnapshotStatus


class SnapshotRead(BaseModel):
    """One harvest run. A failed run has no objects, only the reason."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: SnapshotStatus
    taken_at: datetime
    error: str | None = Field(description="Why the run failed, safe to show to users.")
    schemas: int
    tables: int
    columns: int


class ObjectCounts(BaseModel):
    """What the last successful harvest found, and how much of it is not yet mapped."""

    schemas: int
    tables: int
    columns: int
    unmapped_tables: int
    unmapped_columns: int


class HarvestStatusRead(BaseModel):
    data_store_id: uuid.UUID
    last_run: SnapshotRead | None = Field(description="The latest run, whether it worked or not.")
    objects: ObjectCounts | None = Field(
        description="From the last successful run; null if no run has succeeded."
    )
    recent_runs: list[SnapshotRead] = Field(description="Latest first.")


class ObjectMappingRead(BaseModel):
    asset_id: uuid.UUID | None = Field(description="Set on a table.")
    asset_name: str | None
    data_element_id: uuid.UUID | None = Field(description="Set on a column.")


class PhysicalObjectRead(BaseModel):
    id: uuid.UUID
    kind: ObjectKind
    path: str = Field(description="Dotted, e.g. `public.orders.id`.")
    name: str
    parent_path: str | None
    data_type: str | None
    row_count: int | None = Field(description="Estimated from statistics; harvest reads no rows.")
    mapping: ObjectMappingRead | None = Field(
        description="Null for an unmapped table or column, and for schemas."
    )


class MapTable(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, description="The table's path, e.g. `public.orders`.")
    asset_id: uuid.UUID = Field(
        description="The asset the table stores. Its columns are matched to the asset's data "
        "elements by name, and the missing elements are added."
    )


class CreateAssets(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paths: list[str] = Field(
        min_length=1, max_length=100, description="Unmapped tables to declare an asset for each."
    )
    retention_policy_id: uuid.UUID = Field(description="How long the data may be kept.")
    data_category_id: uuid.UUID | None = None
    owner_id: uuid.UUID | None = Field(
        default=None,
        description="A Data Owner in the application's domain, who is asked to confirm.",
    )


class CreatedAsset(BaseModel):
    path: str
    asset_id: uuid.UUID
    asset_name: str


class HarvestStatusResponse(Envelope[HarvestStatusRead]):
    pass


class PhysicalObjectPage(ListEnvelope[PhysicalObjectRead]):
    pass


class PhysicalObjectResponse(Envelope[PhysicalObjectRead]):
    pass


class CreatedAssetList(Envelope[list[CreatedAsset]]):
    pass
