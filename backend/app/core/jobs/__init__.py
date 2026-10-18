"""Background work in Postgres: the job queue, the worker and its scheduler (ADR 0009).

Modules use `enqueue` (in their own transaction) and, in routes, `accepted`; they declare
handlers in a `register(registry)` function that `app/worker.py` calls.
"""

from app.core.jobs.models import Job, JobStatus
from app.core.jobs.queue import enqueue
from app.core.jobs.registry import JobContext, PermanentJobError, Registry

__all__ = ["Job", "JobContext", "JobStatus", "PermanentJobError", "Registry", "enqueue"]
