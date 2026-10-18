"""The worker loop: relay outbox events, run jobs, enqueue scheduled jobs (ADR 0009).

`app/worker.py` builds the registry and runs `Worker.run` as `uv run dmc-worker`. Any number of
workers can run against one database: claims skip locked rows, deliveries are deduplicated and
schedules are keyed by time slot.
"""

import logging
import os
import socket
import threading
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta
from functools import partial
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.db import Database
from app.core.jobs import queue
from app.core.jobs.models import JobStatus, WorkerHeartbeat
from app.core.jobs.registry import JobContext, PermanentJobError, Registry
from app.core.logs import log_context
from app.core.outbox import Event, OutboxDelivery, OutboxEvent

logger = logging.getLogger(__name__)

HEARTBEAT_EVERY = 10.0
ERROR_LIMIT = 2000


class _LeaseLost(Exception):
    pass


def _describe(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"[:ERROR_LIMIT]


def default_worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"


class Worker:
    def __init__(
        self,
        database: Database,
        registry: Registry,
        *,
        worker_id: str | None = None,
        lease: timedelta = timedelta(minutes=5),
        poll_interval: float = 1.0,
        event_batch: int = 50,
        keep_leases: bool = True,
    ) -> None:
        """`keep_leases` refreshes a running job's lease from a second thread; tests that bind
        the database to one connection turn it off."""
        self.database = database
        self.registry = registry
        self.worker_id = worker_id or default_worker_id()
        self.lease = lease
        self.poll_interval = poll_interval
        self.event_batch = event_batch
        self.keep_leases = keep_leases
        self._last_slot: dict[str, int] = {}
        self._next_recovery = 0.0
        self._last_beat = 0.0

    # The loop

    def run(self, stop: threading.Event) -> None:
        """Work until `stop` is set. The current job or event batch finishes first."""
        with log_context(worker_id=self.worker_id):
            logger.info("Worker %s started", self.worker_id)
            self.beat()
            try:
                while not stop.is_set():
                    if not self.run_once():
                        stop.wait(self.poll_interval)
                    if time.monotonic() - self._last_beat >= HEARTBEAT_EVERY:
                        self.beat()
            finally:
                self.beat(stopped=True)
                logger.info("Worker %s stopped", self.worker_id)

    def run_once(self) -> bool:
        """One pass over everything. True if it did something, so the loop goes again at once."""
        if time.monotonic() >= self._next_recovery:
            self.recover_stalled_jobs()
            self._next_recovery = time.monotonic() + self.lease.total_seconds() / 2
        self.enqueue_due_schedules()
        relayed = self.relay_events()
        ran = self.run_next_job()
        return relayed > 0 or ran

    # Heartbeat

    def beat(self, *, stopped: bool = False) -> None:
        with self.database.transaction() as session:
            self._beat(session, stopped=stopped)

    def _beat(self, session: Session, *, stopped: bool = False) -> None:
        stopped_at: Any = func.now() if stopped else None
        session.execute(
            insert(WorkerHeartbeat)
            .values(worker_id=self.worker_id, hostname=socket.gethostname(), pid=os.getpid())
            .on_conflict_do_update(
                index_elements=[WorkerHeartbeat.worker_id],
                set_={"beat_at": func.now(), "stopped_at": stopped_at},
            )
        )
        self._last_beat = time.monotonic()

    # Recovery and schedules

    def recover_stalled_jobs(self) -> list[uuid.UUID]:
        with self.database.transaction() as session:
            recovered = queue.recover_stalled(session, self.lease)
        for job_id in recovered:
            logger.warning(
                "Job %s lost its worker; recovered", job_id, extra={"job_id": str(job_id)}
            )
        return recovered

    def enqueue_due_schedules(self, now: float | None = None) -> int:
        """Enqueue each schedule once per time slot. The slot is in the job's idempotency key, so
        workers racing for the same slot queue one job between them."""
        now = time.time() if now is None else now
        due = []
        for schedule in self.registry.schedules.values():
            slot = int(now // schedule.interval.total_seconds())
            if self._last_slot.get(schedule.name) != slot:
                due.append((schedule, slot))
        if not due:
            return 0
        with self.database.transaction() as session:
            for schedule, slot in due:
                queue.enqueue(
                    session,
                    schedule.kind,
                    schedule.payload,
                    created_by="scheduler",
                    idempotency_key=f"schedule:{schedule.name}:{slot}",
                )
        for schedule, slot in due:
            self._last_slot[schedule.name] = slot
        return len(due)

    # Outbox relay

    def relay_events(self) -> int:
        """Hand a batch of pending events to their handlers. Handlers should be quick: the batch
        stays locked until it is done, so heavy work belongs in a job the handler enqueues."""
        with self.database.transaction() as session:
            events = session.scalars(
                select(OutboxEvent)
                .where(OutboxEvent.processed_at.is_(None), OutboxEvent.available_at <= func.now())
                .order_by(OutboxEvent.available_at, OutboxEvent.id)
                .limit(self.event_batch)
                .with_for_update(skip_locked=True)
            ).all()
            for row in events:
                with log_context(event_id=str(row.id), event_type=row.type):
                    self._deliver(session, row)
        return len(events)

    def _deliver(self, session: Session, row: OutboxEvent) -> None:
        handlers = self.registry.events.get(row.type, {})
        delivered = set(
            session.scalars(select(OutboxDelivery.handler).where(OutboxDelivery.event_id == row.id))
        )
        event = Event(id=row.id, type=row.type, payload=row.payload, created_at=row.created_at)
        errors = []
        for name, handler in handlers.items():
            if name in delivered:
                continue
            try:
                # The handler's writes and its delivery record commit together, or neither does.
                with session.begin_nested():
                    handler(session, event)
                    session.add(OutboxDelivery(event_id=row.id, handler=name))
            except Exception as exc:
                logger.exception("Handler %s failed on event %s (%s)", name, row.id, row.type)
                errors.append(f"{name}: {_describe(exc)}")
        row.attempts += 1
        if errors:
            row.last_error = "\n".join(errors)[:ERROR_LIMIT]
            row.available_at = func.now() + queue.retry_delay(row.attempts)  # type: ignore[assignment]
        else:
            row.last_error = None
            row.processed_at = func.now()  # type: ignore[assignment]
        session.flush()

    # Jobs

    def run_next_job(self) -> bool:
        with self.database.transaction() as session:
            job = queue.claim(session, self.worker_id, self.registry.jobs.keys())
            if job is None:
                return False
            job_id, kind, payload, attempt = job.id, job.kind, job.payload, job.attempts
        self._execute(job_id, kind, payload, attempt)
        return True

    def _execute(self, job_id: uuid.UUID, kind: str, payload: dict[str, Any], attempt: int) -> None:
        with log_context(job_id=str(job_id), job_kind=kind):
            self._run_handler(job_id, kind, payload, attempt)

    def _run_handler(
        self, job_id: uuid.UUID, kind: str, payload: dict[str, Any], attempt: int
    ) -> None:
        logger.info("Job %s (%s) started, attempt %d", job_id, kind, attempt)
        handler = self.registry.jobs[kind]
        with self._lease_kept(job_id):
            try:
                with self.database.transaction() as session:
                    context = JobContext(
                        job_id=job_id,
                        kind=kind,
                        payload=payload,
                        attempt=attempt,
                        session=session,
                        _report_progress=partial(self._report_progress, job_id),
                    )
                    result = handler(context)
                    if not queue.succeed(session, job_id, self.worker_id, result):
                        raise _LeaseLost
            except _LeaseLost:
                logger.warning("Job %s lost its lease; its work was rolled back", job_id)
                return
            except Exception as exc:
                logger.exception("Job %s (%s) failed", job_id, kind)
                with self.database.transaction() as session:
                    status = queue.fail(
                        session,
                        job_id,
                        self.worker_id,
                        _describe(exc),
                        permanent=isinstance(exc, PermanentJobError),
                    )
                if status is JobStatus.QUEUED:
                    logger.info("Job %s will be retried", job_id)
                return
        logger.info("Job %s (%s) succeeded", job_id, kind)

    def _report_progress(self, job_id: uuid.UUID, percent: int) -> None:
        with self.database.transaction() as session:
            queue.set_progress(session, job_id, self.worker_id, percent)

    @contextmanager
    def _lease_kept(self, job_id: uuid.UUID) -> Iterator[None]:
        """Refresh the job's lease (and the heartbeat) while the handler runs."""
        if not self.keep_leases:
            yield
            return
        done = threading.Event()

        def keep() -> None:
            while not done.wait(self.lease.total_seconds() / 3):
                try:
                    with self.database.transaction() as session:
                        queue.refresh_lease(session, job_id, self.worker_id)
                        self._beat(session)
                except Exception:
                    logger.exception("Could not refresh the lease of job %s", job_id)

        thread = threading.Thread(target=keep, name=f"lease-{job_id}", daemon=True)
        thread.start()
        try:
            yield
        finally:
            done.set()
            thread.join()
