import uuid
from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy import Connection, text

from app.core.auth import DEV_USER_HEADER
from app.modules.identity.service import User

GOVERNANCE = {DEV_USER_HEADER: "hannah.becker"}
DATA_OWNER = {DEV_USER_HEADER: "priya.raman"}  # Customer only

Settle = Callable[[], None]


def _ref(client: TestClient, path: str, code: str) -> str:
    items = client.get(f"/api/v1/reference/{path}", headers=GOVERNANCE).json()["data"]
    return next(item["id"] for item in items if item["code"] == code)


def _control(client: TestClient, code: str = "RET-01", **overrides: object) -> dict:
    policy = client.post(
        "/api/v1/policies",
        json={"code": "RET", "name": "Retention", "statement": "Keep data no longer than needed."},
        headers=GOVERNANCE,
    ).json()["data"]
    body = {
        "policy_id": policy["id"],
        "code": code,
        "name": "Delete at end of retention",
        "rule_type": "retention_window",
        "selector": {
            "subject": "asset",
            "where": {"is_stored": True, "data_category.in": ["personal", "payment"]},
        },
    } | overrides
    response = client.post("/api/v1/controls", json=body, headers=GOVERNANCE)
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _asset(client: TestClient, name: str, category: str, *, domain: str = "customer") -> dict:
    retention = client.get("/api/v1/reference/retention-policies", headers=GOVERNANCE).json()[
        "data"
    ][0]["id"]
    response = client.post(
        "/api/v1/assets",
        json={
            "name": name,
            "domain_id": _ref(client, "domains", domain),
            "data_category_id": _ref(client, "data-categories", category),
            "is_stored": True,
            "retention_policy_id": retention,
        },
        headers=GOVERNANCE,
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _applied(client: TestClient, headers: dict[str, str] = GOVERNANCE, **query: str) -> list[dict]:
    response = client.get("/api/v1/applied-controls", params=query, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_a_new_control_is_applied_to_every_matching_asset_with_a_reason(
    api: TestClient, settle: Settle
) -> None:
    matching = _asset(api, "Customer master", "personal")
    _asset(api, "Marketing copy", "operational")
    control = _control(api)
    settle()

    [applied] = _applied(api, control_id=control["id"])

    assert applied["subject"] == {"type": "asset", "id": matching["id"], "name": "Customer master"}
    assert applied["status"] == "active"
    assert applied["rule_version"] == 1
    assert applied["reason"] == (
        "Applies because Data category is one of Payment, Personal (it is Personal); Stored is yes."
    )
    assert applied["derived_from"]["attributes"] == {"data_category": "personal", "is_stored": True}
    detail = api.get(f"/api/v1/applied-controls/{applied['id']}", headers=GOVERNANCE).json()
    assert detail["data"]["reason"] == applied["reason"]
    count = api.get(f"/api/v1/controls/{control['id']}", headers=GOVERNANCE).json()["data"]
    assert count["applied_count"] == 1


def test_a_new_asset_inherits_the_control_without_naming_it(
    api: TestClient, settle: Settle
) -> None:
    control = _control(api)
    settle()
    assert _applied(api, control_id=control["id"]) == []

    asset = _asset(api, "Payment ledger", "payment")
    settle()

    [applied] = _applied(api, control_id=control["id"])
    assert applied["subject"]["id"] == asset["id"]


def test_changing_an_attribute_retires_the_applied_control_and_keeps_its_history(
    api: TestClient, settle: Settle, db_connection: Connection
) -> None:
    control = _control(api)
    asset = _asset(api, "Customer master", "personal")
    settle()
    [applied] = _applied(api, control_id=control["id"])

    api.patch(
        f"/api/v1/assets/{asset['id']}",
        json={"data_category_id": _ref(api, "data-categories", "operational")},
        headers=GOVERNANCE,
    )
    settle()

    assert _applied(api, control_id=control["id"]) == []
    [retired] = _applied(api, control_id=control["id"], status="retired")
    assert retired["id"] == applied["id"]
    assert retired["retired_reason"] == (
        "No longer applies: Data category is one of Payment, Personal is required but it is "
        "Operational."
    )
    assert retired["retired_at"] is not None
    audit = (
        db_connection.execute(
            text(
                "SELECT action FROM audit.audit_event WHERE subject_type = 'applied_control' "
                "AND subject_id = :id ORDER BY seq"
            ),
            {"id": applied["id"]},
        )
        .scalars()
        .all()
    )
    assert audit == ["applied_control.derived", "applied_control.retired"]

    # Becoming personal again applies the control anew; the retired row stays as history.
    api.patch(
        f"/api/v1/assets/{asset['id']}",
        json={"data_category_id": _ref(api, "data-categories", "personal")},
        headers=GOVERNANCE,
    )
    settle()
    [again] = _applied(api, control_id=control["id"])
    assert again["id"] != applied["id"]
    assert len(_applied(api, control_id=control["id"], status="retired")) == 1


def test_flagging_a_personal_data_element_applies_a_pii_control(
    api: TestClient, settle: Settle
) -> None:
    control = _control(
        api,
        code="KNOW-02",
        rule_type="declaration_complete",
        selector={"subject": "asset", "where": {"contains_pii": True}},
    )
    asset = _asset(api, "Customer master", "personal")
    settle()
    assert _applied(api, control_id=control["id"]) == []

    added = api.post(
        f"/api/v1/assets/{asset['id']}/data-elements",
        json={"name": "email", "data_type": "text", "is_pii": True},
        headers=GOVERNANCE,
    )
    assert added.status_code == 201, added.text
    settle()

    assert len(_applied(api, control_id=control["id"])) == 1


def test_a_new_rule_version_recomputes_the_applied_controls(
    api: TestClient, settle: Settle
) -> None:
    control = _control(api)
    _asset(api, "Customer master", "personal")
    internal = _asset(api, "Marketing copy", "operational")
    settle()
    assert len(_applied(api, control_id=control["id"])) == 1

    published = api.post(
        f"/api/v1/controls/{control['id']}/rule-versions",
        json={
            "selector": {"subject": "asset", "where": {"is_stored": True}},
            "params": {"grace_days": 0},
            "reason": "Retention applies to every stored asset",
        },
        headers=GOVERNANCE,
    )
    assert published.status_code == 201
    settle()

    applied = _applied(api, control_id=control["id"])
    assert len(applied) == 2
    assert {a["rule_version"] for a in applied} == {2}
    assert internal["id"] in {a["subject"]["id"] for a in applied}


def test_retiring_a_control_retires_its_applied_controls(api: TestClient, settle: Settle) -> None:
    control = _control(api)
    _asset(api, "Customer master", "personal")
    settle()

    api.post(
        f"/api/v1/controls/{control['id']}/retire",
        json={"reason": "Replaced"},
        headers=GOVERNANCE,
    )
    settle()

    assert _applied(api, control_id=control["id"]) == []
    [retired] = _applied(api, control_id=control["id"], status="retired")
    assert retired["retired_reason"] == "The control was retired: Replaced"


def test_applied_controls_name_who_is_accountable_and_responsible(
    api: TestClient, settle: Settle, personas: dict[str, User]
) -> None:
    control = _control(api)
    asset = _asset(api, "Customer master", "personal")
    assigned = api.put(
        f"/api/v1/assets/{asset['id']}/ownership/owner",
        json={"user_id": str(personas["priya.raman"].id)},
        headers=GOVERNANCE,
    )
    assert assigned.status_code == 200, assigned.text
    settle()

    [applied] = _applied(api, control_id=control["id"])

    assert applied["accountable"]["display_name"] == "Priya Raman"
    assert applied["responsible"] is None


def test_applied_controls_are_filtered_to_the_callers_domains(
    api: TestClient, settle: Settle
) -> None:
    control = _control(api)
    _asset(api, "Customer master", "personal")
    finance = _asset(api, "Ledger", "payment", domain="finance")
    settle()

    everything = _applied(api, control_id=control["id"])
    customer_only = _applied(api, DATA_OWNER, control_id=control["id"])

    assert len(everything) == 2
    assert [a["subject"]["name"] for a in customer_only] == ["Customer master"]
    finance_applied = next(a for a in everything if a["subject"]["id"] == finance["id"])
    outside = api.get(f"/api/v1/applied-controls/{finance_applied['id']}", headers=DATA_OWNER)
    assert outside.status_code == 403


def test_recomputing_twice_changes_nothing(api: TestClient, settle: Settle) -> None:
    control = _control(api)
    _asset(api, "Customer master", "personal")
    settle()
    before = _applied(api, control_id=control["id"])

    response = api.post(f"/api/v1/controls/{control['id']}/recompute", headers=GOVERNANCE)
    settle()

    assert response.status_code == 202
    assert uuid.UUID(response.json()["data"]["id"])
    assert _applied(api, control_id=control["id"]) == before
