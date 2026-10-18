"""Database access for connectors. Only the service uses it."""

import uuid
from dataclasses import dataclass

from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import Session

from app.modules.connectors.adapters import HarvestedObject
from app.modules.connectors.domain import ObjectKind, SnapshotStatus
from app.modules.connectors.models import HarvestSnapshot, PhysicalObject, PhysicalObjectMapping


@dataclass(frozen=True)
class ObjectRow:
    object: PhysicalObject
    mapping: PhysicalObjectMapping | None


class ConnectorsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    # --- Snapshots

    def add_snapshot(
        self,
        data_store_id: uuid.UUID,
        status: SnapshotStatus,
        *,
        error: str | None,
        requested_by: str | None,
        objects: list[HarvestedObject],
    ) -> HarvestSnapshot:
        snapshot = HarvestSnapshot(
            data_store_id=data_store_id, status=status.value, error=error, requested_by=requested_by
        )
        self._session.add(snapshot)
        self._session.flush()
        self._session.add_all(
            PhysicalObject(
                snapshot_id=snapshot.id,
                kind=o.kind.value,
                path=o.path,
                name=o.name,
                parent_path=o.parent_path,
                ordinal=o.ordinal,
                data_type=o.data_type,
                row_count=o.row_count,
            )
            for o in objects
        )
        self._session.flush()
        self._session.refresh(snapshot)
        return snapshot

    def recent_snapshots(self, data_store_id: uuid.UUID, limit: int) -> list[HarvestSnapshot]:
        return list(
            self._session.scalars(
                select(HarvestSnapshot)
                .where(HarvestSnapshot.data_store_id == data_store_id)
                .order_by(HarvestSnapshot.taken_at.desc(), HarvestSnapshot.id.desc())
                .limit(limit)
            )
        )

    def last_successful_snapshot(self, data_store_id: uuid.UUID) -> HarvestSnapshot | None:
        return self._session.scalar(
            select(HarvestSnapshot)
            .where(
                HarvestSnapshot.data_store_id == data_store_id,
                HarvestSnapshot.status == SnapshotStatus.SUCCEEDED.value,
            )
            .order_by(HarvestSnapshot.taken_at.desc(), HarvestSnapshot.id.desc())
            .limit(1)
        )

    def object_counts(self, snapshot_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict[str, int]]:
        rows = self._session.execute(
            select(PhysicalObject.snapshot_id, PhysicalObject.kind, func.count())
            .where(PhysicalObject.snapshot_id.in_(snapshot_ids))
            .group_by(PhysicalObject.snapshot_id, PhysicalObject.kind)
        )
        counts: dict[uuid.UUID, dict[str, int]] = {}
        for snapshot_id, kind, count in rows:
            counts.setdefault(snapshot_id, {})[kind] = count
        return counts

    # --- Objects and their mappings

    def _rows(
        self,
        data_store_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        *,
        kind: ObjectKind | None,
        parent_path: str | None,
        mapped: bool | None,
    ) -> Select[PhysicalObject, PhysicalObjectMapping]:
        statement = (
            select(PhysicalObject, PhysicalObjectMapping)
            .outerjoin(
                PhysicalObjectMapping,
                and_(
                    PhysicalObjectMapping.data_store_id == data_store_id,
                    PhysicalObjectMapping.path == PhysicalObject.path,
                ),
            )
            .where(PhysicalObject.snapshot_id == snapshot_id)
        )
        if kind is not None:
            statement = statement.where(PhysicalObject.kind == kind.value)
        if parent_path is not None:
            statement = statement.where(PhysicalObject.parent_path == parent_path)
        if mapped is not None:
            # Schemas are structure, not something to map.
            statement = statement.where(PhysicalObject.kind != ObjectKind.SCHEMA.value)
            statement = statement.where(
                PhysicalObjectMapping.id.is_not(None)
                if mapped
                else PhysicalObjectMapping.id.is_(None)
            )
        return statement

    def list_objects(
        self,
        data_store_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        *,
        kind: ObjectKind | None,
        parent_path: str | None,
        mapped: bool | None,
        after: str | None,
        limit: int,
    ) -> list[ObjectRow]:
        statement = self._rows(
            data_store_id, snapshot_id, kind=kind, parent_path=parent_path, mapped=mapped
        )
        if after is not None:
            statement = statement.where(PhysicalObject.path > after)
        statement = statement.order_by(PhysicalObject.path, PhysicalObject.ordinal).limit(limit)
        return [ObjectRow(o, m) for o, m in self._session.execute(statement)]

    def count_objects(
        self,
        data_store_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        *,
        kind: ObjectKind | None,
        parent_path: str | None,
        mapped: bool | None,
    ) -> int:
        subquery = self._rows(
            data_store_id, snapshot_id, kind=kind, parent_path=parent_path, mapped=mapped
        ).subquery()
        return self._session.scalar(select(func.count()).select_from(subquery)) or 0

    def get_object(self, snapshot_id: uuid.UUID, path: str) -> PhysicalObject | None:
        return self._session.scalar(
            select(PhysicalObject).where(
                PhysicalObject.snapshot_id == snapshot_id, PhysicalObject.path == path
            )
        )

    def columns_of(self, snapshot_id: uuid.UUID, table_path: str) -> list[PhysicalObject]:
        return list(
            self._session.scalars(
                select(PhysicalObject)
                .where(
                    PhysicalObject.snapshot_id == snapshot_id,
                    PhysicalObject.parent_path == table_path,
                    PhysicalObject.kind == ObjectKind.COLUMN.value,
                )
                .order_by(PhysicalObject.ordinal)
            )
        )

    def get_mapping(self, data_store_id: uuid.UUID, path: str) -> PhysicalObjectMapping | None:
        return self._session.scalar(
            select(PhysicalObjectMapping).where(
                PhysicalObjectMapping.data_store_id == data_store_id,
                PhysicalObjectMapping.path == path,
            )
        )

    def add_mapping(self, mapping: PhysicalObjectMapping) -> PhysicalObjectMapping:
        self._session.add(mapping)
        self._session.flush()
        self._session.refresh(mapping)
        return mapping
