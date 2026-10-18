"""Read models and response envelopes for the identity API."""

import uuid

from pydantic import BaseModel, Field

from app.core.auth import Role
from app.core.schemas import Envelope, ListEnvelope


class UserRead(BaseModel):
    id: uuid.UUID
    username: str = Field(description="Sign-in name; in dev mode, the X-DMC-Dev-User value.")
    display_name: str
    roles: list[Role]
    domain_ids: list[uuid.UUID] | None = Field(
        description="Domains the user is scoped to; null means every domain."
    )


class UserResponse(Envelope[UserRead]):
    pass


class UserPage(ListEnvelope[UserRead]):
    pass
