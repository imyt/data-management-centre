import uuid

import pytest
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy import Connection, text

from app.core.auth import DEV_USER_HEADER, PrincipalDep
from app.core.db import Database, SessionDep
from app.core.errors import InvalidInputError
from app.core.idempotency import IdempotencyDep
from app.core.jobs import JobContext, Registry, enqueue
from app.core.jobs.router import accepted
from app.core.jobs.schemas import JobResponse
from app.core.jobs.worker import Worker
from app.modules.identity.service import User


class ThingCreate(BaseModel):
    name: str


@pytest.fixture
def probe_client(
    db_client: TestClient, db_connection: Connection, personas: dict[str, User]
) -> TestClient:
    """Retryable writes against a temp table, to check Idempotency-Key and 202 Accepted.
    Requests act as Marcus (an application owner) unless they name another user."""
    db_connection.execute(text("CREATE TEMP TABLE thing (name text)"))
    router = APIRouter(prefix="/probe")

    @router.post("/things", status_code=201, operation_id="createThing")
    def create_thing(
        body: ThingCreate, session: SessionDep, idempotency: IdempotencyDep
    ) -> JSONResponse:
        session.execute(text("INSERT INTO thing VALUES (:name)"), {"name": body.name})
        count = session.execute(text("SELECT count(*) FROM thing")).scalar_one()
        content = {"data": {"name": body.name, "count": count}}
        headers = {"Location": f"/probe/things/{count}"}
        return idempotency.record(JSONResponse(content, status_code=201, headers=headers))

    @router.post("/fails", operation_id="createFailure")
    def fails(session: SessionDep, idempotency: IdempotencyDep) -> None:
        session.execute(text("INSERT INTO thing VALUES ('failed')"))
        raise InvalidInputError("rejected after writing")

    @router.post("/forgets", operation_id="createForgetful")
    def forgets(session: SessionDep, idempotency: IdempotencyDep) -> dict[str, bool]:
        session.execute(text("INSERT INTO thing VALUES ('forgotten')"))
        return {"ok": True}

    @router.post(
        "/exports", status_code=202, response_model=JobResponse, operation_id="createExport"
    )
    def start_export(
        request: Request, session: SessionDep, principal: PrincipalDep, idempotency: IdempotencyDep
    ) -> JSONResponse:
        job = enqueue(session, "test.export", {}, created_by=principal.actor)
        return idempotency.record(accepted(request, job))

    db_client.app.include_router(router)  # type: ignore[attr-defined]
    db_client.headers[DEV_USER_HEADER] = "marcus.webb"
    return db_client


def _things(connection: Connection) -> list[str]:
    return list(connection.execute(text("SELECT name FROM thing")).scalars())


def _keys(connection: Connection) -> int:
    return connection.execute(text("SELECT count(*) FROM platform.idempotency_key")).scalar_one()


KEY = {"Idempotency-Key": "8c6f2d1e-0b5a-4c1e-9b7e-2f3a4d5e6f70"}


def test_without_a_key_every_request_runs(
    probe_client: TestClient, db_connection: Connection
) -> None:
    first = probe_client.post("/probe/things", json={"name": "a"})
    second = probe_client.post("/probe/things", json={"name": "a"})

    assert (first.status_code, second.status_code) == (201, 201)
    assert "Idempotent-Replayed" not in second.headers
    assert _things(db_connection) == ["a", "a"]


def test_a_retry_with_the_same_key_replays_the_response(
    probe_client: TestClient, db_connection: Connection
) -> None:
    first = probe_client.post("/probe/things", json={"name": "a"}, headers=KEY)
    retry = probe_client.post("/probe/things", json={"name": "a"}, headers=KEY)

    assert first.status_code == retry.status_code == 201
    assert retry.json() == first.json() == {"data": {"name": "a", "count": 1}}
    assert retry.headers["Location"] == first.headers["Location"] == "/probe/things/1"
    assert retry.headers["Idempotent-Replayed"] == "true"
    assert "Idempotent-Replayed" not in first.headers
    assert _things(db_connection) == ["a"]


@pytest.mark.parametrize(
    ("path", "body"), [("/probe/things", {"name": "b"}), ("/probe/exports", None)]
)
def test_the_same_key_for_a_different_request_is_a_conflict(
    probe_client: TestClient, db_connection: Connection, path: str, body: object
) -> None:
    probe_client.post("/probe/things", json={"name": "a"}, headers=KEY)

    response = probe_client.post(path, json=body, headers=KEY)

    assert response.status_code == 409
    assert response.headers["content-type"] == "application/problem+json"
    problem = response.json()
    assert problem["type"] == "urn:dmc:problem:conflict"
    assert problem["idempotency_key"] == KEY["Idempotency-Key"]
    assert _things(db_connection) == ["a"]


def test_keys_are_per_caller(probe_client: TestClient, db_connection: Connection) -> None:
    probe_client.post("/probe/things", json={"name": "a"}, headers=KEY)

    other = probe_client.post(
        "/probe/things", json={"name": "a"}, headers={**KEY, DEV_USER_HEADER: "priya.raman"}
    )

    assert other.status_code == 201
    assert "Idempotent-Replayed" not in other.headers
    assert _things(db_connection) == ["a", "a"]


def test_a_failed_request_keeps_no_key_so_it_can_be_retried(
    probe_client: TestClient, db_connection: Connection
) -> None:
    assert probe_client.post("/probe/fails", headers=KEY).status_code == 400
    assert probe_client.post("/probe/fails", headers=KEY).status_code == 400

    assert _keys(db_connection) == 0
    assert _things(db_connection) == []


def test_an_expired_key_runs_the_request_again(
    probe_client: TestClient, db_connection: Connection
) -> None:
    probe_client.post("/probe/things", json={"name": "a"}, headers=KEY)
    db_connection.execute(
        text("UPDATE platform.idempotency_key SET expires_at = now() - interval '1 second'")
    )

    response = probe_client.post("/probe/things", json={"name": "a"}, headers=KEY)

    assert "Idempotent-Replayed" not in response.headers
    assert _things(db_connection) == ["a", "a"]


def test_keys_are_kept_for_24_hours(probe_client: TestClient, db_connection: Connection) -> None:
    probe_client.post("/probe/things", json={"name": "a"}, headers=KEY)

    ttl = db_connection.execute(
        text("SELECT expires_at - created_at FROM platform.idempotency_key")
    ).scalar_one()
    assert ttl.total_seconds() == 24 * 3600


def test_a_route_that_takes_a_key_must_record_its_response(
    probe_client: TestClient, db_connection: Connection
) -> None:
    assert probe_client.post("/probe/forgets", headers=KEY).status_code == 500
    assert probe_client.post("/probe/forgets").status_code == 200

    assert _keys(db_connection) == 0
    assert _things(db_connection) == ["forgotten"]


def test_an_overlong_key_is_rejected(probe_client: TestClient) -> None:
    response = probe_client.post(
        "/probe/things", json={"name": "a"}, headers={"Idempotency-Key": "k" * 256}
    )

    assert response.status_code == 422


def test_a_long_operation_returns_202_with_a_job_to_poll(
    probe_client: TestClient, db_connection: Connection
) -> None:
    response = probe_client.post("/probe/exports", headers=KEY)
    retry = probe_client.post("/probe/exports", headers=KEY)

    assert response.status_code == retry.status_code == 202
    job = response.json()["data"]
    assert job["status"] == "queued"
    assert response.headers["Location"] == f"/api/v1/jobs/{job['id']}"
    assert retry.json()["data"]["id"] == job["id"]
    exports = db_connection.execute(
        text("SELECT count(*) FROM platform.job WHERE kind = 'test.export'")
    )
    assert exports.scalar_one() == 1

    polled = probe_client.get(response.headers["Location"])

    assert polled.status_code == 200
    assert polled.json()["data"]["id"] == job["id"]


def test_get_job_reports_status_progress_result_and_error(
    db_client: TestClient, database: Database, personas: dict[str, User]
) -> None:
    db_client.headers[DEV_USER_HEADER] = "marcus.webb"
    registry = Registry()
    outcomes = iter([RuntimeError("store unreachable"), None])

    def export(context: JobContext) -> dict[str, str]:
        if (failure := next(outcomes)) is not None:
            raise failure
        return {"uri": "exports/1.csv"}

    registry.job("test.export", export)
    with database.transaction() as session:
        job_id = enqueue(
            session,
            "test.export",
            {"secret": "not shown"},
            created_by=f"user:{personas['marcus.webb'].id}",
        ).id
    worker = Worker(database, registry, worker_id="test-api", keep_leases=False)

    queued = db_client.get(f"/api/v1/jobs/{job_id}").json()
    worker.run_next_job()
    retrying = db_client.get(f"/api/v1/jobs/{job_id}").json()
    with database.transaction() as session:
        session.execute(
            text("UPDATE platform.job SET run_after = now() WHERE id = :id"), {"id": job_id}
        )
    worker.run_next_job()
    done = db_client.get(f"/api/v1/jobs/{job_id}").json()

    assert set(queued) == {"data", "allowed_actions", "meta"}
    assert "payload" not in queued["data"]
    assert (queued["data"]["status"], queued["data"]["progress"]) == ("queued", None)
    assert retrying["data"]["status"] == "queued"
    assert retrying["data"]["attempts"] == 1
    assert retrying["data"]["error"] == "RuntimeError: store unreachable"
    assert done["data"]["status"] == "succeeded"
    assert done["data"]["progress"] == 100
    assert done["data"]["result"] == {"uri": "exports/1.csv"}
    assert done["data"]["error"] is None
    assert done["data"]["finished_at"] is not None


@pytest.mark.parametrize(
    ("user", "status_code"),
    [("marcus.webb", 200), ("hannah.becker", 200), ("priya.raman", 404), ("sofia.marin", 404)],
)
def test_a_job_is_seen_by_its_creator_and_governance_only(
    db_client: TestClient,
    database: Database,
    personas: dict[str, User],
    user: str,
    status_code: int,
) -> None:
    with database.transaction() as session:
        job = enqueue(session, "test.export", created_by=f"user:{personas['marcus.webb'].id}")

    response = db_client.get(f"/api/v1/jobs/{job.id}", headers={DEV_USER_HEADER: user})

    assert response.status_code == status_code


def test_get_job_that_does_not_exist_is_404(
    db_client: TestClient, personas: dict[str, User]
) -> None:
    response = db_client.get(
        f"/api/v1/jobs/{uuid.uuid4()}", headers={DEV_USER_HEADER: "hannah.becker"}
    )

    assert response.status_code == 404
    assert response.json()["type"] == "urn:dmc:problem:not_found"


def test_get_job_needs_a_signed_in_caller(db_client: TestClient) -> None:
    assert db_client.get(f"/api/v1/jobs/{uuid.uuid4()}").status_code == 401


def test_get_job_with_a_malformed_id_is_422(
    db_client: TestClient, personas: dict[str, User]
) -> None:
    response = db_client.get("/api/v1/jobs/not-a-uuid", headers={DEV_USER_HEADER: "hannah.becker"})

    assert response.status_code == 422
