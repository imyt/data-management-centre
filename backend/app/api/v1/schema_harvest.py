"""API Router for Schema Harvesting and Column-Grain Drift Engine."""
import uuid
from typing import Annotated, Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_user, get_schema_harvest_service
from app.models.physical_schema import MaskingStrategyEnum
from app.models.data_movement import ISRClassificationEnum
from app.models.user import User
from app.services.schema_harvest_service import SchemaHarvestService

router = APIRouter(prefix="/schema-harvest", tags=["Schema Harvesting & Drift Engine"])


class TriggerHarvestRequest(BaseModel):
    app_head_id: uuid.UUID
    storage_control_id: Optional[uuid.UUID] = None


class UpdateColumnClassificationRequest(BaseModel):
    is_pii: bool
    masking_strategy: MaskingStrategyEnum
    isr_classification: ISRClassificationEnum
    business_term_name: Optional[str] = None


@router.get("/app/{app_head_id}/tables")
async def list_tables(
    app_head_id: uuid.UUID,
    service: Annotated[SchemaHarvestService, Depends(get_schema_harvest_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> List[Dict[str, Any]]:
    """List physical tables under an application with column counts and drift flags."""
    return await service.list_tables(app_head_id)


@router.get("/app/{app_head_id}/columns")
async def list_columns(
    app_head_id: uuid.UUID,
    service: Annotated[SchemaHarvestService, Depends(get_schema_harvest_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    table_id: Optional[uuid.UUID] = Query(None),
    drift_status: Optional[str] = Query(None),
) -> List[Dict[str, Any]]:
    """List physical columns with atomic data governance attributes and drift states."""
    return await service.list_columns(
        app_head_id=app_head_id,
        table_id=table_id,
        drift_status=drift_status,
    )


@router.post("/trigger")
async def trigger_harvest(
    req: TriggerHarvestRequest,
    service: Annotated[SchemaHarvestService, Depends(get_schema_harvest_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Dict[str, Any]:
    """Execute on-demand physical schema harvest, detect drift, and flag unclassified columns."""
    return await service.trigger_harvest(
        app_head_id=req.app_head_id,
        storage_control_id=req.storage_control_id,
        user_id=current_user.id,
    )


@router.put("/columns/{column_id}/classification")
async def update_column_classification(
    column_id: uuid.UUID,
    req: UpdateColumnClassificationRequest,
    service: Annotated[SchemaHarvestService, Depends(get_schema_harvest_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Dict[str, Any]:
    """Update atomic classification, PII flag, and masking strategy for a physical column."""
    try:
        return await service.update_column_classification(
            column_id=column_id,
            is_pii=req.is_pii,
            masking_strategy=req.masking_strategy,
            isr_classification=req.isr_classification,
            business_term_name=req.business_term_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
