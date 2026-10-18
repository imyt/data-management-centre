"""Read models and response envelopes for the Inbox."""

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.core.schemas import ListEnvelope


class InboxItemKind(StrEnum):
    OWNERSHIP_CONFIRMATION = "ownership_confirmation"


class InboxItem(BaseModel):
    id: uuid.UUID
    kind: InboxItemKind
    title: str = Field(description="What is being asked, in a sentence.")
    subject_type: str = Field(description="What it is about, e.g. `asset`.")
    subject_id: uuid.UUID
    subject_name: str
    requested_by: str | None
    requested_at: datetime
    due_at: datetime
    overdue: bool


class InboxPage(ListEnvelope[InboxItem]):
    pass
