"""Evaluation's jobs, event handlers and schedule, registered by the worker."""

import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.jobs import JobContext, Registry
from app.core.outbox import Event
from app.modules.connectors.service import HARVEST_SUCCEEDED
from app.modules.evaluation.domain import Trigger
from app.modules.evaluation.service import (
    RUN_EVALUATION,
    SWEEP_EVALUATION,
    EvaluationService,
)
from app.modules.inventory.service import SUBJECT_CHANGED, SubjectType
from app.modules.policy.service import APPLIED_CONTROL_DERIVED


def run(context: JobContext) -> dict[str, Any]:
    """Evaluate applied controls (payload: `applied_control_ids`, `trigger`, `requested_by`)."""
    payload = context.payload
    summary = EvaluationService(context.session).run(
        [uuid.UUID(str(i)) for i in payload["applied_control_ids"]],
        Trigger(payload["trigger"]),
        requested_by=payload.get("requested_by"),
    )
    return {"run_id": str(summary.run_id), **summary.counts}


def sweep(context: JobContext) -> dict[str, int]:
    """The scheduled pass over every active applied control."""
    return {"queued": EvaluationService(context.session).sweep(job_id=context.job_id)}


def on_applied_control_derived(session: Session, event: Event) -> None:
    """A control now applies to a subject, or under a new rule version: evaluate it."""
    EvaluationService(session).enqueue_run(
        [uuid.UUID(str(event.payload["applied_control_id"]))],
        Trigger.EVENT,
        idempotency_key=f"event:{event.id}",
    )


def on_subject_changed(session: Session, event: Event) -> None:
    """A subject's declarations changed (say, its retention policy): evaluate its controls."""
    service = EvaluationService(session)
    service.enqueue_run(
        service.applied_control_ids_for_subject(
            SubjectType(event.payload["subject_type"]), uuid.UUID(str(event.payload["subject_id"]))
        ),
        Trigger.EVENT,
        idempotency_key=f"event:{event.id}",
    )


def on_harvest_succeeded(session: Session, event: Event) -> None:
    """A new snapshot of a data store: evaluate the assets stored in it."""
    service = EvaluationService(session)
    service.enqueue_run(
        service.applied_control_ids_for_store(uuid.UUID(str(event.payload["data_store_id"]))),
        Trigger.EVENT,
        idempotency_key=f"event:{event.id}",
    )


def register(registry: Registry, *, interval: timedelta) -> None:
    registry.job(RUN_EVALUATION, run)
    registry.job(SWEEP_EVALUATION, sweep)
    registry.on_event(
        APPLIED_CONTROL_DERIVED, on_applied_control_derived, name="evaluation.on_derived"
    )
    registry.on_event(SUBJECT_CHANGED, on_subject_changed, name="evaluation.on_subject_changed")
    registry.on_event(HARVEST_SUCCEEDED, on_harvest_succeeded, name="evaluation.on_harvest")
    registry.every(interval, SWEEP_EVALUATION)
