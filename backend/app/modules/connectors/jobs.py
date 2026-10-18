"""Connectors' jobs, event handlers and schedule, registered by the worker."""

import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.jobs import JobContext, Registry
from app.core.outbox import Event
from app.modules.connectors.service import HARVEST, ConnectorsService, describe
from app.modules.inventory.service import DATA_STORE_CREATED

HARVEST_ALL = "connectors.harvest_all"


def harvest(context: JobContext) -> dict[str, Any]:
    """Harvest one data store (payload: `data_store_id`, `requested_by`)."""
    outcome = ConnectorsService(context.session).run_harvest(
        uuid.UUID(str(context.payload["data_store_id"])),
        requested_by=context.payload.get("requested_by"),
    )
    return describe(outcome)


def harvest_all(context: JobContext) -> dict[str, int]:
    """The scheduled sweep: queue a harvest for every data store."""
    service = ConnectorsService(context.session)
    ids = service.data_store_ids()
    for store_id in ids:
        # Keyed by this sweep, so a retried sweep queues each store once.
        service.enqueue_harvest(store_id, idempotency_key=f"sweep:{context.job_id}:{store_id}")
    return {"queued": len(ids)}


def on_data_store_created(session: Session, event: Event) -> None:
    """A newly registered data store gets its first harvest without waiting for the schedule."""
    ConnectorsService(session).enqueue_harvest(
        uuid.UUID(str(event.payload["data_store_id"])), idempotency_key=f"event:{event.id}"
    )


def register(registry: Registry, *, interval: timedelta) -> None:
    registry.job(HARVEST, harvest)
    registry.job(HARVEST_ALL, harvest_all)
    registry.on_event(DATA_STORE_CREATED, on_data_store_created, name="connectors.first_harvest")
    registry.every(interval, HARVEST_ALL)
