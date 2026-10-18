"""Policy API: policies, the control library, rule versions and applied controls."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.core.auth import PrincipalDep
from app.core.db import SessionDep
from app.core.jobs.router import accepted
from app.core.jobs.schemas import JobResponse
from app.core.schemas import ListMeta, error_responses
from app.modules.inventory.service import SubjectType
from app.modules.policy.domain import AppliedControlStatus, ControlStatus
from app.modules.policy.schemas import (
    AppliedControlPage,
    AppliedControlResponse,
    ControlCreate,
    ControlPage,
    ControlResponse,
    ControlUpdate,
    PolicyCreate,
    PolicyList,
    PolicyResponse,
    PolicyUpdate,
    RetireControl,
    RuleVersionCreate,
    SelectorPreviewRequest,
    SelectorPreviewResponse,
    VocabularyResponse,
)
from app.modules.policy.service import (
    PolicyService,
    control_actions,
    control_list_actions,
    policy_actions,
    policy_list_actions,
)

router = APIRouter(tags=["policy"])


def get_service(session: SessionDep) -> PolicyService:
    return PolicyService(session)


Service = Annotated[PolicyService, Depends(get_service)]


@router.get(
    "/policy/vocabulary",
    response_model=VocabularyResponse,
    operation_id="getPolicyVocabulary",
    summary="List the rule types and the attributes selectors may use",
    responses=error_responses(401),
)
def get_vocabulary(service: Service, principal: PrincipalDep) -> VocabularyResponse:
    return VocabularyResponse(data=service.vocabulary())


# --- Policies (FR-P1)


@router.get(
    "/policies",
    response_model=PolicyList,
    operation_id="listPolicies",
    summary="List policies",
    responses=error_responses(401),
)
def list_policies(service: Service, principal: PrincipalDep) -> PolicyList:
    policies = service.list_policies()
    return PolicyList(
        data=policies,
        allowed_actions=policy_list_actions(principal),
        meta=ListMeta(total=len(policies)),
    )


@router.post(
    "/policies",
    response_model=PolicyResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createPolicy",
    summary="Add a policy",
    responses=error_responses(400, 401, 403, 409, 422),
)
def create_policy(body: PolicyCreate, service: Service, principal: PrincipalDep) -> PolicyResponse:
    return PolicyResponse(
        data=service.create_policy(principal, body), allowed_actions=policy_actions(principal)
    )


@router.get(
    "/policies/{policy_id}",
    response_model=PolicyResponse,
    operation_id="getPolicy",
    summary="Get a policy",
    responses=error_responses(401, 404, 422),
)
def get_policy(policy_id: uuid.UUID, service: Service, principal: PrincipalDep) -> PolicyResponse:
    return PolicyResponse(
        data=service.get_policy(policy_id), allowed_actions=policy_actions(principal)
    )


@router.patch(
    "/policies/{policy_id}",
    response_model=PolicyResponse,
    operation_id="updatePolicy",
    summary="Update a policy",
    responses=error_responses(400, 401, 403, 404, 422),
)
def update_policy(
    policy_id: uuid.UUID, body: PolicyUpdate, service: Service, principal: PrincipalDep
) -> PolicyResponse:
    return PolicyResponse(
        data=service.update_policy(principal, policy_id, body),
        allowed_actions=policy_actions(principal),
    )


# --- Controls (FR-P1, FR-P4)


@router.get(
    "/controls",
    response_model=ControlPage,
    operation_id="listControls",
    summary="List the control library",
    responses=error_responses(400, 401, 422),
)
def list_controls(
    service: Service,
    principal: PrincipalDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: Annotated[str | None, Query()] = None,
    q: Annotated[
        str | None, Query(max_length=200, description="Matches name or code, ignoring case.")
    ] = None,
    policy_id: Annotated[uuid.UUID | None, Query()] = None,
    rule_type: Annotated[str | None, Query()] = None,
    control_status: Annotated[ControlStatus | None, Query(alias="status")] = None,
) -> ControlPage:
    page = service.list_controls(
        limit=limit,
        cursor=cursor,
        policy_id=policy_id,
        rule_type_key=rule_type,
        status=control_status,
        query=q,
    )
    return ControlPage(
        data=page.items,
        allowed_actions=control_list_actions(principal),
        meta=ListMeta(next_cursor=page.next_cursor, total=page.total),
    )


@router.post(
    "/controls",
    response_model=ControlResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createControl",
    summary="Add a control to the library",
    responses=error_responses(400, 401, 403, 409, 422),
)
def create_control(
    body: ControlCreate, service: Service, principal: PrincipalDep
) -> ControlResponse:
    control = service.create_control(principal, body)
    return ControlResponse(data=control, allowed_actions=control_actions(principal, control))


@router.post(
    "/controls/preview-selector",
    response_model=SelectorPreviewResponse,
    operation_id="previewSelector",
    summary="Count the subjects a selector matches",
    responses=error_responses(400, 401, 403, 422),
)
def preview_selector(
    body: SelectorPreviewRequest, service: Service, principal: PrincipalDep
) -> SelectorPreviewResponse:
    return SelectorPreviewResponse(data=service.preview_selector(principal, body.selector))


@router.get(
    "/controls/{control_id}",
    response_model=ControlResponse,
    operation_id="getControl",
    summary="Get a control with its rule versions",
    responses=error_responses(401, 404, 422),
)
def get_control(
    control_id: uuid.UUID, service: Service, principal: PrincipalDep
) -> ControlResponse:
    control = service.get_control(control_id)
    return ControlResponse(data=control, allowed_actions=control_actions(principal, control))


@router.patch(
    "/controls/{control_id}",
    response_model=ControlResponse,
    operation_id="updateControl",
    summary="Update a control's description, owner or evidence requirement",
    responses=error_responses(400, 401, 403, 404, 409, 422),
)
def update_control(
    control_id: uuid.UUID, body: ControlUpdate, service: Service, principal: PrincipalDep
) -> ControlResponse:
    control = service.update_control(principal, control_id, body)
    return ControlResponse(data=control, allowed_actions=control_actions(principal, control))


@router.post(
    "/controls/{control_id}/rule-versions",
    response_model=ControlResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="publishRuleVersion",
    summary="Publish a new version of a control's rule",
    responses=error_responses(400, 401, 403, 404, 409, 422),
)
def publish_rule_version(
    control_id: uuid.UUID, body: RuleVersionCreate, service: Service, principal: PrincipalDep
) -> ControlResponse:
    control = service.publish_rule_version(
        principal,
        control_id,
        params=body.params,
        selector_body=body.selector,
        reason=body.reason,
    )
    return ControlResponse(data=control, allowed_actions=control_actions(principal, control))


@router.post(
    "/controls/{control_id}/retire",
    response_model=ControlResponse,
    operation_id="retireControl",
    summary="Retire a control",
    responses=error_responses(400, 401, 403, 404, 409, 422),
)
def retire_control(
    control_id: uuid.UUID, body: RetireControl, service: Service, principal: PrincipalDep
) -> ControlResponse:
    control = service.retire_control(principal, control_id, body.reason)
    return ControlResponse(data=control, allowed_actions=control_actions(principal, control))


@router.post(
    "/controls/{control_id}/recompute",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="recomputeControl",
    summary="Re-derive a control's applied controls",
    responses=error_responses(401, 403, 404, 409, 422),
)
def recompute_control(
    control_id: uuid.UUID, request: Request, service: Service, principal: PrincipalDep
) -> object:
    return accepted(request, service.recompute(principal, control_id))


# --- Applied controls (FR-P3, FR-A5)


@router.get(
    "/applied-controls",
    response_model=AppliedControlPage,
    operation_id="listAppliedControls",
    summary="List applied controls",
    responses=error_responses(400, 401, 422),
)
def list_applied_controls(
    service: Service,
    principal: PrincipalDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: Annotated[str | None, Query()] = None,
    control_id: Annotated[uuid.UUID | None, Query()] = None,
    subject_type: Annotated[SubjectType | None, Query()] = None,
    subject_id: Annotated[uuid.UUID | None, Query()] = None,
    rule_type: Annotated[str | None, Query()] = None,
    applied_status: Annotated[
        AppliedControlStatus | None,
        Query(alias="status", description="Defaults to active; retired ones are the history."),
    ] = AppliedControlStatus.ACTIVE,
) -> AppliedControlPage:
    page = service.list_applied_controls(
        principal,
        limit=limit,
        cursor=cursor,
        control_id=control_id,
        subject_type=subject_type,
        subject_id=subject_id,
        status=applied_status,
        rule_type_key=rule_type,
    )
    return AppliedControlPage(
        data=page.items, meta=ListMeta(next_cursor=page.next_cursor, total=page.total)
    )


@router.get(
    "/applied-controls/{applied_control_id}",
    response_model=AppliedControlResponse,
    operation_id="getAppliedControl",
    summary="Get an applied control and why it applies",
    responses=error_responses(401, 403, 404, 422),
)
def get_applied_control(
    applied_control_id: uuid.UUID, service: Service, principal: PrincipalDep
) -> AppliedControlResponse:
    return AppliedControlResponse(data=service.get_applied_control(principal, applied_control_id))
