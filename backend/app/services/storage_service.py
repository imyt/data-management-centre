"""Service for Storage & Retention Control Plane."""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.storage_control import (
    StorageControl,
    StorageTypeEnum,
    EncryptionAlgorithmEnum,
    PurgeMechanismEnum,
)
from app.models.compliance import ComplianceIssue, IssueStatusEnum


class StorageService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_by_app(self, app_head_id: uuid.UUID) -> List[Dict[str, Any]]:
        """List all storage repositories for an application with purge health calculation."""
        res = await self.session.execute(
            select(StorageControl)
            .options(selectinload(StorageControl.attested_by_user))
            .where(StorageControl.app_head_id == app_head_id)
            .order_by(StorageControl.storage_name.asc())
        )
        storages = res.scalars().all()
        now = datetime.now(timezone.utc)

        results = []
        for s in storages:
            # Calculate purge health
            last_purge = s.last_purge_attestation_at
            if last_purge and last_purge.tzinfo is None:
                last_purge = last_purge.replace(tzinfo=timezone.utc)

            is_overdue = False
            days_since_purge = None
            if last_purge:
                days_since_purge = (now - last_purge).days
                if days_since_purge > s.retention_period_days:
                    is_overdue = True
            else:
                is_overdue = True

            results.append({
                "id": str(s.id),
                "app_head_id": str(s.app_head_id),
                "storage_name": s.storage_name,
                "storage_type": s.storage_type.value,
                "encryption_algorithm": s.encryption_algorithm.value,
                "kms_key_arn": s.kms_key_arn,
                "retention_period_days": s.retention_period_days,
                "purge_mechanism": s.purge_mechanism.value,
                "legal_hold_active": s.legal_hold_active,
                "legal_hold_reason": s.legal_hold_reason,
                "last_purge_attestation_at": last_purge.isoformat() if last_purge else None,
                "days_since_purge": days_since_purge,
                "is_purge_overdue": is_overdue,
                "attested_by_name": s.attested_by_user.full_name if s.attested_by_user else None,
                "created_at": s.created_at.isoformat(),
            })
        return results

    async def create_storage_control(
        self,
        app_head_id: uuid.UUID,
        storage_name: str,
        storage_type: StorageTypeEnum,
        encryption_algorithm: EncryptionAlgorithmEnum,
        kms_key_arn: Optional[str],
        retention_period_days: int,
        purge_mechanism: PurgeMechanismEnum,
        user_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Register a new storage repository under an application."""
        storage = StorageControl(
            app_head_id=app_head_id,
            storage_name=storage_name,
            storage_type=storage_type,
            encryption_algorithm=encryption_algorithm,
            kms_key_arn=kms_key_arn,
            retention_period_days=retention_period_days,
            purge_mechanism=purge_mechanism,
            legal_hold_active=False,
            last_purge_attestation_at=datetime.now(timezone.utc),
            last_purge_attested_by=user_id,
        )
        self.session.add(storage)
        await self.session.commit()
        await self.session.refresh(storage)
        return {"id": str(storage.id), "storage_name": storage.storage_name}

    async def toggle_legal_hold(
        self,
        storage_id: uuid.UUID,
        active: bool,
        reason: Optional[str],
        user_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Enable or disable legal hold on repository."""
        res = await self.session.execute(
            select(StorageControl).where(StorageControl.id == storage_id)
        )
        storage = res.scalar_one_or_none()
        if not storage:
            raise ValueError("Storage control not found.")

        storage.legal_hold_active = active
        storage.legal_hold_reason = reason if active else None
        await self.session.commit()
        return {
            "id": str(storage.id),
            "storage_name": storage.storage_name,
            "legal_hold_active": storage.legal_hold_active,
            "message": f"Legal hold {'activated' if active else 'lifted'} for {storage.storage_name}."
        }

    async def attest_purge(
        self,
        storage_id: uuid.UUID,
        user_id: uuid.UUID,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record manual or CI/CD purge attestation."""
        res = await self.session.execute(
            select(StorageControl).where(StorageControl.id == storage_id)
        )
        storage = res.scalar_one_or_none()
        if not storage:
            raise ValueError("Storage control not found.")

        now = datetime.now(timezone.utc)
        storage.last_purge_attestation_at = now
        storage.last_purge_attested_by = user_id

        # Also resolve any open STOR_001 issues for this storage
        issues_res = await self.session.execute(
            select(ComplianceIssue).where(
                ComplianceIssue.storage_control_id == storage_id,
                ComplianceIssue.rule_code == "STOR_001",
                ComplianceIssue.status == IssueStatusEnum.OPEN,
            )
        )
        for issue in issues_res.scalars().all():
            issue.status = IssueStatusEnum.RESOLVED
            issue.resolved_at = now

        await self.session.commit()
        return {
            "id": str(storage.id),
            "storage_name": storage.storage_name,
            "last_purge_attestation_at": now.isoformat(),
            "message": f"Purge attestation recorded for {storage.storage_name}."
        }
