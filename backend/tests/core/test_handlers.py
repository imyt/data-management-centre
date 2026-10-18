import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from app.core.errors import (
    ConflictError,
    DomainError,
    InvalidInputError,
    NotFoundError,
    PermissionDeniedError,
)
from app.core.handlers import RequestIdMiddleware, register_error_handlers


def test_health_is_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_request_id_is_echoed_or_generated(client: TestClient) -> None:
    echoed = client.get("/api/v1/health", headers={"X-Request-ID": "req-123"})
    generated = client.get("/api/v1/health")

    assert echoed.headers["X-Request-ID"] == "req-123"
    assert len(generated.headers["X-Request-ID"]) == 32


def test_unknown_route_returns_problem_details(client: TestClient) -> None:
    response = client.get("/api/v1/nope", headers={"X-Request-ID": "req-nope"})

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.headers["X-Request-ID"] == "req-nope"
    assert response.json() == {
        "type": "about:blank",
        "title": "Not Found",
        "status": 404,
        "detail": "Not Found",
        "instance": "/api/v1/nope",
        "request_id": "req-nope",
    }


def _app_raising(exc: Exception) -> TestClient:
    router = APIRouter()

    @router.get("/boom", operation_id="getBoom")
    async def boom() -> None:
        raise exc

    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)
    register_error_handlers(app)
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    ("exc", "status", "code"),
    [
        (NotFoundError("gone"), 404, "not_found"),
        (InvalidInputError("bad"), 400, "invalid_input"),
        (ConflictError("clash"), 409, "conflict"),
        (PermissionDeniedError("no"), 403, "permission_denied"),
        (DomainError("other"), 400, "domain_error"),
    ],
)
def test_domain_errors_map_to_status(exc: DomainError, status: int, code: str) -> None:
    response = _app_raising(exc).get("/boom")
    body = response.json()

    assert response.status_code == status
    assert body["status"] == status
    assert body["type"] == f"urn:dmc:problem:{code}"
    assert body["detail"] == exc.message


def test_domain_details_cannot_overwrite_standard_members() -> None:
    exc = ConflictError("clash", details={"status": 200, "existing_id": "EX-1"})
    body = _app_raising(exc).get("/boom").json()

    assert body["status"] == 409
    assert body["existing_id"] == "EX-1"


def test_unhandled_error_hides_internals() -> None:
    response = _app_raising(RuntimeError("secret")).get("/boom")
    body = response.json()

    assert response.status_code == 500
    assert body["title"] == "Internal Server Error"
    assert "secret" not in response.text
    assert body["request_id"] == response.headers["X-Request-ID"]
