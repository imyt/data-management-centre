"""The current user (`/me`) and, with dev authentication only, the personas to act as."""

from fastapi import APIRouter

from app.core.auth import DevAuthOnly, PrincipalDep
from app.core.db import SessionDep
from app.core.schemas import ListMeta, error_responses
from app.modules.identity.schemas import UserPage, UserRead, UserResponse
from app.modules.identity.service import IdentityService, User

router = APIRouter(tags=["identity"])


def _read(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        roles=sorted(user.roles),
        domain_ids=None if user.domain_ids is None else sorted(user.domain_ids),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    operation_id="getMe",
    summary="Get the current user",
    responses=error_responses(401, 501),
)
def get_me(principal: PrincipalDep, session: SessionDep) -> UserResponse:
    return UserResponse(data=_read(IdentityService(session).get_user(principal.user_id)))


@router.get(
    "/dev/users",
    response_model=UserPage,
    operation_id="listDevUsers",
    summary="List the personas to act as (dev authentication only)",
    dependencies=[DevAuthOnly],
    responses=error_responses(404),
)
def list_dev_users(session: SessionDep) -> UserPage:
    users = IdentityService(session).list_active_users()
    return UserPage(data=[_read(u) for u in users], meta=ListMeta(total=len(users)))
