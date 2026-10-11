import uuid
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.services import (
    AssetService,
    ComplianceService,
    DataMovementService,
    MetamodelService,
    WorkflowService,
    WorkbenchService,
    StorageService,
    SchemaHarvestService,
    PrivacyService,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Dependency that extracts and validates JWT token, returning the current User entity."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = uuid.UUID(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )
    return user


# -----------------------------------------------------------------------------
# Pragmatic 3-Tier Service Dependencies
# -----------------------------------------------------------------------------

def get_asset_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> AssetService:
    """Dependency providing cohesive AssetService for catalog operations."""
    return AssetService(db)


def get_workflow_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> WorkflowService:
    """Dependency providing cohesive WorkflowService for review pipelines."""
    return WorkflowService(db)


def get_compliance_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> ComplianceService:
    """Dependency providing cohesive ComplianceService for scans & remediation."""
    return ComplianceService(db)


def get_metamodel_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> MetamodelService:
    """Dependency providing cohesive MetamodelService for dynamic schemas."""
    return MetamodelService(db)


def get_data_movement_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> DataMovementService:
    """Dependency providing cohesive DataMovementService for data movement & integrity."""
    return DataMovementService(db)


def get_workbench_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> WorkbenchService:
    """Dependency providing WorkbenchService for App Owner remediation workflows."""
    return WorkbenchService(db)


def get_storage_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> StorageService:
    """Dependency providing StorageService for retention and legal hold management."""
    return StorageService(db)


def get_schema_harvest_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> SchemaHarvestService:
    """Dependency providing SchemaHarvestService for drift detection."""
    return SchemaHarvestService(db)


def get_privacy_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> PrivacyService:
    """Dependency providing PrivacyService for consumer app entitlements."""
    return PrivacyService(db)

