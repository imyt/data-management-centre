import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient
from sqlalchemy import Connection, event, text
from sqlalchemy.exc import ProgrammingError

from app.core.config import Settings
from app.core.db import SessionDep
from app.core.errors import InvalidInputError
from app.main import create_app


def test_database_is_postgres_18_with_uuidv7(db_connection: Connection) -> None:
    version = db_connection.execute(text("SHOW server_version_num")).scalar_one()
    ids = db_connection.execute(text("SELECT uuidv7() FROM generate_series(1, 2)"))
    first, second = ids.scalars()

    assert int(version) >= 180000
    assert first.version == 7
    assert first < second


def test_runtime_role_cannot_change_the_schema(db_connection: Connection) -> None:
    with pytest.raises(ProgrammingError, match="permission denied"):
        db_connection.execute(text("CREATE SCHEMA not_allowed"))


@pytest.fixture
def probe_client(db_client: TestClient, db_connection: Connection) -> TestClient:
    """Routes that write to a temp table, to check the per-request transaction."""
    db_connection.execute(text("CREATE TEMP TABLE probe (v int)"))
    router = APIRouter()

    @router.post("/probe/ok", operation_id="createProbeOk")
    def write_and_return(session: SessionDep) -> None:
        session.execute(text("INSERT INTO probe VALUES (1)"))

    @router.post("/probe/raise", operation_id="createProbeRaise")
    def write_and_raise(session: SessionDep) -> None:
        session.execute(text("INSERT INTO probe VALUES (2)"))
        raise InvalidInputError("rejected after writing")

    @router.post("/probe/commit-fails", operation_id="createProbeCommitFails")
    def write_with_failing_commit(session: SessionDep) -> None:
        session.execute(text("INSERT INTO probe VALUES (3)"))

        @event.listens_for(session, "before_commit")
        def fail(_session: object) -> None:
            raise RuntimeError("commit failed")

    db_client.app.include_router(router)  # type: ignore[attr-defined]
    return db_client


def _probe_values(connection: Connection) -> list[int]:
    return list(connection.execute(text("SELECT v FROM probe ORDER BY v")).scalars())


def test_request_commits_when_the_route_returns(
    probe_client: TestClient, db_connection: Connection
) -> None:
    assert probe_client.post("/probe/ok").status_code == 200
    assert _probe_values(db_connection) == [1]


def test_request_rolls_back_when_the_route_raises(
    probe_client: TestClient, db_connection: Connection
) -> None:
    assert probe_client.post("/probe/raise").status_code == 400
    assert _probe_values(db_connection) == []


def test_failed_commit_is_an_error_response_not_a_success(
    probe_client: TestClient, db_connection: Connection
) -> None:
    assert probe_client.post("/probe/commit-fails").status_code == 500
    assert _probe_values(db_connection) == []


def test_session_without_a_database_fails_clearly() -> None:
    app = create_app(Settings(_env_file=None, environment="test"))
    router = APIRouter()

    @router.get("/needs-db", operation_id="getNeedsDb")
    def needs_db(session: SessionDep) -> None: ...

    app.include_router(router)
    client = TestClient(app)

    with pytest.raises(RuntimeError, match="DMC_DATABASE_URL"):
        client.get("/needs-db")
