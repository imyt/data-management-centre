"""Tier 1: Presentation / Driving HTTP REST Controller for Curated Asset Catalog."""
from typing import Annotated, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_asset_service, get_current_user
from app.domain.exceptions import (
    ConcurrencyLockException,
    DomainException,
    DraftNotFoundException,
    EntityNotFoundException,
    UnauthorizedDraftModificationException,
    ValidationException,
)
from app.models.user import User
from app.schemas.asset import (
    AssetCreate,
    AssetDraftUpdate,
    AssetHeadRead,
    AssetRelationCreate,
    AssetRelationRead,
    AssetVersionRead,
    DiffResponse,
)
from app.schemas.lineage import LineageGraphRead
from app.services.asset_service import AssetService

router = APIRouter(prefix="/assets", tags=["Curated Asset Catalog"])


def _handle_domain_exception(e: DomainException):
    """Map domain exceptions to HTTP status codes."""
    if isinstance(e, EntityNotFoundException):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    elif isinstance(e, ConcurrencyLockException):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)
    elif isinstance(e, UnauthorizedDraftModificationException):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.message)
    elif isinstance(e, DraftNotFoundException):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    elif isinstance(e, ValidationException):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.message)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)


@router.get("", response_model=List[AssetHeadRead])
async def list_assets(
    service: Annotated[AssetService, Depends(get_asset_service)],
    domain_id: Optional[uuid.UUID] = Query(None, description="Filter by Domain"),
    asset_type_id: Optional[uuid.UUID] = Query(None, description="Filter by Asset Type"),
    status: Optional[str] = Query(None, description="Filter by status (DRAFT, PUBLISHED, etc.)"),
    search: Optional[str] = Query(None, description="Search query matching asset name or description"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List catalog asset heads with optional domain, type, status, and search filters."""
    return await service.list_assets(
        domain_id=domain_id,
        asset_type_id=asset_type_id,
        status=status,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.post("", response_model=AssetHeadRead, status_code=status.HTTP_201_CREATED)
async def create_asset_head_and_initial_draft(
    asset_in: AssetCreate,
    service: Annotated[AssetService, Depends(get_asset_service)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Propose and create a new catalog asset head with an initial working draft (v1 DRAFT)."""
    try:
        return await service.create_asset(
            domain_id=asset_in.domain_id,
            asset_type_id=asset_in.asset_type_id,
            name=asset_in.name,
            user_id=current_user.id,
            description_markdown=asset_in.description_markdown,
            attributes_payload=asset_in.attributes_payload,
        )
    except DomainException as e:
        _handle_domain_exception(e)


@router.get("/{asset_head_id}", response_model=AssetHeadRead)
async def get_asset(
    asset_head_id: uuid.UUID,
    service: Annotated[AssetService, Depends(get_asset_service)],
):
    """Fetch an asset head with its active working draft and published version."""
    try:
        return await service.get_asset_head(asset_head_id)
    except DomainException as e:
        _handle_domain_exception(e)


@router.post("/{asset_head_id}/draft", response_model=AssetVersionRead)
async def acquire_or_fork_draft(
    asset_head_id: uuid.UUID,
    service: Annotated[AssetService, Depends(get_asset_service)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Acquire exclusive editing lease, forking a working draft if only a published version exists."""
    try:
        return await service.acquire_or_fork_draft(
            asset_head_id=asset_head_id,
            user_id=current_user.id,
        )
    except DomainException as e:
        _handle_domain_exception(e)


@router.put("/{asset_head_id}/draft", response_model=AssetVersionRead)
async def update_draft(
    asset_head_id: uuid.UUID,
    update_in: AssetDraftUpdate,
    service: Annotated[AssetService, Depends(get_asset_service)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Update working draft metadata and attributes while holding exclusive editing lease."""
    try:
        return await service.update_draft(
            asset_head_id=asset_head_id,
            user_id=current_user.id,
            name=update_in.name,
            description_markdown=update_in.description_markdown,
            attributes_payload=update_in.attributes_payload,
        )
    except DomainException as e:
        _handle_domain_exception(e)


@router.post("/{asset_head_id}/draft/release-lock")
async def release_lock(
    asset_head_id: uuid.UUID,
    service: Annotated[AssetService, Depends(get_asset_service)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Release exclusive editing lease voluntarily without publishing changes."""
    try:
        released = await service.release_lock(
            asset_head_id=asset_head_id,
            user_id=current_user.id,
        )
        return {"released": released}
    except DomainException as e:
        _handle_domain_exception(e)


@router.get("/{asset_head_id}/diff", response_model=DiffResponse)
async def get_visual_diff(
    asset_head_id: uuid.UUID,
    service: Annotated[AssetService, Depends(get_asset_service)],
):
    """Generate side-by-side visual diff between active working draft and approved published version."""
    try:
        return await service.get_visual_diff(asset_head_id)
    except DomainException as e:
        _handle_domain_exception(e)


@router.post("/{asset_head_id}/publish", response_model=AssetVersionRead)
async def publish_asset_version(
    asset_head_id: uuid.UUID,
    service: Annotated[AssetService, Depends(get_asset_service)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Approve and publish active draft version, generating immutable snapshot and updating head pointer."""
    try:
        return await service.publish_draft(
            asset_head_id=asset_head_id,
            user_id=current_user.id,
        )
    except DomainException as e:
        _handle_domain_exception(e)


@router.get("/{asset_head_id}/history", response_model=List[AssetVersionRead])
async def get_version_history(
    asset_head_id: uuid.UUID,
    service: Annotated[AssetService, Depends(get_asset_service)],
):
    """Retrieve immutable chronological audit ledger of all versions for this asset."""
    try:
        return await service.get_version_history(asset_head_id)
    except DomainException as e:
        _handle_domain_exception(e)


@router.post(
    "/{asset_head_id}/relations",
    response_model=AssetRelationRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_asset_relation(
    asset_head_id: uuid.UUID,
    relation_in: AssetRelationCreate,
    service: Annotated[AssetService, Depends(get_asset_service)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Create a live semantic relationship linking this asset head to a target asset head."""
    try:
        return await service.add_relation(
            source_asset_head_id=asset_head_id,
            target_asset_head_id=relation_in.target_asset_head_id,
            relation_type_id=relation_in.relation_type_id,
            created_by_user_id=current_user.id,
        )
    except DomainException as e:
        _handle_domain_exception(e)


@router.get("/{asset_head_id}/relations", response_model=List[AssetRelationRead])
async def list_asset_relations(
    asset_head_id: uuid.UUID,
    service: Annotated[AssetService, Depends(get_asset_service)],
):
    """List live outgoing semantic relations for this asset head."""
    return await service.list_relations(asset_head_id, direction="outgoing")


@router.get("/{asset_head_id}/lineage", response_model=LineageGraphRead)
async def get_asset_lineage(
    asset_head_id: uuid.UUID,
    service: Annotated[AssetService, Depends(get_asset_service)],
    depth: int = Query(2, ge=1, le=5, description="Traversal depth"),
    direction: str = Query("both", description="Traversal direction: upstream, downstream, or both"),
):
    """Traverse semantic relationships to generate multi-hop lineage graph DAG."""
    try:
        return await service.get_lineage_graph(
            asset_head_id=asset_head_id,
            max_depth=depth,
            direction=direction,
        )
    except DomainException as e:
        _handle_domain_exception(e)
