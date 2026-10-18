"""Inventory API: reference data, applications, environments and data stores."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.auth import PrincipalDep
from app.core.db import SessionDep
from app.core.schemas import ListMeta, error_responses
from app.modules.inventory.domain import LifecycleStatus
from app.modules.inventory.schemas import (
    ApplicationCreate,
    ApplicationDetail,
    ApplicationPage,
    ApplicationRead,
    ApplicationResponse,
    ApplicationUpdate,
    DataStoreCreate,
    DataStoreRead,
    DataStoreResponse,
    EnvironmentCreate,
    EnvironmentRead,
    EnvironmentResponse,
    ReferenceItemList,
    ReferenceItemRead,
    RetentionPolicyList,
    RetentionPolicyRead,
)
from app.modules.inventory.service import (
    InventoryService,
    application_actions,
    application_list_actions,
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
        limit=limit, cursor=cursor, query=q, domain_id=domain_id, lifecycle_status=lifecycle_status
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
    responses=error_responses(404, 422),
)
def get_application(
    application_id: uuid.UUID, service: Service, principal: PrincipalDep
) -> ApplicationResponse:
    application = service.get_application(application_id)
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
