from fastapi.testclient import TestClient


def test_health_is_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_request_id_is_echoed_or_generated(client: TestClient) -> None:
    echoed = client.get("/api/v1/health", headers={"X-Request-ID": "req-123"})
    generated = client.get("/api/v1/health")

    assert echoed.headers["X-Request-ID"] == "req-123"
    assert len(generated.headers["X-Request-ID"]) == 32


def test_unknown_route_uses_error_shape(client: TestClient) -> None:
    response = client.get("/api/v1/nope")

    assert response.status_code == 404
    assert response.json()["code"] == "http_error"
