from fastapi.testclient import TestClient


def test_list_examples_pages_with_cursor(client: TestClient) -> None:
    first = client.get("/api/v1/examples", params={"limit": 2}).json()
    second = client.get(
        "/api/v1/examples", params={"limit": 2, "cursor": first["meta"]["next_cursor"]}
    ).json()

    assert [item["id"] for item in first["data"]] == ["EX-0001", "EX-0002"]
    assert first["meta"]["total"] == 3
    assert first["allowed_actions"] == []
    assert [item["id"] for item in second["data"]] == ["EX-0003"]
    assert second["meta"]["next_cursor"] is None


def test_get_example(client: TestClient) -> None:
    response = client.get("/api/v1/examples/EX-0002")

    assert response.status_code == 200
    assert response.json() == {
        "data": {
            "id": "EX-0002",
            "name": "Payments ledger",
            "status": "draft",
            "created_at": "2026-10-02T00:00:00Z",
        },
        "allowed_actions": [],
        "meta": {"evaluated_at": None, "stale_after": None},
    }


def test_missing_example_returns_problem_details(client: TestClient) -> None:
    response = client.get("/api/v1/examples/EX-9999", headers={"X-Request-ID": "req-404"})

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json() == {
        "type": "urn:dmc:problem:not_found",
        "title": "Not found",
        "status": 404,
        "detail": "Example EX-9999 does not exist.",
        "instance": "/api/v1/examples/EX-9999",
        "request_id": "req-404",
        "id": "EX-9999",
    }


def test_invalid_limit_returns_validation_problem(client: TestClient) -> None:
    response = client.get("/api/v1/examples", params={"limit": 0})
    body = response.json()

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert body["type"] == "urn:dmc:problem:validation_error"
    assert body["status"] == 422
    assert body["errors"][0]["loc"] == ["query", "limit"]


def test_invalid_cursor_returns_400(client: TestClient) -> None:
    response = client.get("/api/v1/examples", params={"cursor": "%%%"})

    assert response.status_code == 400
    assert response.json()["type"] == "urn:dmc:problem:invalid_input"
