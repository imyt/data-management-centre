import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection, text

from app.core.auth import DEV_USER_HEADER
from app.modules.identity.service import User


@pytest.fixture
def api(db_client: TestClient, personas: dict[str, User]) -> TestClient:
    """Acts as the governance persona, who may change applications in every domain."""
    db_client.headers[DEV_USER_HEADER] = "hannah.becker"
    return db_client


def _ref(client: TestClient, path: str, code: str) -> str:
    items = client.get(f"/api/v1/reference/{path}").json()["data"]
    return next(item["id"] for item in items if item["code"] == code)


def _create(client: TestClient, **overrides: object) -> dict:
    body = {
        "name": "Order management",
        "code": "ORD",
        "domain_id": _ref(client, "domains", "finance"),
        "criticality": "high",
        "hosting": "public_cloud",
        **overrides,
    }
    response = client.post("/api/v1/applications", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def test_reference_lists(api: TestClient) -> None:
    for path in ("domains", "data-categories", "regions", "retention-policies", "purposes"):
        body = api.get(f"/api/v1/reference/{path}").json()
        assert body["data"], path
        assert body["meta"]["total"] == len(body["data"])
    policies = api.get("/api/v1/reference/retention-policies").json()["data"]
    assert all(p["retention_days"] > 0 for p in policies)


def test_register_an_application_with_an_environment_and_a_store(
    api: TestClient, db_connection: Connection
) -> None:
    created = _create(api)
    app_id = created["data"]["id"]
    assert created["data"]["domain"]["code"] == "finance"
    assert created["data"]["environments"] == []
    assert "edit" in created["allowed_actions"]

    eu = _ref(api, "regions", "eu")
    environment = api.post(
        f"/api/v1/applications/{app_id}/environments",
        json={"name": "Production", "type": "production", "region_id": eu},
    )
    assert environment.status_code == 201
    env_id = environment.json()["data"]["id"]
    store = api.post(
        f"/api/v1/environments/{env_id}/data-stores",
        json={
            "name": "orders-db",
            "type": "relational",
            "platform": "PostgreSQL 18",
            "region_id": eu,
            "connection_ref": "vault:dmc/orders-db",
        },
    )
    assert store.status_code == 201
    assert store.json()["data"]["harvest_status"] == "never"

    detail = api.get(f"/api/v1/applications/{app_id}").json()
    assert detail["allowed_actions"] == ["add_data_store", "add_environment", "edit"]
    [env] = detail["data"]["environments"]
    assert env["region"]["code"] == "eu"
    assert [s["name"] for s in env["data_stores"]] == ["orders-db"]

    actions = db_connection.execute(
        text("SELECT action FROM audit.audit_event WHERE subject_type = 'application' ORDER BY seq")
    ).scalars()
    assert list(actions) == ["application.created", "app_environment.created", "data_store.created"]


def test_list_searches_and_filters(api: TestClient) -> None:
    _create(api, code="ORD", name="Order management")
    _create(
        api,
        code="CRM",
        name="Customer portal",
        domain_id=_ref(api, "domains", "customer"),
        lifecycle_status="active",
    )

    everything = api.get("/api/v1/applications").json()
    assert [a["code"] for a in everything["data"]] == ["CRM", "ORD"]
    assert everything["allowed_actions"] == ["create"]
    assert everything["meta"]["total"] == 2

    finance = _ref(api, "domains", "finance")
    by_domain = api.get("/api/v1/applications", params={"domain_id": finance}).json()
    assert [a["code"] for a in by_domain["data"]] == ["ORD"]
    active = api.get("/api/v1/applications", params={"lifecycle_status": "active"}).json()
    assert [a["code"] for a in active["data"]] == ["CRM"]
    search = api.get("/api/v1/applications", params={"q": "portal"}).json()
    assert [a["code"] for a in search["data"]] == ["CRM"]


def test_update_application(api: TestClient) -> None:
    app_id = _create(api)["data"]["id"]

    response = api.patch(
        f"/api/v1/applications/{app_id}", json={"lifecycle_status": "active", "criticality": "low"}
    )

    assert response.status_code == 200
    assert response.json()["data"]["lifecycle_status"] == "active"
    assert response.json()["data"]["criticality"] == "low"


def test_duplicate_code_is_a_conflict(api: TestClient) -> None:
    _create(api)
    response = api.post(
        "/api/v1/applications",
        json={
            "name": "Other",
            "code": "ord",
            "domain_id": _ref(api, "domains", "finance"),
            "criticality": "low",
            "hosting": "saas",
        },
    )

    assert response.status_code == 409
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["field"] == "code"


def test_missing_application_is_not_found(api: TestClient) -> None:
    response = api.get("/api/v1/applications/00000000-0000-7000-8000-000000000000")

    assert response.status_code == 404
    assert response.json()["type"] == "urn:dmc:problem:not_found"


def test_connection_ref_must_be_a_reference_not_a_secret(api: TestClient) -> None:
    app_id = _create(api)["data"]["id"]
    eu = _ref(api, "regions", "eu")
    env_id = api.post(
        f"/api/v1/applications/{app_id}/environments",
        json={"name": "Production", "type": "production", "region_id": eu},
    ).json()["data"]["id"]

    response = api.post(
        f"/api/v1/environments/{env_id}/data-stores",
        json={
            "name": "orders-db",
            "type": "relational",
            "platform": "PostgreSQL 18",
            "region_id": eu,
            "connection_ref": "postgresql://admin:hunter2@db:5432/orders",
        },
    )

    assert response.status_code == 422
    assert response.json()["errors"][0]["loc"] == ["body", "connection_ref"]


def test_roles_and_scope_decide_writes_and_allowed_actions(api: TestClient) -> None:
    app_id = _create(api, domain_id=_ref(api, "domains", "people"))["data"]["id"]
    as_auditor = {DEV_USER_HEADER: "sofia.marin"}
    as_app_owner = {DEV_USER_HEADER: "marcus.webb"}  # scoped to Customer and Finance

    assert api.get("/api/v1/applications", headers=as_auditor).json()["allowed_actions"] == []
    assert api.get(f"/api/v1/applications/{app_id}", headers=as_app_owner).status_code == 403
    listed = api.get("/api/v1/applications", headers=as_app_owner).json()
    assert listed["data"] == []
    assert listed["allowed_actions"] == ["create"]
    auditor_view = api.get(f"/api/v1/applications/{app_id}", headers=as_auditor).json()
    assert auditor_view["allowed_actions"] == []
    denied = api.patch(f"/api/v1/applications/{app_id}", json={"name": "X"}, headers=as_app_owner)
    assert denied.status_code == 403
    assert denied.headers["content-type"] == "application/problem+json"

    created = api.post(
        "/api/v1/applications",
        headers=as_app_owner,
        json={
            "name": "Ledger",
            "code": "GL",
            "domain_id": _ref(api, "domains", "finance"),
            "criticality": "high",
            "hosting": "saas",
        },
    )
    assert created.status_code == 201
    assert created.json()["allowed_actions"] == ["add_data_store", "add_environment", "edit"]


def test_writes_need_a_signed_in_user(db_client: TestClient) -> None:
    response = db_client.get("/api/v1/applications")

    assert response.status_code == 401
