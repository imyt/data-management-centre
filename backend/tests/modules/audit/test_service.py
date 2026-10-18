import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient
from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import DBAPIError, ProgrammingError

from app.core.db import Database, SessionDep
from app.core.errors import InvalidInputError
from app.modules.audit.domain import GENESIS_HASH
from app.modules.audit.service import AuditService


def _record(database: Database, **overrides: object) -> None:
    fields: dict[str, object] = {
        "actor": "user:ada",
        "action": "asset.updated",
        "subject_type": "asset",
        "subject_id": "A-1",
    }
    with database.transaction() as session:
        AuditService(session).record(**{**fields, **overrides})  # type: ignore[arg-type]


def _events(connection: Connection) -> list[dict[str, object]]:
    rows = connection.execute(text("SELECT * FROM audit.audit_event ORDER BY seq"))
    return [dict(row._mapping) for row in rows]


def test_events_form_a_chain_from_genesis(database: Database, db_connection: Connection) -> None:
    _record(database, action="asset.created", after={"name": "Orders"})
    _record(database, action="asset.updated", before={"name": "Orders"}, after={"name": "Sales"})

    first, second = _events(db_connection)
    assert first["prev_hash"] == GENESIS_HASH
    assert second["prev_hash"] == first["hash"]
    with database.transaction() as session:
        assert AuditService(session).verify_chain().valid


def test_values_are_stored_as_hashed_so_the_chain_verifies_after_reading_back(
    database: Database,
) -> None:
    _record(
        database,
        subject_id=uuid.uuid4(),
        before=None,
        after={
            "id": uuid.uuid4(),
            "at": datetime(2026, 10, 18, 9, 30, tzinfo=UTC),
            "score": 0.1,
            "amount": Decimal("12.50"),
            "nested": {"z": [1, 2.5, None, "ü"], "a": True},
        },
    )

    with database.transaction() as session:
        check = AuditService(session).verify_chain()
    assert check.valid
    assert check.checked == 1


def test_risk_decisions_need_a_reason(database: Database, db_connection: Connection) -> None:
    with pytest.raises(InvalidInputError, match="reason is required"):
        _record(database, action="exception.approved", reason="  ", reason_required=True)

    _record(
        database,
        action="exception.approved",
        reason="Compensating control in place",
        reason_required=True,
    )

    assert [e["reason"] for e in _events(db_connection)] == ["Compensating control in place"]


def test_runtime_role_cannot_update_or_delete_events(
    database: Database, db_connection: Connection
) -> None:
    _record(database)

    for statement in ("UPDATE audit.audit_event SET reason = 'x'", "DELETE FROM audit.audit_event"):
        with (
            pytest.raises(ProgrammingError, match="permission denied"),
            db_connection.begin_nested(),
        ):
            db_connection.execute(text(statement))


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE audit.audit_event SET reason = 'x'",
        "DELETE FROM audit.audit_event",
        "TRUNCATE audit.audit_event",
    ],
)
def test_even_the_owner_cannot_change_events(owner_connection: Connection, statement: str) -> None:
    _record(Database(owner_connection))

    with pytest.raises(ProgrammingError, match="append-only"):
        owner_connection.execute(text(statement))


def test_tampering_is_detected(owner_connection: Connection) -> None:
    database = Database(owner_connection)
    _record(database, reason="first")
    _record(database, reason="second")
    owner_connection.execute(text("ALTER TABLE audit.audit_event DISABLE TRIGGER USER"))
    owner_connection.execute(
        text("UPDATE audit.audit_event SET reason = 'edited' WHERE reason = 'first'")
    )
    owner_connection.execute(text("ALTER TABLE audit.audit_event ENABLE TRIGGER USER"))

    with database.transaction() as session:
        check = AuditService(session).verify_chain()

    first_id = _events(owner_connection)[0]["id"]
    assert not check.valid
    assert check.broken_at == first_id
    assert check.problem == "content does not match its hash"


def test_removed_event_is_detected(owner_connection: Connection) -> None:
    database = Database(owner_connection)
    for reason in ("first", "second", "third"):
        _record(database, reason=reason)
    owner_connection.execute(text("ALTER TABLE audit.audit_event DISABLE TRIGGER USER"))
    owner_connection.execute(text("DELETE FROM audit.audit_event WHERE reason = 'second'"))
    owner_connection.execute(text("ALTER TABLE audit.audit_event ENABLE TRIGGER USER"))

    with database.transaction() as session:
        check = AuditService(session).verify_chain()

    assert not check.valid
    assert check.problem == "does not follow the previous event"


def test_concurrent_writers_wait_for_each_other(database: Database, db_engine: Engine) -> None:
    """The first writer holds the chain lock until its transaction ends, so no fork is possible."""
    _record(database)  # holds the lock in the test's open transaction

    with db_engine.connect() as other:
        other.execute(text("SET lock_timeout = '200ms'"))
        with (
            pytest.raises(DBAPIError, match="lock timeout"),
            Database(other).transaction() as session,
        ):
            AuditService(session).record(
                actor="user:bob", action="asset.updated", subject_type="asset", subject_id="A-2"
            )


def test_event_rolls_back_with_the_change(db_client: TestClient, db_connection: Connection) -> None:
    router = APIRouter()

    @router.post("/probe/audited-failure", operation_id="createProbeAuditedFailure")
    def change_then_fail(session: SessionDep) -> None:
        AuditService(session).record(
            actor="user:ada", action="asset.updated", subject_type="asset", subject_id="A-1"
        )
        raise InvalidInputError("the change itself was rejected")

    db_client.app.include_router(router)  # type: ignore[attr-defined]

    assert db_client.post("/probe/audited-failure").status_code == 400
    assert _events(db_connection) == []
