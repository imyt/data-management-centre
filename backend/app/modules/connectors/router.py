"""Connectors API: harvest a data store, see what it found, map the objects to assets."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import JSONResponse

from app.core.auth import PrincipalDep
from app.core.db import SessionDep
from app.core.jobs.router import accepted
from app.core.jobs.schemas import JobResponse
from app.core.schemas import ListMeta, error_responses
from app.modules.connectors.domain import ObjectKind
from app.modules.connectors.schemas import (
    CreateAssets,
    CreatedAsset,
    CreatedAssetList,
    HarvestStatusRead,
    HarvestStatusResponse,
    MapTable,
    ObjectCounts,
    ObjectMappingRead,
    PhysicalObjectPage,
    PhysicalObjectRead,
    PhysicalObjectResponse,
    SnapshotRead,
)
from app.modules.connectors.service import (
    ConnectorsService,
    ObjectView,
    RunView,
    StatusView,
    data_store_actions,
)

router = APIRouter(tags=["connectors"])


def get_service(session: SessionDep) -> ConnectorsService:
    return ConnectorsService(session)


Service = Annotated[ConnectorsService, Depends(get_service)]


def _snapshot(run: RunView) -> SnapshotRead:
    return SnapshotRead(
        id=run.snapshot.id,
        status=run.snapshot.status,
        taken_at=run.snapshot.taken_at,
        error=run.snapshot.error,
        schemas=run.counts.get("schema", 0),
        tables=run.counts.get("table", 0),
        columns=run.counts.get("column", 0),
    )


def _status(view: StatusView) -> HarvestStatusRead:
    runs = [_snapshot(run) for run in view.runs]
    objects = view.objects
    return HarvestStatusRead(
        data_store_id=view.data_store_id,
        last_run=runs[0] if runs else None,
        objects=ObjectCounts(
            schemas=objects.get("schema", 0),
            tables=objects.get("table", 0),
            columns=objects.get("column", 0),
            unmapped_tables=objects["unmapped_table"],
            unmapped_columns=objects["unmapped_column"],
        )
        if objects is not None
        else None,
        recent_runs=runs,
    )


def _object(view: ObjectView) -> PhysicalObjectRead:
    obj, mapping = view.row.object, view.row.mapping
    return PhysicalObjectRead(
        id=obj.id,
        kind=ObjectKind(obj.kind),
        path=obj.path,
        name=obj.name,
        parent_path=obj.parent_path,
        data_type=obj.data_type,
        row_count=obj.row_count,
        mapping=ObjectMappingRead(
            asset_id=mapping.asset_id,
            asset_name=view.asset_name,
            data_element_id=mapping.data_element_id,
        )
        if mapping
        else None,
    )


@router.get(
    "/data-stores/{data_store_id}/harvest",
    response_model=HarvestStatusResponse,
    operation_id="getHarvestStatus",
    summary="Get a data store's harvest status, recent runs and unmapped counts",
    responses=error_responses(403, 404, 422),
)
def get_harvest_status(
    data_store_id: uuid.UUID, service: Service, principal: PrincipalDep
) -> HarvestStatusResponse:
    view = service.status(principal, data_store_id)
    return HarvestStatusResponse(
        data=_status(view), allowed_actions=data_store_actions(principal, view.domain_id)
    )


@router.post(
    "/data-stores/{data_store_id}/harvest",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="runHarvest",
    summary="Harvest a data store now",
    description="Queues a harvest and returns the job; poll `/jobs/{id}` or the harvest status.",
    responses=error_responses(403, 404, 422),
)
def run_harvest(
    data_store_id: uuid.UUID, request: Request, service: Service, principal: PrincipalDep
) -> JSONResponse:
    return accepted(request, service.request_harvest(principal, data_store_id))


@router.get(
    "/data-stores/{data_store_id}/objects",
    response_model=PhysicalObjectPage,
    operation_id="listPhysicalObjects",
    summary="List the schemas, tables and columns the last harvest found",
    responses=error_responses(403, 404, 422),
)
def list_objects(
    data_store_id: uuid.UUID,
    service: Service,
    principal: PrincipalDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    cursor: str | None = None,
    kind: ObjectKind | None = None,
    parent_path: Annotated[str | None, Query(description="Only the children of this path.")] = None,
    mapped: Annotated[
        bool | None,
        Query(description="false: only tables and columns with no asset or element yet."),
    ] = None,
) -> PhysicalObjectPage:
    page = service.list_objects(
        principal,
        data_store_id,
        limit=limit,
        cursor=cursor,
        kind=kind,
        parent_path=parent_path,
        mapped=mapped,
    )
    return PhysicalObjectPage(
        data=[_object(v) for v in page.items],
        meta=ListMeta(next_cursor=page.next_cursor, total=page.total),
    )


@router.post(
    "/data-stores/{data_store_id}/mappings",
    response_model=PhysicalObjectResponse,
    operation_id="mapTable",
    summary="Map a table to an existing asset",
    description="Matches the table's columns to the asset's data elements by name and adds the "
    "elements it lacks.",
    responses=error_responses(400, 403, 404, 409, 422),
)
def map_table(
    data_store_id: uuid.UUID, body: MapTable, service: Service, principal: PrincipalDep
) -> PhysicalObjectResponse:
    return PhysicalObjectResponse(data=_object(service.map_table(principal, data_store_id, body)))


@router.post(
    "/data-stores/{data_store_id}/mappings/assets",
    response_model=CreatedAssetList,
    status_code=status.HTTP_201_CREATED,
    operation_id="createAssetsFromTables",
    summary="Declare an asset for each unmapped table and map it",
    description="Each asset is a stored dataset in the application's domain with a data element "
    "per column. A given Data Owner is asked to confirm.",
    responses=error_responses(400, 403, 404, 422),
)
def create_assets(
    data_store_id: uuid.UUID, body: CreateAssets, service: Service, principal: PrincipalDep
) -> CreatedAssetList:
    created = service.create_assets(principal, data_store_id, body)
    return CreatedAssetList(
        data=[CreatedAsset(path=p, asset_id=i, asset_name=n) for p, i, n in created]
    )
