from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy import Connection, Engine, text
from sqlalchemy.orm import Session

from app.core.db import Database
from app.core.jobs import Registry, enqueue
from app.core.jobs.worker import Worker
from app.core.outbox import Event, publish


def _worker(database: Database, registry: Registry) -> Worker:
    return Worker(database, registry, worker_id="test-relay", keep_leases=False)


def _event(connection: Connection, event_id: object) -> dict[str, Any]:
    row = connection.execute(
        text("SELECT *, now() AS now FROM platform.outbox_event WHERE id = :id"), {"id": event_id}
    ).one()
    return dict(row._mapping)


def _publish(database: Database, type: str, payload: dict[str, Any]) -> Any:
    with database.transaction() as session:
        return publish(session, type, payload)


def test_publish_writes_in_the_callers_transaction(
    database: Database, db_connection: Connection
) -> None:
    with pytest.raises(RuntimeError), database.transaction() as session:
        publish(session, "test.changed", {"id": 1})
        raise RuntimeError("the change failed")

    count = db_connection.execute(
        text("SELECT count(*) FROM platform.outbox_event WHERE type = 'test.changed'")
    )
    assert count.scalar_one() == 0


def test_relay_hands_each_event_to_its_types_handlers(
    database: Database, db_connection: Connection
) -> None:
    registry = Registry()
    received: list[tuple[str, Event]] = []
    registry.on_event("test.created", lambda s, e: received.append(("a", e)), name="a")
    registry.on_event("test.created", lambda s, e: received.append(("b", e)), name="b")
    registry.on_event("test.deleted", lambda s, e: received.append(("c", e)), name="c")
    event_id = _publish(database, "test.created", {"id": 7})

    assert _worker(database, registry).relay_events() >= 1

    assert [(name, e.id, e.payload) for name, e in received] == [
        ("a", event_id, {"id": 7}),
        ("b", event_id, {"id": 7}),
    ]
    row = _event(db_connection, event_id)
    assert row["processed_at"] is not None
    assert row["attempts"] == 1


def test_relay_delivers_each_event_once_per_handler_across_retries(
    database: Database, db_connection: Connection
) -> None:
    registry = Registry()
    calls = {"enqueue": 0, "notify": 0}
    notify_works = False

    def enqueue_follow_up(session: Session, event: Event) -> None:
        calls["enqueue"] += 1
        enqueue(session, "test.follow-up", idempotency_key=f"event:{event.id}")

    def notify(session: Session, event: Event) -> None:
        calls["notify"] += 1
        if not notify_works:
            raise ConnectionError("mail server down")

    registry.on_event("test.changed", enqueue_follow_up, name="enqueue_follow_up")
    registry.on_event("test.changed", notify, name="notify")
    event_id = _publish(database, "test.changed", {})
    worker = _worker(database, registry)

    worker.relay_events()

    row = _event(db_connection, event_id)
    assert row["processed_at"] is None
    assert row["attempts"] == 1
    assert "notify: ConnectionError: mail server down" in row["last_error"]
    assert row["available_at"] - row["now"] == timedelta(seconds=10)
    assert worker.relay_events() == 0, "not due until the backoff has passed"

    notify_works = True
    db_connection.execute(
        text("UPDATE platform.outbox_event SET available_at = now() WHERE id = :id"),
        {"id": event_id},
    )
    worker.relay_events()
    worker.relay_events()

    assert calls == {"enqueue": 1, "notify": 2}
    row = _event(db_connection, event_id)
    assert row["processed_at"] is not None
    assert row["last_error"] is None
    deliveries = db_connection.execute(
        text("SELECT handler FROM platform.outbox_delivery WHERE event_id = :id ORDER BY 1"),
        {"id": event_id},
    )
    assert list(deliveries.scalars()) == ["enqueue_follow_up", "notify"]
    follow_ups = db_connection.execute(
        text("SELECT count(*) FROM platform.job WHERE kind = 'test.follow-up'")
    )
    assert follow_ups.scalar_one() == 1


def test_a_failing_handlers_writes_are_rolled_back(
    database: Database, db_connection: Connection
) -> None:
    registry = Registry()

    def half_done(session: Session, event: Event) -> None:
        enqueue(session, "test.half-done")
        raise RuntimeError("failed after writing")

    registry.on_event("test.changed", half_done)
    _publish(database, "test.changed", {})

    _worker(database, registry).relay_events()

    count = db_connection.execute(
        text("SELECT count(*) FROM platform.job WHERE kind = 'test.half-done'")
    )
    assert count.scalar_one() == 0


def test_an_event_without_handlers_is_marked_processed(
    database: Database, db_connection: Connection
) -> None:
    event_id = _publish(database, "test.nobody-listens", {})

    _worker(database, Registry()).relay_events()

    assert _event(db_connection, event_id)["processed_at"] is not None


def test_an_event_being_relayed_is_skipped_by_other_relays(
    committed_database: Database, db_engine: Engine
) -> None:
    registry = Registry()
    received = []
    registry.on_event("test.locked", lambda s, e: received.append(e.id))
    event_id = _publish(committed_database, "test.locked", {})

    with db_engine.connect() as other_relay:
        other_relay.execute(
            text("SELECT id FROM platform.outbox_event WHERE id = :id FOR UPDATE"),
            {"id": event_id},
        )
        _worker(committed_database, registry).relay_events()
        assert received == []
        other_relay.rollback()

    _worker(committed_database, registry).relay_events()
    assert received == [event_id]


def test_handlers_and_jobs_cannot_be_registered_twice() -> None:
    registry = Registry()
    registry.job("test.kind", lambda context: None)
    registry.on_event("test.changed", lambda s, e: None, name="h")
    registry.every(timedelta(minutes=1), "test.kind")

    with pytest.raises(ValueError, match="already registered"):
        registry.job("test.kind", lambda context: None)
    with pytest.raises(ValueError, match="already registered"):
        registry.on_event("test.changed", lambda s, e: None, name="h")
    with pytest.raises(ValueError, match="already registered"):
        registry.every(timedelta(minutes=2), "test.kind")
