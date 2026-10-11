"""Service Tier: Cohesive domain service managing metamodel types and attribute definitions."""
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.exceptions import EntityNotFoundException
from app.domain.validation.attribute_validator import validate_asset_attributes
from app.models.metamodel import (
    AssetType,
    AssetTypeAttributeAssignment,
    AttributeType,
    RelationType,
)


class MetamodelService:
    """Cohesive business logic service for governance metamodels and dynamic schemas."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_asset_types(self) -> List[AssetType]:
        """Fetch all metamodel asset types with nested attribute schemas."""
        stmt = (
            select(AssetType)
            .options(
                selectinload(AssetType.attribute_assignments).selectinload(
                    AssetTypeAttributeAssignment.attribute_type
                )
            )
            .order_by(AssetType.name.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_asset_type(self, asset_type_id: uuid.UUID) -> AssetType:
        """Fetch single asset type with attribute definitions."""
        stmt = (
            select(AssetType)
            .options(
                selectinload(AssetType.attribute_assignments).selectinload(
                    AssetTypeAttributeAssignment.attribute_type
                )
            )
            .where(AssetType.id == asset_type_id)
        )
        result = await self.db.execute(stmt)
        item = result.scalar_one_or_none()
        if not item:
            raise EntityNotFoundException(f"Asset type '{asset_type_id}' not found.")
        return item

    async def validate_attributes(
        self, asset_type_id: uuid.UUID, attributes: Dict[str, Any]
    ) -> List[str]:
        """Validate an attribute payload against an asset type's attribute definitions."""
        asset_type = await self.get_asset_type(asset_type_id)
        return validate_asset_attributes(attributes, asset_type.attribute_assignments)
