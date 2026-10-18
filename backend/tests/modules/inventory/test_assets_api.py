import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection, text

from app.core.auth import DEV_USER_HEADER, Role
from app.core.db import Database
from app.modules.identity.service import IdentityService, NewUser, User

GOVERNANCE = {DEV_USER_HEADER: "hannah.becker"}
APP_OWNER = {DEV_USER_HEADER: "marcus.webb"}  # Customer and Finance
DATA_OWNER = {DEV_USER_HEADER: "priya.raman"}  # Customer only
STEWARD = {DEV_USER_HEADER: "lena.okafor"}  # Customer only
AUDITOR = {DEV_USER_HEADER: "sofia.marin"}


@pytest.fixture
def api(db_client: TestClient, personas: dict[str, User]) -> TestClient:
    return db_client


def _ref(client: TestClient, path: str, code: str) -> str:
    items = client.get(f"/api/v1/reference/{path}", headers=GOVERNANCE).json()["data"]
    return next(item["id"] for item in items if item["code"] == code)


def _create(client: TestClient, headers: dict[str, str] = GOVERNANCE, **overrides: object) -> dict:
    body = {
        "name": "Customer master",
        "domain_id": _ref(client, "domains", "customer"),
        "business_context": "Golden record of customers.",
        **overrides,
    }
    response = client.post("/api/v1/assets", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["data"]


def domain_id(client: TestClient, code: str) -> uuid.UUID:
    return uuid.UUID(_ref(client, "domains", code))


def _user_id(personas: dict[str, User], name: str) -> str:
    return str(personas[name].id)


def _audit(connection: Connection) -> list[tuple[str, str | None]]:
    rows = connection.execute(
        text(
            "SELECT action, reason FROM audit.audit_event WHERE subject_type = 'asset' ORDER BY seq"
        )
    )
    return [(row.action, row.reason) for row in rows]


def test_declare_an_asset_with_category_context_and_retention(
    api: TestClient, db_connection: Connection
) -> None:
    policy = api.get("/api/v1/reference/retention-policies", headers=GOVERNANCE).json()["data"][0][
        "id"
    ]
    category = api.get("/api/v1/reference/data-categories", headers=GOVERNANCE).json()["data"][0][
        "id"
    ]

    asset = _create(
        api,
        APP_OWNER,
        data_category_id=category,
        is_stored=True,
        retention_policy_id=policy,
    )

    assert asset["type"] == "dataset"
    assert asset["is_stored"] is True
    assert asset["retention_policy"]["id"] == policy
    assert asset["owner"] is None
    assert asset["data_elements"] == []
    assert _audit(db_connection) == [("asset.created", None)]


def test_a_stored_asset_needs_a_retention_policy_and_an_unstored_one_has_none(
    api: TestClient,
) -> None:
    body = {"name": "Orders", "domain_id": _ref(api, "domains", "customer")}
    policy = api.get("/api/v1/reference/retention-policies", headers=GOVERNANCE).json()["data"][0]

    stored = api.post("/api/v1/assets", json={**body, "is_stored": True}, headers=GOVERNANCE)
    unstored = api.post(
        "/api/v1/assets", json={**body, "retention_policy_id": policy["id"]}, headers=GOVERNANCE
    )

    assert stored.status_code == 400
    assert stored.json()["field"] == "retention_policy_id"
    assert unstored.status_code == 400

    asset = _create(api, is_stored=True, retention_policy_id=policy["id"])
    cleared = api.patch(
        f"/api/v1/assets/{asset['id']}", json={"is_stored": False}, headers=GOVERNANCE
    )
    assert cleared.status_code == 200
    assert cleared.json()["data"]["retention_policy"] is None


def test_roles_and_scope_decide_who_declares_and_reads(api: TestClient) -> None:
    people = _ref(api, "domains", "people")
    asset = _create(api, domain_id=people)

    assert api.get("/api/v1/assets", headers=AUDITOR).json()["allowed_actions"] == []
    assert api.get("/api/v1/assets", headers=APP_OWNER).json()["data"] == []
    assert api.get(f"/api/v1/assets/{asset['id']}", headers=APP_OWNER).status_code == 403
    denied = api.post("/api/v1/assets", json={"name": "X", "domain_id": people}, headers=APP_OWNER)
    assert denied.status_code == 403
    read_only = api.post(
        "/api/v1/assets",
        json={"name": "X", "domain_id": _ref(api, "domains", "customer")},
        headers=AUDITOR,
    )
    assert read_only.status_code == 403


def test_list_searches_filters_and_pages(api: TestClient) -> None:
    for name in ("Alpha", "Bravo", "Charlie"):
        _create(api, name=name)
    _create(api, name="Churn report", type="report")

    first = api.get("/api/v1/assets", params={"limit": 2}, headers=GOVERNANCE).json()
    second = api.get(
        "/api/v1/assets",
        params={"limit": 2, "cursor": first["meta"]["next_cursor"]},
        headers=GOVERNANCE,
    ).json()
    reports = api.get("/api/v1/assets", params={"type": "report"}, headers=GOVERNANCE).json()
    search = api.get("/api/v1/assets", params={"q": "brav"}, headers=GOVERNANCE).json()

    assert [a["name"] for a in first["data"]] == ["Alpha", "Bravo"]
    assert [a["name"] for a in second["data"]] == ["Charlie", "Churn report"]
    assert second["meta"]["next_cursor"] is None
    assert first["meta"]["total"] == 4
    assert [a["name"] for a in reports["data"]] == ["Churn report"]
    assert [a["name"] for a in search["data"]] == ["Bravo"]


def test_data_elements_flag_pii_and_only_a_data_owner_flags_cde(
    api: TestClient, db_connection: Connection
) -> None:
    asset_id = _create(api)["id"]

    created = api.post(
        f"/api/v1/assets/{asset_id}/data-elements",
        json={"name": "email", "data_type": "text", "is_pii": True},
        headers=APP_OWNER,
    )
    assert created.status_code == 201
    element = created.json()["data"]
    assert (element["is_pii"], element["pii_source"], element["is_cde"]) == (
        True,
        "declared",
        False,
    )

    refused = api.patch(
        f"/api/v1/data-elements/{element['id']}", json={"is_cde": True}, headers=APP_OWNER
    )
    assert refused.status_code == 403
    flagged = api.patch(
        f"/api/v1/data-elements/{element['id']}", json={"is_cde": True}, headers=DATA_OWNER
    )
    assert flagged.json()["data"]["is_cde"] is True
    cleared = api.patch(
        f"/api/v1/data-elements/{element['id']}", json={"is_pii": False}, headers=APP_OWNER
    )
    assert cleared.json()["data"]["pii_source"] is None

    duplicate = api.post(
        f"/api/v1/assets/{asset_id}/data-elements",
        json={"name": "EMAIL", "data_type": "text"},
        headers=APP_OWNER,
    )
    assert duplicate.status_code == 409
    detail = api.get(f"/api/v1/assets/{asset_id}", headers=GOVERNANCE).json()
    assert [e["name"] for e in detail["data"]["data_elements"]] == ["email"]
    assert [a for a, _ in _audit(db_connection)] == [
        "asset.created",
        "data_element.created",
        "data_element.updated",
        "data_element.updated",
    ]


def test_assign_confirm_and_the_inbox(
    api: TestClient, personas: dict[str, User], db_connection: Connection
) -> None:
    asset = _create(api, name="Customer master")
    assert api.get("/api/v1/inbox", headers=DATA_OWNER).json()["data"] == []

    assigned = api.put(
        f"/api/v1/assets/{asset['id']}/ownership/owner",
        json={"user_id": _user_id(personas, "priya.raman")},
        headers=APP_OWNER,
    )
    assert assigned.status_code == 200, assigned.text
    owner = assigned.json()["data"]["owner"]
    assert (owner["status"], owner["user"]["display_name"]) == ("pending", "Priya Raman")
    assert owner["assigned_by"]["display_name"] == "Marcus Webb"

    inbox = api.get("/api/v1/inbox", headers=DATA_OWNER).json()
    [item] = inbox["data"]
    assert (item["kind"], item["subject_name"], item["overdue"]) == (
        "ownership_confirmation",
        "Customer master",
        False,
    )
    assert item["title"] == "Confirm you are the Data Owner of Customer master"
    assert api.get("/api/v1/inbox", headers=APP_OWNER).json()["data"] == []
    detail = api.get(f"/api/v1/assets/{asset['id']}", headers=DATA_OWNER).json()
    assert "confirm_owner" in detail["allowed_actions"]
    assert (
        "confirm_owner"
        not in api.get(f"/api/v1/assets/{asset['id']}", headers=APP_OWNER).json()["allowed_actions"]
    )

    stranger = api.post(f"/api/v1/assets/{asset['id']}/ownership/owner/confirm", headers=APP_OWNER)
    assert stranger.status_code == 403
    confirmed = api.post(
        f"/api/v1/assets/{asset['id']}/ownership/owner/confirm", headers=DATA_OWNER
    )
    assert confirmed.json()["data"]["owner"]["status"] == "confirmed"
    assert api.get("/api/v1/inbox", headers=DATA_OWNER).json()["data"] == []
    again = api.post(f"/api/v1/assets/{asset['id']}/ownership/owner/confirm", headers=DATA_OWNER)
    assert again.status_code == 409
    assert [a for a, _ in _audit(db_connection)] == [
        "asset.created",
        "asset.owner_assigned",
        "asset.owner_confirmed",
    ]


def test_disputes_and_reassignments_need_a_reason_and_are_audited(
    api: TestClient, personas: dict[str, User], db_connection: Connection
) -> None:
    asset_id = _create(api)["id"]
    path = f"/api/v1/assets/{asset_id}/ownership"
    api.put(
        f"{path}/owner", json={"user_id": _user_id(personas, "priya.raman")}, headers=GOVERNANCE
    )

    no_reason = api.post(f"{path}/owner/dispute", json={}, headers=DATA_OWNER)
    assert no_reason.status_code == 422
    disputed = api.post(
        f"{path}/owner/dispute", json={"reason": "This belongs to Finance."}, headers=DATA_OWNER
    )
    owner = disputed.json()["data"]["owner"]
    assert (owner["status"], owner["reason"]) == ("disputed", "This belongs to Finance.")
    assert api.get("/api/v1/inbox", headers=DATA_OWNER).json()["data"] == []
    assert "confirm_owner" not in disputed.json()["allowed_actions"]

    to_self = api.put(
        f"{path}/owner",
        json={"user_id": _user_id(personas, "priya.raman"), "reason": "x"},
        headers=GOVERNANCE,
    )
    assert to_self.status_code == 400
    wrong_role = api.put(
        f"{path}/owner",
        json={"user_id": _user_id(personas, "lena.okafor"), "reason": "x"},
        headers=GOVERNANCE,
    )
    assert wrong_role.status_code == 400
    assert [a for a, _ in _audit(db_connection)] == [
        "asset.created",
        "asset.owner_assigned",
        "asset.owner_disputed",
    ]
    assert _audit(db_connection)[-1][1] == "This belongs to Finance."


def test_reassigning_resets_to_pending_with_the_reason(
    api: TestClient, database: Database, personas: dict[str, User], db_connection: Connection
) -> None:
    with database.transaction() as session:
        second = IdentityService(session).create_user(
            NewUser(
                "dee.owner",
                "Dee Owner",
                frozenset({Role.DATA_OWNER}),
                frozenset({domain_id(api, "customer")}),
            ),
            actor="test",
        )
    asset_id = _create(api)["id"]
    path = f"/api/v1/assets/{asset_id}/ownership"
    api.put(
        f"{path}/owner", json={"user_id": _user_id(personas, "priya.raman")}, headers=GOVERNANCE
    )
    api.post(f"{path}/owner/confirm", headers=DATA_OWNER)

    missing = api.put(f"{path}/owner", json={"user_id": str(second.id)}, headers=GOVERNANCE)
    assert missing.status_code == 400
    assert missing.json()["field"] == "reason"

    reassigned = api.put(
        f"{path}/owner",
        json={"user_id": str(second.id), "reason": "Priya moved to Finance."},
        headers=GOVERNANCE,
    )

    owner = reassigned.json()["data"]["owner"]
    assert (owner["user"]["display_name"], owner["status"]) == ("Dee Owner", "pending")
    assert owner["reason"] == "Priya moved to Finance."
    assert api.get("/api/v1/inbox", headers=DATA_OWNER).json()["data"] == []
    assert api.get("/api/v1/inbox", headers={DEV_USER_HEADER: "dee.owner"}).json()["data"]
    assert _audit(db_connection)[-1] == ("asset.owner_reassigned", "Priya moved to Finance.")


def test_only_data_owners_and_governance_name_stewards(
    api: TestClient, personas: dict[str, User]
) -> None:
    asset_id = _create(api)["id"]
    path = f"/api/v1/assets/{asset_id}/ownership/steward"
    body = {"user_id": _user_id(personas, "lena.okafor")}

    assert api.put(path, json=body, headers=APP_OWNER).status_code == 403
    assigned = api.put(path, json=body, headers=DATA_OWNER)
    assert assigned.json()["data"]["steward"]["user"]["display_name"] == "Lena Okafor"
    assert api.get("/api/v1/inbox", headers=STEWARD).json()["data"][0]["title"] == (
        "Confirm you are the Data Steward of Customer master"
    )
