"""What the worker knows how to do: job handlers by kind, event handlers by type, schedules.

Core declares the registry; the composition root (`app/worker.py`) fills it with each module's
handlers, so core never imports modules.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.outbox import Event


class PermanentJobError(Exception):
    """Raise from a job handler when retrying cannot help: the job fails without retries."""


@dataclass
class JobContext:
    """What a job handler gets. Writes through `session` commit only if the job succeeds."""

    job_id: uuid.UUID
    kind: str
    payload: dict[str, Any]
    attempt: int
    session: Session
    _report_progress: Callable[[int], None] = field(repr=False)

    def set_progress(self, percent: int) -> None:
        """Record progress (0 to 100) at once, outside the job's transaction, for GET /jobs/{id}."""
        if not 0 <= percent <= 100:
            raise ValueError("progress is a percentage from 0 to 100")
        self._report_progress(percent)


JobHandler = Callable[[JobContext], Any]
"""Runs one job. The return value (plain JSON) is stored as the job's `result`."""

EventHandler = Callable[[Session, Event], None]
"""Reacts to one event, writing through the session it is given."""


@dataclass(frozen=True)
class Schedule:
    """Enqueue `kind` once per `interval` (slots aligned to the epoch), by whichever worker
    sees the slot first."""

    name: str
    interval: timedelta
    kind: str
    payload: dict[str, Any]


class Registry:
    def __init__(self) -> None:
        self.jobs: dict[str, JobHandler] = {}
        self.events: dict[str, dict[str, EventHandler]] = {}
        self.schedules: dict[str, Schedule] = {}

    def job(self, kind: str, handler: JobHandler) -> None:
        if kind in self.jobs:
            raise ValueError(f"A handler for job kind {kind!r} is already registered")
        self.jobs[kind] = handler

    def on_event(self, type: str, handler: EventHandler, *, name: str | None = None) -> None:
        """Register a handler for an event type. `name` (default: its import path) keys dedupe,
        so renaming a handler makes it see past events again; pass the old name to avoid that."""
        name = name or f"{handler.__module__}.{handler.__qualname__}"
        handlers = self.events.setdefault(type, {})
        if name in handlers:
            raise ValueError(f"Handler {name!r} is already registered for {type!r}")
        handlers[name] = handler

    def every(
        self,
        interval: timedelta,
        kind: str,
        payload: dict[str, Any] | None = None,
        *,
        name: str | None = None,
    ) -> None:
        if interval < timedelta(seconds=1):
            raise ValueError("A schedule's interval must be at least one second")
        name = name or kind
        if name in self.schedules:
            raise ValueError(f"A schedule named {name!r} is already registered")
        self.schedules[name] = Schedule(name, interval, kind, payload or {})
