import uuid
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.organization import Domain, DomainTypeEnum
from app.models.user import User
from app.schemas.organization import DomainCreate, DomainRead

router = APIRouter(prefix="/domains", tags=["Governance Domains"])


@router.get("", response_model=List[DomainRead])
async def list_domains(
    db: Annotated[AsyncSession, Depends(get_db)],
    community_id: Optional[uuid.UUID] = None,
    domain_type: Optional[DomainTypeEnum] = None,
):
    """List governance domains with optional community or type filter."""
    query = select(Domain)
    if community_id:
        query = query.where(Domain.community_id == community_id)
    if domain_type:
        query = query.where(Domain.domain_type == domain_type)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=DomainRead, status_code=status.HTTP_201_CREATED)
async def create_domain(
    domain_in: DomainCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Create a new domain within a community."""
    domain = Domain(
        community_id=domain_in.community_id,
        name=domain_in.name,
        description=domain_in.description,
        domain_type=domain_in.domain_type,
    )
    db.add(domain)
    await db.commit()
    await db.refresh(domain)
    return domain
