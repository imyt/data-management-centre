"""API shapes for jobs."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.jobs.models import JobStatus
from app.core.schemas import Envelope


class JobRead(BaseModel):
    """A background job's state. Poll it while `status` is queued or running."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str = Field(description="What the job does, `<module>.<verb>`.")
    status: JobStatus
    progress: int | None = Field(description="Percent done (0 to 100), when the job reports it.")
    result: Any | None = Field(description="What the job produced, once it has succeeded.")
    error: str | None = Field(
        description="Why the last attempt failed. Set while a failed job waits for a retry."
    )
    attempts: int
    max_attempts: int
    created_at: datetime
    run_after: datetime = Field(description="Not started before this time (retries back off).")
    started_at: datetime | None
    finished_at: datetime | None


class JobResponse(Envelope[JobRead]):
    pass
