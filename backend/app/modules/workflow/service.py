"""Public interface of the workflow module: the Inbox, gathered from the modules that ask things
of a person."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.auth import Principal
from app.modules.inventory.service import AssetService
from app.modules.workflow.schemas import InboxItem, InboxItemKind


class InboxService:
    def __init__(self, session: Session) -> None:
        self._assets = AssetService(session)

    def items(self, principal: Principal) -> list[InboxItem]:
        """Everything waiting on the caller, most overdue first. v1: ownership confirmations."""
        now = datetime.now(UTC)
        items = [
            InboxItem(
                id=due.ownership_id,
                kind=InboxItemKind.OWNERSHIP_CONFIRMATION,
                title=f"Confirm you are the {_ROLE_LABEL[due.role]} of {due.asset_name}",
                subject_type="asset",
                subject_id=due.asset_id,
                subject_name=due.asset_name,
                requested_by=due.assigned_by,
                requested_at=due.assigned_at,
                due_at=due.due_at,
                overdue=due.due_at < now,
            )
            for due in self._assets.ownership_confirmations_due(principal)
        ]
        return sorted(items, key=lambda item: item.due_at)


_ROLE_LABEL = {"owner": "Data Owner", "steward": "Data Steward"}
