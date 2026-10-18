"""The platform's own recurring job: purge rows that have outlived their use."""

from datetime import timedelta
from typing import Any

from sqlalchemy import delete, func

from app.core.idempotency import IdempotencyKey
from app.core.jobs.models import WorkerHeartbeat
from app.core.jobs.registry import JobContext, Registry
from app.core.outbox import OutboxEvent

PURGE = "platform.purge"
KEEP_PROCESSED_EVENTS = timedelta(days=7)
KEEP_STOPPED_WORKERS = timedelta(days=7)


def purge(context: JobContext) -> dict[str, Any]:
    session = context.session
    counts = {}
    for name, statement in {
        "idempotency_keys": delete(IdempotencyKey).where(IdempotencyKey.expires_at <= func.now()),
        "outbox_events": delete(OutboxEvent).where(
            OutboxEvent.processed_at < func.now() - KEEP_PROCESSED_EVENTS
        ),
        "worker_heartbeats": delete(WorkerHeartbeat).where(
            WorkerHeartbeat.beat_at < func.now() - KEEP_STOPPED_WORKERS
        ),
    }.items():
        counts[name] = session.execute(statement).rowcount  # type: ignore[attr-defined]
    return counts


def register_platform_jobs(registry: Registry) -> None:
    registry.job(PURGE, purge)
    registry.every(timedelta(hours=1), PURGE)
