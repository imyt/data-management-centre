"""The job queue's operations. `enqueue` is for callers; the rest are the worker's (ADR 0009).

A job is `queued` until a worker claims it (`SELECT … FOR UPDATE SKIP LOCKED`, so two workers
never claim the same job) and marks it `running` under a lease: `locked_by` and `locked_at`,
which the worker refreshes while the handler runs. Every write that finishes a job checks the
lease is still the worker's, so a job recovered from a stalled worker cannot be finished twice.
"""

import uuid
from collections.abc import Collection
from datetime import datetime, timedelta
from typing import Any, cast

from pydantic_core import to_jsonable_python
from sqlalchemy import CursorResult, Result, case, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.jobs.models import Job, JobStatus

RETRY_BASE = timedelta(seconds=10)
RETRY_CAP = timedelta(hours=1)
LOST_WORKER_ERROR = "The worker running this job stopped responding."


def enqueue(
    session: Session,
    kind: str,
    payload: dict[str, Any] | None = None,
    *,
    max_attempts: int = 5,
    run_after: datetime | None = None,
    created_by: str | None = None,
    idempotency_key: str | None = None,
) -> Job:
    """Queue a job in the caller's transaction, so it exists only if the caller commits.

    With an `idempotency_key`, a second enqueue of the same kind and key returns the first job
    (whatever its payload) instead of queueing another.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    values: dict[str, Any] = {
        "kind": kind,
        "payload": to_jsonable_python(payload or {}),
        "max_attempts": max_attempts,
        "created_by": created_by,
        "idempotency_key": idempotency_key,
    }
    if run_after is not None:
        values["run_after"] = run_after
    if idempotency_key is None:
        job = Job(**values)
        session.add(job)
        session.flush()
        return job
    inserted = session.scalars(
        insert(Job)
        .values(**values)
        .on_conflict_do_nothing(index_elements=[Job.kind, Job.idempotency_key])
        .returning(Job)
    ).one_or_none()
    if inserted is not None:
        return inserted
    return session.scalars(
        select(Job).where(Job.kind == kind, Job.idempotency_key == idempotency_key)
    ).one()


def get_job(session: Session, job_id: uuid.UUID) -> Job | None:
    return session.get(Job, job_id)


def cancel(session: Session, job_id: uuid.UUID) -> bool:
    """Cancel a job that has not started. Running jobs cannot be cancelled yet."""
    result = session.execute(
        update(Job)
        .where(Job.id == job_id, Job.status == JobStatus.QUEUED)
        .values(status=JobStatus.CANCELLED, finished_at=func.now())
        .execution_options(synchronize_session=False)
    )
    return _affected(result) == 1


def retry_delay(attempt: int) -> timedelta:
    """Exponential backoff after the given (1-based) failed attempt: 10s, 20s, 40s … up to 1h."""
    delay: timedelta = RETRY_BASE * 2 ** (attempt - 1)
    return min(delay, RETRY_CAP)


def claim(session: Session, worker_id: str, kinds: Collection[str]) -> Job | None:
    """Take the oldest due job of the given kinds, skipping jobs other workers are claiming."""
    if not kinds:
        return None
    next_due = (
        select(Job.id)
        .where(Job.status == JobStatus.QUEUED, Job.run_after <= func.now(), Job.kind.in_(kinds))
        .order_by(Job.run_after, Job.id)
        .limit(1)
        .with_for_update(skip_locked=True)
        .scalar_subquery()
    )
    return session.scalars(
        update(Job)
        .where(Job.id == next_due)
        .values(
            status=JobStatus.RUNNING,
            locked_by=worker_id,
            locked_at=func.now(),
            attempts=Job.attempts + 1,
            started_at=func.coalesce(Job.started_at, func.now()),
        )
        .returning(Job)
        .execution_options(synchronize_session=False, populate_existing=True)
    ).one_or_none()


def _leased(session: Session, job_id: uuid.UUID, worker_id: str) -> Job | None:
    """The job, locked, if it is still running under this worker's lease."""
    return session.scalars(
        select(Job)
        .where(Job.id == job_id, Job.status == JobStatus.RUNNING, Job.locked_by == worker_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one_or_none()


def succeed(session: Session, job_id: uuid.UUID, worker_id: str, result: Any) -> bool:
    """Mark the job succeeded. False if the lease was lost (the caller must roll back)."""
    job = _leased(session, job_id, worker_id)
    if job is None:
        return False
    job.status = JobStatus.SUCCEEDED
    job.result = to_jsonable_python(result)
    job.progress = 100
    job.error = None
    job.locked_by = job.locked_at = None
    job.finished_at = func.now()
    session.flush()
    return True


def fail(
    session: Session, job_id: uuid.UUID, worker_id: str, error: str, *, permanent: bool = False
) -> JobStatus | None:
    """Record a failed attempt: requeue with backoff, or fail for good when out of attempts.

    Returns the job's new status, or None if the lease was lost.
    """
    job = _leased(session, job_id, worker_id)
    if job is None:
        return None
    if permanent or job.attempts >= job.max_attempts:
        status = JobStatus.FAILED
        job.finished_at = func.now()
    else:
        status = JobStatus.QUEUED
        job.run_after = func.now() + retry_delay(job.attempts)
    job.status = status
    job.error = error
    job.locked_by = job.locked_at = None
    session.flush()
    return status


def refresh_lease(session: Session, job_id: uuid.UUID, worker_id: str) -> bool:
    result = session.execute(
        update(Job)
        .where(Job.id == job_id, Job.status == JobStatus.RUNNING, Job.locked_by == worker_id)
        .values(locked_at=func.now())
        .execution_options(synchronize_session=False)
    )
    return _affected(result) == 1


def set_progress(session: Session, job_id: uuid.UUID, worker_id: str, percent: int) -> bool:
    result = session.execute(
        update(Job)
        .where(Job.id == job_id, Job.status == JobStatus.RUNNING, Job.locked_by == worker_id)
        .values(progress=percent, locked_at=func.now())
        .execution_options(synchronize_session=False)
    )
    return _affected(result) == 1


def recover_stalled(session: Session, lease: timedelta) -> list[uuid.UUID]:
    """Requeue running jobs whose lease has not been refreshed within `lease` (their worker died),
    or fail them if they have used all their attempts. Returns the recovered job ids."""
    out_of_attempts = Job.attempts >= Job.max_attempts
    return list(
        session.scalars(
            update(Job)
            .where(Job.status == JobStatus.RUNNING, Job.locked_at < func.now() - lease)
            .values(
                status=case(
                    (out_of_attempts, JobStatus.FAILED.value), else_=JobStatus.QUEUED.value
                ),
                finished_at=case((out_of_attempts, func.now()), else_=None),
                run_after=func.now(),
                locked_by=None,
                locked_at=None,
                error=LOST_WORKER_ERROR,
            )
            .returning(Job.id)
            .execution_options(synchronize_session=False)
        )
    )


def _affected(result: Result[Any]) -> int:
    """Rows matched by an UPDATE; `Result` doesn't declare `rowcount`, `CursorResult` does."""
    return cast("CursorResult[Any]", result).rowcount
