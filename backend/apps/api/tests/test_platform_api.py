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


def test_list_examples_pages_with_cursor(client: TestClient) -> None:
    first = client.get("/api/v1/examples", params={"limit": 2}).json()
    second = client.get(
        "/api/v1/examples", params={"limit": 2, "cursor": first["next_cursor"]}
    ).json()

    assert [item["id"] for item in first["items"]] == ["EX-0001", "EX-0002"]
    assert first["total"] == 3
    assert [item["id"] for item in second["items"]] == ["EX-0003"]
    assert second["next_cursor"] is None


def test_get_example(client: TestClient) -> None:
    response = client.get("/api/v1/examples/EX-0002")

    assert response.status_code == 200
    assert response.json() == {
        "id": "EX-0002",
        "name": "Payments ledger",
        "status": "draft",
        "created_at": "2026-10-02T00:00:00Z",
    }


def test_missing_example_returns_error_shape(client: TestClient) -> None:
    response = client.get("/api/v1/examples/EX-9999", headers={"X-Request-ID": "req-404"})

    assert response.status_code == 404
    assert response.json() == {
        "code": "not_found",
        "message": "Example EX-9999 does not exist.",
        "details": {"id": "EX-9999"},
        "request_id": "req-404",
    }


def test_invalid_limit_returns_validation_error(client: TestClient) -> None:
    response = client.get("/api/v1/examples", params={"limit": 0})
    body = response.json()

    assert response.status_code == 422
    assert body["code"] == "validation_error"
    assert body["details"][0]["loc"] == ["query", "limit"]


def test_invalid_cursor_returns_400(client: TestClient) -> None:
    response = client.get("/api/v1/examples", params={"cursor": "%%%"})

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_input"


def test_unknown_route_uses_error_shape(client: TestClient) -> None:
    response = client.get("/api/v1/nope")

    assert response.status_code == 404
    assert response.json()["code"] == "http_error"
