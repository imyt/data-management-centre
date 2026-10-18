import threading
import time
from datetime import timedelta
from typing import Any

from sqlalchemy import Connection, text

from app.core.db import Database
from app.core.jobs import JobContext, JobStatus, PermanentJobError, Registry, enqueue
from app.core.jobs.worker import Worker
from app.core.outbox import publish

from .conftest import job_row


def _worker(database: Database, registry: Registry, **options: Any) -> Worker:
    return Worker(database, registry, worker_id="test-worker", keep_leases=False, **options)


def _queue(database: Database, kind: str, **options: Any) -> Any:
    with database.transaction() as session:
        return enqueue(session, kind, {"n": 1}, **options).id


def _events(connection: Connection, type: str) -> int:
    count = connection.execute(
        text("SELECT count(*) FROM platform.outbox_event WHERE type = :t"), {"t": type}
    )
    return count.scalar_one()


def test_a_job_runs_and_its_writes_commit_with_its_result(
    database: Database, db_connection: Connection
) -> None:
    registry = Registry()

    def handler(context: JobContext) -> dict[str, Any]:
        publish(context.session, "test.done", {"job": context.job_id})
        return {"doubled": context.payload["n"] * 2}

    registry.job("test.ok", handler)
    job_id = _queue(database, "test.ok")

    assert _worker(database, registry).run_next_job() is True

    row = job_row(db_connection, job_id)
    assert row["status"] == JobStatus.SUCCEEDED
    assert row["result"] == {"doubled": 2}
    assert row["progress"] == 100
    assert row["locked_by"] is None
    assert row["finished_at"] is not None
    assert _events(db_connection, "test.done") == 1


def test_a_failed_attempt_rolls_back_and_retries_with_backoff(
    database: Database, db_connection: Connection
) -> None:
    registry = Registry()

    def handler(context: JobContext) -> None:
        publish(context.session, "test.half-done", {})
        raise ValueError("source unreachable")

    registry.job("test.flaky", handler)
    job_id = _queue(database, "test.flaky", max_attempts=2)
    worker = _worker(database, registry)

    worker.run_next_job()

    row = job_row(db_connection, job_id)
    assert row["status"] == JobStatus.QUEUED
    assert row["attempts"] == 1
    assert row["error"] == "ValueError: source unreachable"
    assert row["run_after"] - row["now"] == timedelta(seconds=10)
    assert row["locked_by"] is None
    assert _events(db_connection, "test.half-done") == 0
    assert worker.run_next_job() is False, "not due until the backoff has passed"

    db_connection.execute(
        text("UPDATE platform.job SET run_after = now() WHERE id = :id"), {"id": job_id}
    )
    worker.run_next_job()

    row = job_row(db_connection, job_id)
    assert row["status"] == JobStatus.FAILED
    assert row["attempts"] == 2
    assert row["finished_at"] is not None


def test_a_permanent_error_fails_without_retries(
    database: Database, db_connection: Connection
) -> None:
    registry = Registry()

    def handler(context: JobContext) -> None:
        raise PermanentJobError("the store was decommissioned")

    registry.job("test.doomed", handler)
    job_id = _queue(database, "test.doomed")

    _worker(database, registry).run_next_job()

    row = job_row(db_connection, job_id)
    assert row["status"] == JobStatus.FAILED
    assert row["attempts"] == 1
    assert "decommissioned" in row["error"]


def test_progress_is_visible_while_the_job_runs(database: Database) -> None:
    registry = Registry()
    seen = []

    def handler(context: JobContext) -> None:
        context.set_progress(40)
        with database.transaction() as other:
            progress = other.execute(
                text("SELECT progress FROM platform.job WHERE id = :id"), {"id": context.job_id}
            )
            seen.append(progress.scalar_one())

    registry.job("test.progress", handler)
    _queue(database, "test.progress")

    _worker(database, registry).run_next_job()

    assert seen == [40]


def test_a_job_whose_lease_was_lost_does_not_commit(
    database: Database, db_connection: Connection
) -> None:
    registry = Registry()

    def handler(context: JobContext) -> None:
        # Meanwhile the job is recovered and another worker claims it. (This runs before the
        # handler writes: in tests every session shares one connection, and the handler's
        # rollback would otherwise undo it too.)
        with database.transaction() as other:
            other.execute(
                text("UPDATE platform.job SET locked_by = 'test-other' WHERE id = :id"),
                {"id": context.job_id},
            )
        publish(context.session, "test.duplicate-work", {})

    registry.job("test.slow", handler)
    job_id = _queue(database, "test.slow")

    _worker(database, registry).run_next_job()

    row = job_row(db_connection, job_id)
    assert row["status"] == JobStatus.RUNNING
    assert row["locked_by"] == "test-other"
    assert _events(db_connection, "test.duplicate-work") == 0


def test_schedules_enqueue_once_per_slot_across_workers(
    database: Database, db_connection: Connection
) -> None:
    registry = Registry()
    registry.job("test.tick", lambda context: None)
    registry.every(timedelta(minutes=5), "test.tick", {"scope": "all"})
    first = _worker(database, registry)
    second = Worker(database, registry, worker_id="test-second", keep_leases=False)
    slot_start = 1_800_000_000.0  # a multiple of 300 seconds: slot 6,000,000

    assert first.enqueue_due_schedules(now=slot_start) == 1
    assert first.enqueue_due_schedules(now=slot_start + 299) == 0
    second.enqueue_due_schedules(now=slot_start + 10)
    first.enqueue_due_schedules(now=slot_start + 300)

    jobs = db_connection.execute(
        text("SELECT idempotency_key, payload FROM platform.job WHERE kind = 'test.tick'")
    ).all()
    assert sorted(tuple(row) for row in jobs) == [
        ("schedule:test.tick:6000000", {"scope": "all"}),
        ("schedule:test.tick:6000001", {"scope": "all"}),
    ]


def test_heartbeat_records_the_worker_and_when_it_stopped(
    database: Database, db_connection: Connection
) -> None:
    worker = _worker(database, Registry(), poll_interval=0.01)
    stop = threading.Event()
    stop.set()

    worker.run(stop)

    row = db_connection.execute(
        text("SELECT pid, stopped_at FROM platform.worker_heartbeat WHERE worker_id = :id"),
        {"id": "test-worker"},
    ).one()
    assert row.pid > 0
    assert row.stopped_at is not None


def test_a_running_worker_keeps_its_lease_and_stops_gracefully(
    committed_database: Database,
) -> None:
    """Real threads and commits: the handler outlives its lease three times over while another
    worker keeps recovering stalled jobs, yet it runs once."""
    registry = Registry()
    runs = []

    def handler(context: JobContext) -> str:
        runs.append(context.attempt)
        time.sleep(1.2)
        return "done"

    registry.job("test.long", handler)
    job_id = _queue(committed_database, "test.long")
    lease = timedelta(seconds=0.4)
    worker = Worker(
        committed_database, registry, worker_id="test-long", lease=lease, poll_interval=0.05
    )
    rival = Worker(committed_database, Registry(), worker_id="test-rival", lease=lease)
    stop = threading.Event()
    thread = threading.Thread(target=worker.run, args=(stop,))
    thread.start()
    status = None
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and status != JobStatus.SUCCEEDED:
            rival.recover_stalled_jobs()
            time.sleep(0.05)
            with committed_database.transaction() as session:
                status = session.execute(
                    text("SELECT status FROM platform.job WHERE id = :id"), {"id": job_id}
                ).scalar_one()
    finally:
        stop.set()
        thread.join(timeout=10)

    assert not thread.is_alive()
    assert status == JobStatus.SUCCEEDED
    assert runs == [1]
    with committed_database.transaction() as session:
        stopped_at = session.execute(
            text("SELECT stopped_at FROM platform.worker_heartbeat WHERE worker_id = 'test-long'")
        ).scalar_one()
    assert stopped_at is not None
