"""Policy's jobs and event handlers, registered by the worker."""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.jobs import JobContext, Registry
from app.core.outbox import Event
from app.modules.inventory.service import SUBJECT_CHANGED, SubjectType
from app.modules.policy.derivation import DerivationSummary
from app.modules.policy.service import RECOMPUTE_CONTROL, PolicyService


def _describe(summary: DerivationSummary) -> dict[str, Any]:
    return {"created": summary.created, "updated": summary.updated, "retired": summary.retired}


def recompute_control(context: JobContext) -> dict[str, Any]:
    """Re-derive one control's applied controls (payload: `control_id`)."""
    summary = PolicyService(context.session).recompute_control(
        uuid.UUID(str(context.payload["control_id"]))
    )
    return _describe(summary)


def on_subject_changed(session: Session, event: Event) -> None:
    """A subject's attributes may have changed: re-derive its applied controls."""
    PolicyService(session).derive_subject(
        SubjectType(event.payload["subject_type"]), uuid.UUID(str(event.payload["subject_id"]))
    )


def register(registry: Registry) -> None:
    registry.job(RECOMPUTE_CONTROL, recompute_control)
    registry.on_event(SUBJECT_CHANGED, on_subject_changed, name="policy.derive_applied_controls")
