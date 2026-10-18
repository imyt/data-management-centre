"""Inbox API."""

from fastapi import APIRouter

from app.core.auth import PrincipalDep
from app.core.db import SessionDep
from app.core.schemas import ListMeta, error_responses
from app.modules.workflow.schemas import InboxPage
from app.modules.workflow.service import InboxService

router = APIRouter(tags=["workflow"])


@router.get(
    "/inbox",
    response_model=InboxPage,
    operation_id="listInbox",
    summary="List what is waiting on the current user",
    responses=error_responses(401),
)
def list_inbox(principal: PrincipalDep, session: SessionDep) -> InboxPage:
    items = InboxService(session).items(principal)
    return InboxPage(data=items, meta=ListMeta(total=len(items)))
