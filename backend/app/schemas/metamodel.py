import uuid
from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict
from app.models.metamodel import AttributeDataType


class AttributeTypeRead(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    data_type: AttributeDataType
    allowed_values: Optional[Any] = None
    description: Optional[str] = None
    is_deprecated: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssetTypeAttributeAssignmentRead(BaseModel):
    id: uuid.UUID
    attribute_type: AttributeTypeRead
    is_required: bool
    default_value: Optional[str] = None
    display_order: int

    model_config = ConfigDict(from_attributes=True)


class AssetTypeRead(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: Optional[str] = None
    parent_asset_type_id: Optional[uuid.UUID] = None
    is_deprecated: bool
    icon: Optional[str] = None
    created_at: datetime
    attribute_assignments: List[AssetTypeAttributeAssignmentRead] = []

    model_config = ConfigDict(from_attributes=True)


class RelationTypeRead(BaseModel):
    id: uuid.UUID
    code: str
    source_asset_type_id: uuid.UUID
    target_asset_type_id: uuid.UUID
    role_name: str
    co_role_name: str
    description: Optional[str] = None
    is_deprecated: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
