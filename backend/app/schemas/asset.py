import uuid
from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict
from app.models.asset import VersionStatusEnum


class AssetVersionBase(BaseModel):
    name: str
    description_markdown: Optional[str] = None
    attributes_payload: dict[str, Any] = {}
    relations_snapshot: list[Any] = []


class AssetVersionRead(AssetVersionBase):
    id: uuid.UUID
    asset_head_id: uuid.UUID
    version_number: int
    status: VersionStatusEnum
    created_by: uuid.UUID
    created_at: datetime
    published_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AssetHeadRead(BaseModel):
    id: uuid.UUID
    domain_id: uuid.UUID
    asset_type_id: uuid.UUID
    published_version_id: Optional[uuid.UUID] = None
    active_draft_version_id: Optional[uuid.UUID] = None
    locked_by_user_id: Optional[uuid.UUID] = None
    locked_at: Optional[datetime] = None
    created_at: datetime
    published_version: Optional[AssetVersionRead] = None
    active_draft_version: Optional[AssetVersionRead] = None

    model_config = ConfigDict(from_attributes=True)


class AssetCreate(BaseModel):
    domain_id: uuid.UUID
    asset_type_id: uuid.UUID
    name: str
    description_markdown: Optional[str] = None
    attributes_payload: dict[str, Any] = {}


class AssetDraftUpdate(BaseModel):
    name: Optional[str] = None
    description_markdown: Optional[str] = None
    attributes_payload: Optional[dict[str, Any]] = None


class AssetRelationCreate(BaseModel):
    relation_type_id: uuid.UUID
    target_asset_head_id: uuid.UUID


class AssetRelationRead(BaseModel):
    id: uuid.UUID
    relation_type_id: uuid.UUID
    source_asset_head_id: uuid.UUID
    target_asset_head_id: uuid.UUID
    created_by: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttributeDiffItem(BaseModel):
    attribute_code: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    change_type: str  # "ADDED" | "MODIFIED" | "REMOVED" | "UNCHANGED"


class DiffResponse(BaseModel):
    has_changes: bool
    name_diff: dict[str, Any]
    description_diff: dict[str, Any]
    attributes_diff: List[AttributeDiffItem]
    relations_diff: dict[str, Any]


class LineageNodeRead(BaseModel):
    id: uuid.UUID
    name: str
    asset_type_id: Optional[uuid.UUID] = None
    asset_type_code: Optional[str] = None
    domain_id: Optional[uuid.UUID] = None
    status: Optional[str] = None
    version_number: Optional[int] = None
    is_current: bool = False
    depth: int = 0
    direction: str = "current"
    metadata: dict[str, Any] = {}

    model_config = ConfigDict(from_attributes=True)


class LineageEdgeRead(BaseModel):
    id: uuid.UUID
    source_asset_head_id: uuid.UUID
    target_asset_head_id: uuid.UUID
    relation_type_id: Optional[uuid.UUID] = None
    relation_type_code: Optional[str] = None
    role_name: Optional[str] = None
    direction: str = "downstream"

    model_config = ConfigDict(from_attributes=True)


class LineageGraphRead(BaseModel):
    root_asset_head_id: uuid.UUID
    nodes: List[LineageNodeRead] = []
    edges: List[LineageEdgeRead] = []

    model_config = ConfigDict(from_attributes=True)
