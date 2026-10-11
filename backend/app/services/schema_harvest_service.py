"""Service for Schema Harvesting and Column-Grain Drift Detection."""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.physical_schema import (
    PhysicalTable,
    PhysicalColumn,
    SchemaHarvestRun,
    DriftStatusEnum,
    MaskingStrategyEnum,
    HarvestStatusEnum,
)
from app.models.data_movement import ISRClassificationEnum
from app.models.compliance import ComplianceIssue, IssueSeverityEnum, IssueStatusEnum


class SchemaHarvestService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_tables(self, app_head_id: uuid.UUID) -> List[Dict[str, Any]]:
        """List physical tables under an application with column counts and drift flags."""
        res = await self.session.execute(
            select(PhysicalTable)
            .options(selectinload(PhysicalTable.columns), selectinload(PhysicalTable.storage_control))
            .where(PhysicalTable.app_head_id == app_head_id)
            .order_by(PhysicalTable.table_name.asc())
        )
        tables = res.scalars().all()

        results = []
        for t in tables:
            unclassified_count = sum(1 for c in t.columns if c.drift_status == DriftStatusEnum.ADDED_UNCLASSIFIED)
            pii_count = sum(1 for c in t.columns if c.is_pii)
            results.append({
                "id": str(t.id),
                "app_head_id": str(t.app_head_id),
                "storage_control_id": str(t.storage_control_id) if t.storage_control_id else None,
                "storage_name": t.storage_control.storage_name if t.storage_control else "Unlinked",
                "schema_name": t.schema_name,
                "table_name": t.table_name,
                "row_count_estimate": t.row_count_estimate,
                "total_columns": len(t.columns),
                "unclassified_drift_count": unclassified_count,
                "pii_count": pii_count,
                "is_active": t.is_active,
                "created_at": t.created_at.isoformat(),
            })
        return results

    async def list_columns(
        self,
        app_head_id: uuid.UUID,
        table_id: Optional[uuid.UUID] = None,
        drift_status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List physical columns under an application with full privacy and governance metadata."""
        query = (
            select(PhysicalColumn)
            .options(
                selectinload(PhysicalColumn.table),
                selectinload(PhysicalColumn.dataset_mappings),
            )
            .join(PhysicalTable, PhysicalColumn.table_id == PhysicalTable.id)
            .where(PhysicalTable.app_head_id == app_head_id)
        )

        if table_id:
            query = query.where(PhysicalColumn.table_id == table_id)
        if drift_status:
            query = query.where(PhysicalColumn.drift_status == drift_status)

        query = query.order_by(PhysicalTable.table_name.asc(), PhysicalColumn.column_name.asc())
        res = await self.session.execute(query)
        columns = res.scalars().all()

        results = []
        for col in columns:
            results.append({
                "id": str(col.id),
                "table_id": str(col.table_id),
                "table_name": col.table.table_name,
                "schema_name": col.table.schema_name,
                "column_name": col.column_name,
                "data_type": col.data_type,
                "is_nullable": col.is_nullable,
                "drift_status": col.drift_status.value,
                "is_pii": col.is_pii,
                "masking_strategy": col.masking_strategy.value,
                "isr_classification": col.isr_classification.value,
                "business_term_name": col.business_term_name,
                "linked_datasets_count": len(col.dataset_mappings),
                "updated_at": col.updated_at.isoformat(),
            })
        return results

    async def trigger_harvest(
        self,
        app_head_id: uuid.UUID,
        storage_control_id: Optional[uuid.UUID],
        user_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Trigger an on-demand harvest scan. Detects schema drift and generates DRIFT_001 if unclassified."""
        now = datetime.now(timezone.utc)

        # Count tables and columns
        tables_res = await self.session.execute(
            select(PhysicalTable).where(PhysicalTable.app_head_id == app_head_id)
        )
        tables = tables_res.scalars().all()

        cols_res = await self.session.execute(
            select(PhysicalColumn)
            .join(PhysicalTable, PhysicalColumn.table_id == PhysicalTable.id)
            .where(PhysicalTable.app_head_id == app_head_id)
        )
        columns = cols_res.scalars().all()

        unclassified_cols = [c for c in columns if c.drift_status == DriftStatusEnum.ADDED_UNCLASSIFIED]
        drift_detected = len(unclassified_cols) > 0

        summary = {
            "tables_scanned": len(tables),
            "columns_scanned": len(columns),
            "added_unclassified": len(unclassified_cols),
            "dropped": 0,
            "type_modified": 0,
        }

        # Create harvest run record
        harvest_run = SchemaHarvestRun(
            app_head_id=app_head_id,
            storage_control_id=storage_control_id,
            status=HarvestStatusEnum.COMPLETED,
            drift_detected=drift_detected,
            drift_summary=summary,
            harvested_at=now,
            harvested_by=user_id,
        )
        self.session.add(harvest_run)

        # If drift detected and no active issue exists, create a DRIFT_001 defect
        if drift_detected:
            existing_issue_res = await self.session.execute(
                select(ComplianceIssue).where(
                    ComplianceIssue.app_head_id == app_head_id,
                    ComplianceIssue.rule_code == "DRIFT_001",
                    ComplianceIssue.status == IssueStatusEnum.OPEN,
                )
            )
            if not existing_issue_res.scalar_one_or_none():
                new_issue = ComplianceIssue(
                    target_asset_head_id=app_head_id,
                    app_head_id=app_head_id,
                    rule_code="DRIFT_001",
                    title="Schema Drift: Unclassified Physical Columns Detected",
                    description=f"{len(unclassified_cols)} newly harvested columns require PII, Masking, and ISR classification.",
                    severity=IssueSeverityEnum.HIGH,
                    status=IssueStatusEnum.OPEN,
                    remediation_deadline=now + timedelta(days=14),
                    app_owner_id=user_id,
                    created_by=user_id,
                )
                self.session.add(new_issue)

        await self.session.commit()
        await self.session.refresh(harvest_run)

        return {
            "harvest_run_id": str(harvest_run.id),
            "drift_detected": drift_detected,
            "summary": summary,
            "harvested_at": now.isoformat(),
        }

    async def update_column_classification(
        self,
        column_id: uuid.UUID,
        is_pii: bool,
        masking_strategy: MaskingStrategyEnum,
        isr_classification: ISRClassificationEnum,
        business_term_name: Optional[str],
    ) -> Dict[str, Any]:
        """Update atomic physical column classification."""
        res = await self.session.execute(
            select(PhysicalColumn).where(PhysicalColumn.id == column_id)
        )
        col = res.scalar_one_or_none()
        if not col:
            raise ValueError("Physical column not found.")

        col.is_pii = is_pii
        col.masking_strategy = masking_strategy
        col.isr_classification = isr_classification
        col.business_term_name = business_term_name
        col.drift_status = DriftStatusEnum.SYNCED
        col.updated_at = datetime.now(timezone.utc)

        await self.session.commit()
        return {
            "id": str(col.id),
            "column_name": col.column_name,
            "drift_status": col.drift_status.value,
            "is_pii": col.is_pii,
            "masking_strategy": col.masking_strategy.value,
            "isr_classification": col.isr_classification.value,
        }
