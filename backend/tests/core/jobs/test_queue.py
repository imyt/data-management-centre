import threading
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import Connection, Engine, text

from app.core.db import Database
from app.core.jobs import JobStatus, enqueue
from app.core.jobs.queue import (
    LOST_WORKER_ERROR,
    cancel,
    claim,
    recover_stalled,
    retry_delay,
)

from .conftest import job_row


def test_enqueue_writes_in_the_callers_transaction(
    database: Database, db_connection: Connection
) -> None:
    with pytest.raises(RuntimeError), database.transaction() as session:
        enqueue(session, "test.kept", {"n": 1})
        raise RuntimeError("the caller's change failed")

    count = db_connection.execute(
        text("SELECT count(*) FROM platform.job WHERE kind = 'test.kept'")
    )
    assert count.scalar_one() == 0


def test_enqueue_with_an_idempotency_key_queues_once(database: Database) -> None:
    with database.transaction() as session:
        first = enqueue(session, "test.once", {"n": 1}, idempotency_key="k1")
        again = enqueue(session, "test.once", {"n": 2}, idempotency_key="k1")
        other_kind = enqueue(session, "test.other", {"n": 1}, idempotency_key="k1")

    assert again.id == first.id
    assert again.payload == {"n": 1}
    assert other_kind.id != first.id


def test_claim_takes_the_oldest_due_job_of_a_known_kind(
    database: Database, db_connection: Connection
) -> None:
    with database.transaction() as session:
        unknown = enqueue(session, "test.unknown")
        an_hour_from_now = job_row(db_connection, unknown.id)["now"] + timedelta(hours=1)
        later = enqueue(session, "test.claim", run_after=an_hour_from_now)
        first = enqueue(session, "test.claim", {"order": 1})
        second = enqueue(session, "test.claim", {"order": 2})

    with database.transaction() as session:
        claimed = [claim(session, "test-w", ["test.claim"]) for _ in range(3)]

    assert [job.id if job else None for job in claimed] == [first.id, second.id, None]
    row = job_row(db_connection, first.id)
    assert row["status"] == JobStatus.RUNNING
    assert row["attempts"] == 1
    assert row["locked_by"] == "test-w"
    assert row["locked_at"] == row["started_at"] == row["now"]
    assert job_row(db_connection, later.id)["status"] == JobStatus.QUEUED
    assert job_row(db_connection, unknown.id)["status"] == JobStatus.QUEUED


def test_claim_with_no_kinds_claims_nothing(database: Database) -> None:
    with database.transaction() as session:
        enqueue(session, "test.claim")
        assert claim(session, "test-w", []) is None


def test_two_workers_never_claim_the_same_job(
    committed_database: Database, db_engine: Engine
) -> None:
    with committed_database.transaction() as session:
        jobs = [enqueue(session, "test.race").id for _ in range(2)]

    # Worker A's claim is not committed yet, so its row is still locked: B skips it.
    with committed_database.transaction() as a, committed_database.transaction() as b:
        claimed_by_a = claim(a, "test-a", ["test.race"])
        claimed_by_b = claim(b, "test-b", ["test.race"])
        assert claimed_by_a is not None
        assert claimed_by_b is not None
        assert {claimed_by_a.id, claimed_by_b.id} == set(jobs)
        assert claim(b, "test-b", ["test.race"]) is None


def test_many_workers_claim_each_job_exactly_once(committed_database: Database) -> None:
    with committed_database.transaction() as session:
        jobs = {enqueue(session, "test.race").id for _ in range(60)}
    claims: dict[str, list[uuid.UUID]] = {}
    start = threading.Barrier(6)

    def work(worker_id: str) -> None:
        mine = claims.setdefault(worker_id, [])
        start.wait()
        while True:
            with committed_database.transaction() as session:
                job = claim(session, worker_id, ["test.race"])
            if job is None:
                return
            mine.append(job.id)

    threads = [threading.Thread(target=work, args=(f"test-{n}",)) for n in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    claimed = [job_id for ids in claims.values() for job_id in ids]
    assert sorted(claimed) == sorted(jobs)


def test_retry_delay_doubles_up_to_an_hour() -> None:
    delays = [retry_delay(attempt) for attempt in (1, 2, 3, 4, 20)]

    assert delays == [
        timedelta(seconds=10),
        timedelta(seconds=20),
        timedelta(seconds=40),
        timedelta(seconds=80),
        timedelta(hours=1),
    ]


def test_cancel_stops_a_queued_job_only(database: Database, db_connection: Connection) -> None:
    with database.transaction() as session:
        queued = enqueue(session, "test.cancel")
        running = enqueue(session, "test.cancel-running")
        claim(session, "test-w", ["test.cancel-running"])

        assert cancel(session, queued.id) is True
        assert cancel(session, running.id) is False

    row = job_row(db_connection, queued.id)
    assert row["status"] == JobStatus.CANCELLED
    assert row["finished_at"] is not None


def test_stalled_jobs_are_requeued_or_failed_when_out_of_attempts(
    database: Database, db_connection: Connection
) -> None:
    with database.transaction() as session:
        stalled = enqueue(session, "test.stalled")
        last_try = enqueue(session, "test.stalled", max_attempts=1)
        alive = enqueue(session, "test.alive")
        for _ in range(3):
            claim(session, "test-dead", ["test.stalled", "test.alive"])
    db_connection.execute(
        text(
            "UPDATE platform.job SET locked_at = now() - interval '10 minutes' WHERE id IN (:a, :b)"
        ),
        {"a": stalled.id, "b": last_try.id},
    )

    with database.transaction() as session:
        recovered = recover_stalled(session, timedelta(minutes=5))

    assert set(recovered) == {stalled.id, last_try.id}
    requeued = job_row(db_connection, stalled.id)
    assert requeued["status"] == JobStatus.QUEUED
    assert requeued["locked_by"] is None
    assert requeued["error"] == LOST_WORKER_ERROR
    failed = job_row(db_connection, last_try.id)
    assert failed["status"] == JobStatus.FAILED
    assert failed["finished_at"] is not None
    assert job_row(db_connection, alive.id)["status"] == JobStatus.RUNNING
