import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


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
    metadata: Dict[str, Any] = {}

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
