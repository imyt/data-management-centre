from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import Connection, Engine, text

from app.core.db import Database


def _clean(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM platform.job WHERE kind LIKE 'test.%'"))
        connection.execute(text("DELETE FROM platform.outbox_event WHERE type LIKE 'test.%'"))
        connection.execute(
            text("DELETE FROM platform.worker_heartbeat WHERE worker_id LIKE 'test-%'")
        )


@pytest.fixture
def committed_database(db_engine: Engine) -> Iterator[Database]:
    """A database whose transactions really commit, for tests across connections and threads.
    Use kinds and event types starting `test.` and worker ids starting `test-`: they are deleted
    afterwards."""
    _clean(db_engine)
    yield Database(db_engine)
    _clean(db_engine)


def job_row(connection: Connection, job_id: object) -> dict[str, Any]:
    row = connection.execute(
        text("SELECT *, now() AS now FROM platform.job WHERE id = :id"), {"id": job_id}
    ).one()
    return dict(row._mapping)
