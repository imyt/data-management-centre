"""Public interface of the connectors module: the only file other modules import.

Harvest runs as a job (`connectors.harvest`): on demand, on a schedule, and once when a data store
is registered. A run reads the store's structure with its read-only connection, never with DMC's
own credentials, and either stores a snapshot or records why it failed. Mapping physical objects
to assets and data elements is a person's decision; what has no mapping is flagged unmapped.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.auth import Permission, Principal, Role, allowed_actions, require
from app.core.errors import ConflictError, InvalidInputError, NotFoundError
from app.core.jobs import Job, enqueue
from app.core.pagination import PageResult, decode_cursor, encode_cursor
from app.modules.audit.service import AuditService
from app.modules.connectors.adapters import (
    HarvestAdapter,
    HarvestError,
    adapter_for,
    resolve_connection,
)
from app.modules.connectors.domain import ObjectKind, SnapshotStatus
from app.modules.connectors.models import (
    HarvestSnapshot,
    PhysicalObject,
    PhysicalObjectMapping,
)
from app.modules.connectors.repository import ConnectorsRepository, ObjectRow
from app.modules.connectors.schemas import CreateAssets, MapTable
from app.modules.inventory.service import AssetService, DataStoreRef, InventoryService

HARVEST = "connectors.harvest"
SYSTEM_ACTOR = "system:harvest"
RECENT_RUNS = 10

# Application Owners and Governance register stores, so they decide when to harvest them.
RUN_HARVEST = Permission("run_harvest", {Role.APPLICATION_OWNER, Role.GOVERNANCE})
# Whoever may declare assets may say which asset a table stores.
MAP_OBJECTS = Permission("map_objects", {Role.APPLICATION_OWNER, Role.DATA_OWNER, Role.GOVERNANCE})
_PERMISSIONS = (RUN_HARVEST, MAP_OBJECTS)


def data_store_actions(principal: Principal, domain_id: uuid.UUID) -> list[str]:
    """`allowed_actions` on a data store's harvest, from the same rules the writes check."""
    return allowed_actions(principal, _PERMISSIONS, domain_id)


@dataclass(frozen=True)
class RunView:
    snapshot: HarvestSnapshot
    counts: dict[str, int]


@dataclass(frozen=True)
class StatusView:
    data_store_id: uuid.UUID
    domain_id: uuid.UUID
    runs: list[RunView]
    # From the last successful run: kind → count, plus the unmapped tables and columns.
    objects: dict[str, int] | None


@dataclass(frozen=True)
class ObjectView:
    row: ObjectRow
    asset_name: str | None


class ConnectorsService:
    def __init__(self, session: Session, *, adapter: HarvestAdapter | None = None) -> None:
        self._session = session
        self._repository = ConnectorsRepository(session)
        self._audit = AuditService(session)
        self._inventory = InventoryService(session)
        self._assets = AssetService(session)
        self._adapter = adapter

    # --- Running a harvest

    def request_harvest(self, principal: Principal, data_store_id: uuid.UUID) -> Job:
        """Queue a harvest of the store now; the worker runs it."""
        store = self._inventory.get_data_store(principal, data_store_id)
        require(principal, RUN_HARVEST, store.domain_id)
        job = enqueue(
            self._session,
            HARVEST,
            {"data_store_id": store.id, "requested_by": principal.actor},
            created_by=principal.actor,
            max_attempts=3,
        )
        self._audit.record(
            actor=principal.actor,
            action="data_store.harvest_requested",
            subject_type="data_store",
            subject_id=store.id,
            after={"job_id": job.id},
        )
        return job

    def enqueue_harvest(self, data_store_id: uuid.UUID, *, idempotency_key: str) -> Job:
        """Queue a harvest for the system: a schedule's sweep, or a store just registered."""
        return enqueue(
            self._session,
            HARVEST,
            {"data_store_id": data_store_id, "requested_by": None},
            max_attempts=3,
            idempotency_key=idempotency_key,
        )

    def data_store_ids(self) -> list[uuid.UUID]:
        return self._inventory.list_data_store_ids()

    def run_harvest(self, data_store_id: uuid.UUID, *, requested_by: str | None) -> RunView | None:
        """Harvest a store and record the outcome. None if the store no longer exists.

        A harvest that cannot connect or read is recorded as a failed snapshot, not raised, so
        the failure shows on the store; the next run is the retry.
        """
        store = self._inventory.find_data_store(data_store_id)
        if store is None:
            return None
        actor = requested_by or SYSTEM_ACTOR
        now = datetime.now(UTC)
        try:
            adapter = self._adapter or adapter_for(store.platform, store.type)
            catalog = adapter.harvest(resolve_connection(store.connection_ref))
        except HarvestError as exc:
            snapshot = self._repository.add_snapshot(
                store.id,
                SnapshotStatus.FAILED,
                error=str(exc),
                requested_by=requested_by,
                objects=[],
            )
            self._inventory.record_harvest(store.id, succeeded=False, at=now)
            self._audit.record(
                actor=actor,
                action="data_store.harvest_failed",
                subject_type="data_store",
                subject_id=store.id,
                after={"snapshot_id": snapshot.id, "error": str(exc)},
            )
            return RunView(snapshot, {})

        snapshot = self._repository.add_snapshot(
            store.id,
            SnapshotStatus.SUCCEEDED,
            error=None,
            requested_by=requested_by,
            objects=catalog.objects,
        )
        self._inventory.record_harvest(store.id, succeeded=True, at=snapshot.taken_at)
        counts = self._repository.object_counts([snapshot.id])[snapshot.id]
        self._audit.record(
            actor=actor,
            action="data_store.harvested",
            subject_type="data_store",
            subject_id=store.id,
            after={"snapshot_id": snapshot.id, **counts},
        )
        return RunView(snapshot, counts)

    # --- Status and objects

    def status(self, principal: Principal, data_store_id: uuid.UUID) -> StatusView:
        store = self._inventory.get_data_store(principal, data_store_id)
        snapshots = self._repository.recent_snapshots(store.id, RECENT_RUNS)
        counts = self._repository.object_counts([s.id for s in snapshots]) if snapshots else {}
        runs = [RunView(s, counts.get(s.id, {})) for s in snapshots]
        latest_ok = self._repository.last_successful_snapshot(store.id)
        objects = None
        if latest_ok is not None:
            objects = {
                **(self._repository.object_counts([latest_ok.id]).get(latest_ok.id, {})),
                "unmapped_table": self._repository.count_objects(
                    store.id,
                    latest_ok.id,
                    kind=ObjectKind.TABLE,
                    parent_path=None,
                    mapped=False,
                ),
                "unmapped_column": self._repository.count_objects(
                    store.id,
                    latest_ok.id,
                    kind=ObjectKind.COLUMN,
                    parent_path=None,
                    mapped=False,
                ),
            }
        return StatusView(store.id, store.domain_id, runs, objects)

    def list_objects(
        self,
        principal: Principal,
        data_store_id: uuid.UUID,
        *,
        limit: int,
        cursor: str | None,
        kind: ObjectKind | None = None,
        parent_path: str | None = None,
        mapped: bool | None = None,
    ) -> PageResult[ObjectView]:
        """A page of the last successful harvest's objects, ordered by path."""
        store = self._inventory.get_data_store(principal, data_store_id)
        snapshot = self._repository.last_successful_snapshot(store.id)
        if snapshot is None:
            return PageResult(items=[], next_cursor=None, total=0)
        after = decode_cursor(cursor) if cursor else None
        rows = self._repository.list_objects(
            store.id,
            snapshot.id,
            kind=kind,
            parent_path=parent_path,
            mapped=mapped,
            after=after,
            limit=limit + 1,
        )
        items = rows[:limit]
        next_cursor = encode_cursor(items[-1].object.path) if len(rows) > limit else None
        total = self._repository.count_objects(
            store.id, snapshot.id, kind=kind, parent_path=parent_path, mapped=mapped
        )
        return PageResult(items=self._views(items), next_cursor=next_cursor, total=total)

    def _views(self, rows: list[ObjectRow]) -> list[ObjectView]:
        ids = {r.mapping.asset_id for r in rows if r.mapping and r.mapping.asset_id}
        names = self._assets.asset_names(ids)
        return [
            ObjectView(
                r, names.get(r.mapping.asset_id) if r.mapping and r.mapping.asset_id else None
            )
            for r in rows
        ]

    # --- Mapping

    def map_table(
        self, principal: Principal, data_store_id: uuid.UUID, data: MapTable
    ) -> ObjectView:
        """Say which asset a table stores, and match its columns to the asset's data elements."""
        store = self._inventory.get_data_store(principal, data_store_id)
        require(principal, MAP_OBJECTS, store.domain_id)
        snapshot = self._require_snapshot(store)
        table = self._require_table(snapshot, data.path)
        current = self._repository.get_mapping(store.id, table.path)
        if current is not None and current.asset_id != data.asset_id:
            raise ConflictError(
                "This table is already mapped to another asset.", details={"path": table.path}
            )
        self._map(principal, store, snapshot, table, data.asset_id, existing=current)
        return self._view_of(store.id, table)

    def create_assets(
        self, principal: Principal, data_store_id: uuid.UUID, data: CreateAssets
    ) -> list[tuple[str, uuid.UUID, str]]:
        """Declare a stored dataset for each unmapped table, map it, and ask its Data Owner."""
        store = self._inventory.get_data_store(principal, data_store_id)
        require(principal, MAP_OBJECTS, store.domain_id)
        snapshot = self._require_snapshot(store)
        paths = list(dict.fromkeys(data.paths))
        tables = [self._require_table(snapshot, path) for path in paths]
        mapped = [t.path for t in tables if self._repository.get_mapping(store.id, t.path)]
        if mapped:
            raise InvalidInputError("These tables are already mapped.", details={"paths": mapped})
        created = []
        for table in tables:
            name = table.name if table.parent_path == "public" else table.path
            asset_id = self._assets.declare_stored_dataset(
                principal,
                name=name,
                description=(
                    f"Table {table.path} in {store.name}, harvested from {store.application_name}."
                ),
                domain_id=store.domain_id,
                retention_policy_id=data.retention_policy_id,
                data_category_id=data.data_category_id,
                owner_id=data.owner_id,
            )
            self._map(principal, store, snapshot, table, asset_id, existing=None)
            created.append((table.path, asset_id, name))
        return created

    def _map(
        self,
        principal: Principal,
        store: DataStoreRef,
        snapshot: HarvestSnapshot,
        table: PhysicalObject,
        asset_id: uuid.UUID,
        *,
        existing: PhysicalObjectMapping | None,
    ) -> None:
        columns = self._repository.columns_of(snapshot.id, table.path)
        elements = self._assets.element_ids_by_name(
            principal, asset_id, [(c.name, c.data_type or "unknown") for c in columns]
        )
        if existing is None:
            self._repository.add_mapping(
                PhysicalObjectMapping(
                    data_store_id=store.id,
                    path=table.path,
                    asset_id=asset_id,
                    mapped_by_id=principal.user_id,
                )
            )
        for column in columns:
            if self._repository.get_mapping(store.id, column.path) is None:
                self._repository.add_mapping(
                    PhysicalObjectMapping(
                        data_store_id=store.id,
                        path=column.path,
                        data_element_id=elements[column.name],
                        mapped_by_id=principal.user_id,
                    )
                )
        self._audit.record(
            actor=principal.actor,
            action="data_store.table_mapped",
            subject_type="data_store",
            subject_id=store.id,
            after={"path": table.path, "asset_id": asset_id, "columns": len(columns)},
        )

    def _require_snapshot(self, store: DataStoreRef) -> HarvestSnapshot:
        snapshot = self._repository.last_successful_snapshot(store.id)
        if snapshot is None:
            raise InvalidInputError("This data store has not been harvested yet.")
        return snapshot

    def _require_table(self, snapshot: HarvestSnapshot, path: str) -> PhysicalObject:
        table = self._repository.get_object(snapshot.id, path)
        if table is None or table.kind != ObjectKind.TABLE:
            raise NotFoundError(
                f"There is no table {path} in the last harvest.", details={"path": path}
            )
        return table

    def _view_of(self, data_store_id: uuid.UUID, obj: PhysicalObject) -> ObjectView:
        mapping = self._repository.get_mapping(data_store_id, obj.path)
        return self._views([ObjectRow(obj, mapping)])[0]


def describe(job_result: RunView | None) -> dict[str, Any]:
    """A harvest job's `result`: the outcome, small enough to read at /jobs/{id}."""
    if job_result is None:
        return {"status": "skipped", "reason": "The data store no longer exists."}
    snapshot = job_result.snapshot
    return {
        "status": snapshot.status,
        "snapshot_id": str(snapshot.id),
        "error": snapshot.error,
        **job_result.counts,
    }
