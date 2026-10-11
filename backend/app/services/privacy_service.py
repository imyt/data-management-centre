"""Service for Privacy & Consumer Usage Entitlements Control Plane."""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.privacy_entitlement import UsageEntitlement
from app.models.physical_schema import PhysicalColumn, MaskingStrategyEnum
from app.models.asset import AssetHead
from app.models.data_movement import ApplicationProfile


class PrivacyService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_entitlements(self, app_head_id: uuid.UUID) -> List[Dict[str, Any]]:
        """List consumer entitlements with authorized purpose and geo-fencing."""
        res = await self.session.execute(
            select(UsageEntitlement)
            .options(
                selectinload(UsageEntitlement.approver),
            )
            .where(UsageEntitlement.app_head_id == app_head_id)
            .order_by(UsageEntitlement.created_at.desc())
        )
        entitlements = res.scalars().all()

        # Fetch names for consumer app heads
        consumer_head_ids = [e.consumer_app_head_id for e in entitlements]
        apps_res = await self.session.execute(
            select(ApplicationProfile).where(ApplicationProfile.asset_head_id.in_(consumer_head_ids))
        )
        profiles_by_head = {p.asset_head_id: p for p in apps_res.scalars().all()}

        results = []
        now = datetime.now(timezone.utc)
        for e in entitlements:
            prof = profiles_by_head.get(e.consumer_app_head_id)
            expires = e.expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)

            is_expired = now > expires
            results.append({
                "id": str(e.id),
                "app_head_id": str(e.app_head_id),
                "consumer_app_head_id": str(e.consumer_app_head_id),
                "consumer_app_name": prof.itsm_system_name if prof else "External Consumer App",
                "consumer_system_id": prof.itsm_system_id if prof else "EXT-CONSUMER",
                "authorized_purpose": e.authorized_purpose,
                "allowed_geo_regions": e.allowed_geo_regions,
                "is_active": e.is_active and not is_expired,
                "is_expired": is_expired,
                "expires_at": expires.isoformat(),
                "approved_by_name": e.approver.full_name if e.approver else "System Attested",
                "created_at": e.created_at.isoformat(),
            })
        return results

    async def create_entitlement(
        self,
        app_head_id: uuid.UUID,
        consumer_app_head_id: uuid.UUID,
        authorized_purpose: str,
        allowed_geo_regions: List[str],
        duration_days: int,
        user_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Authorize a consumer application under purpose and geo-fencing constraints."""
        expires_at = datetime.now(timezone.utc) + timedelta(days=duration_days)
        ent = UsageEntitlement(
            app_head_id=app_head_id,
            consumer_app_head_id=consumer_app_head_id,
            authorized_purpose=authorized_purpose,
            allowed_geo_regions=allowed_geo_regions,
            is_active=True,
            approved_by=user_id,
            expires_at=expires_at,
        )
        self.session.add(ent)
        await self.session.commit()
        await self.session.refresh(ent)
        return {
            "id": str(ent.id),
            "authorized_purpose": ent.authorized_purpose,
            "expires_at": ent.expires_at.isoformat(),
            "message": "Consumer entitlement authorized successfully."
        }

    async def revoke_entitlement(self, entitlement_id: uuid.UUID) -> Dict[str, Any]:
        """Revoke consumer application data entitlement."""
        res = await self.session.execute(
            select(UsageEntitlement).where(UsageEntitlement.id == entitlement_id)
        )
        ent = res.scalar_one_or_none()
        if not ent:
            raise ValueError("Entitlement not found.")

        ent.is_active = False
        await self.session.commit()
        return {"id": str(ent.id), "is_active": False, "message": "Entitlement revoked."}
