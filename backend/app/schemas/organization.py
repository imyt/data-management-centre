import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.models.organization import DomainTypeEnum


class DomainBase(BaseModel):
    name: str
    description: Optional[str] = None
    domain_type: DomainTypeEnum = DomainTypeEnum.GLOSSARY


class DomainCreate(DomainBase):
    community_id: uuid.UUID


class DomainRead(DomainBase):
    id: uuid.UUID
    community_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CommunityBase(BaseModel):
    name: str
    description: Optional[str] = None
    parent_community_id: Optional[uuid.UUID] = None


class CommunityCreate(CommunityBase):
    pass


class CommunityRead(CommunityBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    domains: List[DomainRead] = []

    model_config = ConfigDict(from_attributes=True)


class CommunityTreeRead(CommunityRead):
    sub_communities: List["CommunityTreeRead"] = []

    model_config = ConfigDict(from_attributes=True)
