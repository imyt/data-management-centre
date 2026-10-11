from typing import Annotated, List
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.metamodel import AssetType, AttributeType, RelationType, AssetTypeAttributeAssignment
from app.schemas.metamodel import AssetTypeRead, AttributeTypeRead, RelationTypeRead

router = APIRouter(prefix="/metamodel", tags=["Metamodel Engine"])


@router.get("/asset-types", response_model=List[AssetTypeRead])
async def list_asset_types(
    db: Annotated[AsyncSession, Depends(get_db)],
    include_deprecated: bool = False,
):
    """Retrieve all configured Asset Types with assigned attribute metadata."""
    query = select(AssetType).options(
        selectinload(AssetType.attribute_assignments).selectinload(AssetTypeAttributeAssignment.attribute_type)
    )
    if not include_deprecated:
        query = query.where(AssetType.is_deprecated == False)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/attribute-types", response_model=List[AttributeTypeRead])
async def list_attribute_types(
    db: Annotated[AsyncSession, Depends(get_db)],
    include_deprecated: bool = False,
):
    """Retrieve all Metamodel Attribute Types."""
    query = select(AttributeType)
    if not include_deprecated:
        query = query.where(AttributeType.is_deprecated == False)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/relation-types", response_model=List[RelationTypeRead])
async def list_relation_types(
    db: Annotated[AsyncSession, Depends(get_db)],
    include_deprecated: bool = False,
):
    """Retrieve all bidirectional semantic Relation Types."""
    query = select(RelationType)
    if not include_deprecated:
        query = query.where(RelationType.is_deprecated == False)
    result = await db.execute(query)
    return result.scalars().all()
