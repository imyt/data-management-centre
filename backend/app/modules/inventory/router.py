"""Inventory API: reference data, applications, environments and data stores."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.auth import Principal, PrincipalDep
from app.core.db import SessionDep
from app.core.schemas import ListMeta, error_responses
from app.modules.inventory.domain import (
    AssetType,
    LifecycleStatus,
    OwnershipRole,
    OwnershipStatus,
)
from app.modules.inventory.schemas import (
    ApplicationCreate,
    ApplicationDetail,
    ApplicationPage,
    ApplicationRead,
    ApplicationResponse,
    ApplicationUpdate,
    AssetCreate,
    AssetDetail,
    AssetPage,
    AssetRead,
    AssetResponse,
    AssetSummary,
    AssetUpdate,
    AssignOwnership,
    DataElementCreate,
    DataElementRead,
    DataElementResponse,
    DataElementUpdate,
    DataStoreCreate,
    DataStoreRead,
    DataStoreResponse,
    DisputeOwnership,
    EnvironmentCreate,
    EnvironmentRead,
    EnvironmentResponse,
    OwnershipRead,
    ReferenceItemList,
    ReferenceItemRead,
    RetentionPolicyList,
    RetentionPolicyRead,
    UserRef,
)
from app.modules.inventory.service import (
    AssetService,
    AssetView,
    InventoryService,
    application_actions,
    application_list_actions,
    asset_actions,
    asset_list_actions,
)

router = APIRouter(tags=["inventory"])


def get_service(session: SessionDep) -> InventoryService:
    return InventoryService(session)


Service = Annotated[InventoryService, Depends(get_service)]


# --- Reference data (FR-D2)


def _reference_list(service: InventoryService, kind: str) -> ReferenceItemList:
    items = service.list_reference(kind)
    return ReferenceItemList(
        data=[ReferenceItemRead.model_validate(i) for i in items],
        meta=ListMeta(total=len(items)),
    )


@router.get(
    "/reference/domains",
    response_model=ReferenceItemList,
    operation_id="listDomains",
    summary="List domains",
)
def list_domains(service: Service) -> ReferenceItemList:
    return _reference_list(service, "domain")


@router.get(
    "/reference/data-categories",
    response_model=ReferenceItemList,
    operation_id="listDataCategories",
    summary="List data categories",
)
def list_data_categories(service: Service) -> ReferenceItemList:
    return _reference_list(service, "data_category")


@router.get(
    "/reference/regions",
    response_model=ReferenceItemList,
    operation_id="listRegions",
    summary="List regions",
)
def list_regions(service: Service) -> ReferenceItemList:
    return _reference_list(service, "region")


@router.get(
    "/reference/retention-policies",
    response_model=RetentionPolicyList,
    operation_id="listRetentionPolicies",
    summary="List retention policies",
)
def list_retention_policies(service: Service) -> RetentionPolicyList:
    items = service.list_reference("retention_policy")
    return RetentionPolicyList(
        data=[RetentionPolicyRead.model_validate(i) for i in items],
        meta=ListMeta(total=len(items)),
    )


@router.get(
    "/reference/purposes",
    response_model=ReferenceItemList,
    operation_id="listPurposes",
    summary="List purposes",
)
def list_purposes(service: Service) -> ReferenceItemList:
    return _reference_list(service, "purpose")


# --- Applications (FR-K1, FR-K2)


@router.get(
    "/applications",
    response_model=ApplicationPage,
    operation_id="listApplications",
    summary="List applications",
    responses=error_responses(400, 422),
)
def list_applications(
    service: Service,
    principal: PrincipalDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: Annotated[str | None, Query()] = None,
    q: Annotated[
        str | None, Query(max_length=200, description="Matches name or code, ignoring case.")
    ] = None,
    domain_id: Annotated[uuid.UUID | None, Query()] = None,
    lifecycle_status: Annotated[LifecycleStatus | None, Query()] = None,
) -> ApplicationPage:
    page = service.list_applications(
        principal,
        limit=limit,
        cursor=cursor,
        query=q,
        domain_id=domain_id,
        lifecycle_status=lifecycle_status,
    )
    return ApplicationPage(
        data=[ApplicationRead.model_validate(item) for item in page.items],
        allowed_actions=application_list_actions(principal),
        meta=ListMeta(next_cursor=page.next_cursor, total=page.total),
    )


@router.post(
    "/applications",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createApplication",
    summary="Register an application",
    responses=error_responses(400, 403, 409, 422),
)
def create_application(
    body: ApplicationCreate, service: Service, principal: PrincipalDep
) -> ApplicationResponse:
    application = service.create_application(principal, body)
    return ApplicationResponse(
        data=ApplicationDetail.model_validate(application),
        allowed_actions=application_actions(principal, application),
    )


@router.get(
    "/applications/{application_id}",
    response_model=ApplicationResponse,
    operation_id="getApplication",
    summary="Get an application with its environments and data stores",
    responses=error_responses(403, 404, 422),
)
def get_application(
    application_id: uuid.UUID, service: Service, principal: PrincipalDep
) -> ApplicationResponse:
    application = service.get_application(principal, application_id)
    return ApplicationResponse(
        data=ApplicationDetail.model_validate(application),
        allowed_actions=application_actions(principal, application),
    )


@router.patch(
    "/applications/{application_id}",
    response_model=ApplicationResponse,
    operation_id="updateApplication",
    summary="Update an application",
    responses=error_responses(400, 403, 404, 409, 422),
)
def update_application(
    application_id: uuid.UUID, body: ApplicationUpdate, service: Service, principal: PrincipalDep
) -> ApplicationResponse:
    application = service.update_application(principal, application_id, body)
    return ApplicationResponse(
        data=ApplicationDetail.model_validate(application),
        allowed_actions=application_actions(principal, application),
    )


@router.post(
    "/applications/{application_id}/environments",
    response_model=EnvironmentResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createEnvironment",
    summary="Add an environment to an application",
    responses=error_responses(400, 403, 404, 422),
)
def create_environment(
    application_id: uuid.UUID, body: EnvironmentCreate, service: Service, principal: PrincipalDep
) -> EnvironmentResponse:
    environment = service.add_environment(principal, application_id, body)
    return EnvironmentResponse(data=EnvironmentRead.model_validate(environment))


@router.post(
    "/environments/{environment_id}/data-stores",
    response_model=DataStoreResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createDataStore",
    summary="Add a data store to an environment",
    responses=error_responses(400, 403, 404, 422),
)
def create_data_store(
    environment_id: uuid.UUID, body: DataStoreCreate, service: Service, principal: PrincipalDep
) -> DataStoreResponse:
    store = service.add_data_store(principal, environment_id, body)
    return DataStoreResponse(data=DataStoreRead.model_validate(store))


# --- Assets, data elements and ownership (FR-K5, FR-K6, FR-K10)


def get_asset_service(session: SessionDep) -> AssetService:
    return AssetService(session)


Assets = Annotated[AssetService, Depends(get_asset_service)]


def _user_ref(view: AssetView, user_id: uuid.UUID) -> UserRef:
    user = view.users.get(user_id)
    return UserRef(id=user_id, display_name=user.display_name if user else "Unknown user")


def _ownership(view: AssetView, role: OwnershipRole) -> OwnershipRead | None:
    row = next((o for o in view.asset.ownerships if o.role == role), None)
    if row is None:
        return None
    return OwnershipRead(
        role=role,
        user=_user_ref(view, row.user_id),
        status=OwnershipStatus(row.status),
        assigned_by=_user_ref(view, row.assigned_by_id),
        assigned_at=row.assigned_at,
        decided_at=row.decided_at,
        reason=row.reason,
    )


def _summary(view: AssetView) -> AssetSummary:
    return AssetSummary(
        **AssetRead.model_validate(view.asset).model_dump(),
        owner=_ownership(view, OwnershipRole.OWNER),
        steward=_ownership(view, OwnershipRole.STEWARD),
    )


def _asset_response(view: AssetView, principal: Principal) -> AssetResponse:
    return AssetResponse(
        data=AssetDetail(
            **_summary(view).model_dump(),
            data_elements=[DataElementRead.model_validate(e) for e in view.asset.data_elements],
        ),
        allowed_actions=asset_actions(principal, view.asset),
    )


@router.get(
    "/assets",
    response_model=AssetPage,
    operation_id="listAssets",
    summary="List assets",
    responses=error_responses(400, 422),
)
def list_assets(
    service: Assets,
    principal: PrincipalDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: Annotated[str | None, Query()] = None,
    q: Annotated[
        str | None, Query(max_length=200, description="Matches name, ignoring case.")
    ] = None,
    domain_id: Annotated[uuid.UUID | None, Query()] = None,
    asset_type: Annotated[AssetType | None, Query(alias="type")] = None,
) -> AssetPage:
    page = service.list_assets(
        principal, limit=limit, cursor=cursor, query=q, domain_id=domain_id, asset_type=asset_type
    )
    return AssetPage(
        data=[_summary(view) for view in page.items],
        allowed_actions=asset_list_actions(principal),
        meta=ListMeta(next_cursor=page.next_cursor, total=page.total),
    )


@router.post(
    "/assets",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createAsset",
    summary="Declare an asset",
    responses=error_responses(400, 403, 422),
)
def create_asset(body: AssetCreate, service: Assets, principal: PrincipalDep) -> AssetResponse:
    return _asset_response(service.create_asset(principal, body), principal)


@router.get(
    "/assets/{asset_id}",
    response_model=AssetResponse,
    operation_id="getAsset",
    summary="Get an asset with its data elements and ownership",
    responses=error_responses(403, 404, 422),
)
def get_asset(asset_id: uuid.UUID, service: Assets, principal: PrincipalDep) -> AssetResponse:
    return _asset_response(service.get_asset(principal, asset_id), principal)


@router.patch(
    "/assets/{asset_id}",
    response_model=AssetResponse,
    operation_id="updateAsset",
    summary="Update an asset's declaration",
    responses=error_responses(400, 403, 404, 422),
)
def update_asset(
    asset_id: uuid.UUID, body: AssetUpdate, service: Assets, principal: PrincipalDep
) -> AssetResponse:
    return _asset_response(service.update_asset(principal, asset_id, body), principal)


@router.post(
    "/assets/{asset_id}/data-elements",
    response_model=DataElementResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createDataElement",
    summary="Add a data element to an asset",
    responses=error_responses(400, 403, 404, 409, 422),
)
def create_data_element(
    asset_id: uuid.UUID, body: DataElementCreate, service: Assets, principal: PrincipalDep
) -> DataElementResponse:
    element = service.add_data_element(principal, asset_id, body)
    return DataElementResponse(data=DataElementRead.model_validate(element))


@router.patch(
    "/data-elements/{element_id}",
    response_model=DataElementResponse,
    operation_id="updateDataElement",
    summary="Update a data element, including its PII and CDE flags",
    responses=error_responses(400, 403, 404, 409, 422),
)
def update_data_element(
    element_id: uuid.UUID, body: DataElementUpdate, service: Assets, principal: PrincipalDep
) -> DataElementResponse:
    element = service.update_data_element(principal, element_id, body)
    return DataElementResponse(data=DataElementRead.model_validate(element))


@router.put(
    "/assets/{asset_id}/ownership/{role}",
    response_model=AssetResponse,
    operation_id="assignOwnership",
    summary="Assign or reassign the Data Owner or Data Steward",
    responses=error_responses(400, 403, 404, 422),
)
def assign_ownership(
    asset_id: uuid.UUID,
    role: OwnershipRole,
    body: AssignOwnership,
    service: Assets,
    principal: PrincipalDep,
) -> AssetResponse:
    view = service.assign(principal, asset_id, role, body.user_id, body.reason)
    return _asset_response(view, principal)


@router.post(
    "/assets/{asset_id}/ownership/{role}/confirm",
    response_model=AssetResponse,
    operation_id="confirmOwnership",
    summary="Confirm an ownership assigned to you",
    responses=error_responses(403, 404, 409, 422),
)
def confirm_ownership(
    asset_id: uuid.UUID, role: OwnershipRole, service: Assets, principal: PrincipalDep
) -> AssetResponse:
    return _asset_response(service.confirm(principal, asset_id, role), principal)


@router.post(
    "/assets/{asset_id}/ownership/{role}/dispute",
    response_model=AssetResponse,
    operation_id="disputeOwnership",
    summary="Dispute an ownership assigned to you, with a reason",
    responses=error_responses(400, 403, 404, 409, 422),
)
def dispute_ownership(
    asset_id: uuid.UUID,
    role: OwnershipRole,
    body: DisputeOwnership,
    service: Assets,
    principal: PrincipalDep,
) -> AssetResponse:
    return _asset_response(service.dispute(principal, asset_id, role, body.reason), principal)
