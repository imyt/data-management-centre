from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.organization import Community
from app.models.user import User
from app.schemas.organization import CommunityCreate, CommunityRead

router = APIRouter(prefix="/communities", tags=["Organizational Hierarchy"])


@router.get("", response_model=List[CommunityRead])
async def list_communities(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List organizational communities with child domains."""
    result = await db.execute(
        select(Community).options(selectinload(Community.domains))
    )
    return result.scalars().all()


@router.post("", response_model=CommunityRead, status_code=status.HTTP_201_CREATED)
async def create_community(
    community_in: CommunityCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Create a new organizational community (requires authentication)."""
    community = Community(
        name=community_in.name,
        description=community_in.description,
        parent_community_id=community_in.parent_community_id,
    )
    db.add(community)
    await db.commit()
    await db.refresh(community, attribute_names=["domains"])
    return community
