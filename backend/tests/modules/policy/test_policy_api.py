import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError

from app.core.auth import DEV_USER_HEADER

GOVERNANCE = {DEV_USER_HEADER: "hannah.becker"}
DATA_OWNER = {DEV_USER_HEADER: "priya.raman"}
AUDITOR = {DEV_USER_HEADER: "sofia.marin"}

STORED = {"subject": "asset", "where": {"is_stored": True}}


def _policy(client: TestClient, code: str = "RET", **overrides: object) -> dict:
    response = client.post(
        "/api/v1/policies",
        json={"code": code, "name": "Retention", "statement": "Keep data no longer than needed."}
        | overrides,
        headers=GOVERNANCE,
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _control(client: TestClient, policy_id: str, code: str = "RET-01", **overrides: object) -> dict:
    body = {
        "policy_id": policy_id,
        "code": code,
        "name": "Delete at end of retention",
        "rule_type": "retention_window",
        "selector": STORED,
    } | overrides
    response = client.post("/api/v1/controls", json=body, headers=GOVERNANCE)
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _audit(connection: Connection, subject_type: str) -> list[tuple[str, str | None]]:
    rows = connection.execute(
        text("SELECT action, reason FROM audit.audit_event WHERE subject_type = :t ORDER BY seq"),
        {"t": subject_type},
    )
    return [(row.action, row.reason) for row in rows]


def test_governance_adds_a_policy_and_a_control_with_a_first_rule_version(
    api: TestClient, db_connection: Connection
) -> None:
    policy = _policy(api)
    control = _control(api, policy["id"], params={"grace_days": 3})

    assert policy["control_count"] == 0
    assert control["status"] == "active"
    assert control["subject_type"] == "asset"
    assert control["rule_type_label"] == "Retention window"
    assert control["current_version"]["version"] == 1
    assert control["current_version"]["params"] == {"grace_days": 3}
    [condition] = control["current_version"]["conditions"]
    assert condition["text"] == "Stored is yes"
    assert [v["version"] for v in control["versions"]] == [1]
    assert _audit(db_connection, "policy") == [("policy.created", None)]
    assert _audit(db_connection, "control") == [("control.created", None)]
    assert (
        api.get(f"/api/v1/policies/{policy['id']}", headers=GOVERNANCE).json()["data"][
            "control_count"
        ]
        == 1
    )


def test_everyone_signed_in_reads_the_library_but_only_governance_changes_it(
    api: TestClient,
) -> None:
    policy = _policy(api)
    control = _control(api, policy["id"])

    listed = api.get("/api/v1/controls", headers=DATA_OWNER).json()
    assert [c["code"] for c in listed["data"]] == ["RET-01"]
    assert listed["allowed_actions"] == []
    assert api.get("/api/v1/controls", headers=GOVERNANCE).json()["allowed_actions"] == [
        "create_control"
    ]
    detail = api.get(f"/api/v1/controls/{control['id']}", headers=DATA_OWNER).json()
    assert detail["allowed_actions"] == []
    assert api.get(f"/api/v1/controls/{control['id']}", headers=GOVERNANCE).json()[
        "allowed_actions"
    ] == ["edit", "publish_rule_version", "recompute", "retire"]

    denied = [
        api.post("/api/v1/policies", json={"code": "X1", "name": "x", "statement": "x"}, headers=h)
        for h in (DATA_OWNER, AUDITOR)
    ]
    assert [r.status_code for r in denied] == [403, 403]
    publish = api.post(
        f"/api/v1/controls/{control['id']}/rule-versions",
        json={"selector": STORED, "params": {"grace_days": 1}, "reason": "Needs time"},
        headers=DATA_OWNER,
    )
    assert publish.status_code == 403


def test_a_selector_can_only_use_attributes(api: TestClient) -> None:
    policy = _policy(api)

    named = api.post(
        "/api/v1/controls",
        json={
            "policy_id": policy["id"],
            "code": "RET-02",
            "name": "x",
            "rule_type": "retention_window",
            "selector": {"subject": "asset", "where": {"name": "Customer master"}},
        },
        headers=GOVERNANCE,
    )
    wrong_subject = api.post(
        "/api/v1/controls",
        json={
            "policy_id": policy["id"],
            "code": "RET-03",
            "name": "x",
            "rule_type": "retention_window",
            "selector": {"subject": "application", "where": {}},
        },
        headers=GOVERNANCE,
    )

    assert named.status_code == 400
    assert named.json()["attribute"] == "name"
    assert wrong_subject.status_code == 400
    assert wrong_subject.json()["field"] == "selector.subject"


def test_codes_are_unique(api: TestClient) -> None:
    policy = _policy(api)
    _control(api, policy["id"])

    duplicate_policy = api.post(
        "/api/v1/policies",
        json={"code": "RET", "name": "Again", "statement": "x"},
        headers=GOVERNANCE,
    )
    duplicate_control = api.post(
        "/api/v1/controls",
        json={
            "policy_id": policy["id"],
            "code": "RET-01",
            "name": "x",
            "rule_type": "retention_window",
            "selector": STORED,
        },
        headers=GOVERNANCE,
    )

    assert duplicate_policy.status_code == 409
    assert duplicate_control.status_code == 409


def test_a_new_rule_version_needs_a_reason_and_keeps_the_old_one(
    api: TestClient, db_connection: Connection
) -> None:
    control = _control(api, _policy(api)["id"])
    url = f"/api/v1/controls/{control['id']}/rule-versions"
    body = {"selector": STORED, "params": {"grace_days": 30}}

    assert api.post(url, json=body, headers=GOVERNANCE).status_code == 422
    assert api.post(url, json={**body, "reason": "  "}, headers=GOVERNANCE).status_code == 422

    published = api.post(
        url, json={**body, "reason": "Legal agreed a grace period"}, headers=GOVERNANCE
    )
    assert published.status_code == 201
    data = published.json()["data"]
    assert data["current_version"]["version"] == 2
    assert data["current_version"]["params"] == {"grace_days": 30}
    assert data["current_version"]["change_reason"] == "Legal agreed a grace period"
    assert [(v["version"], v["params"]) for v in data["versions"]] == [
        (2, {"grace_days": 30}),
        (1, {"grace_days": 0}),
    ]
    assert ("rule_version.published", "Legal agreed a grace period") in _audit(
        db_connection, "control"
    )

    same = api.post(url, json={**body, "reason": "Again"}, headers=GOVERNANCE)
    assert same.status_code == 409


def test_a_rule_version_cannot_be_changed_afterwards(
    api: TestClient, db_connection: Connection
) -> None:
    _control(api, _policy(api)["id"])

    with pytest.raises(DBAPIError, match="immutable"), db_connection.begin_nested():
        db_connection.execute(text("UPDATE policy.rule_version SET params = '{}'"))
    with pytest.raises(DBAPIError, match="immutable"), db_connection.begin_nested():
        db_connection.execute(text("DELETE FROM policy.rule_version"))


def test_retiring_a_control_needs_a_reason_and_stops_further_changes(
    api: TestClient, db_connection: Connection
) -> None:
    control = _control(api, _policy(api)["id"])
    url = f"/api/v1/controls/{control['id']}/retire"

    assert api.post(url, json={}, headers=GOVERNANCE).status_code == 422
    retired = api.post(url, json={"reason": "Superseded by RET-02"}, headers=GOVERNANCE)

    assert retired.status_code == 200
    assert retired.json()["data"]["status"] == "retired"
    assert retired.json()["data"]["retired_reason"] == "Superseded by RET-02"
    assert retired.json()["allowed_actions"] == []
    assert ("control.retired", "Superseded by RET-02") in _audit(db_connection, "control")
    again = api.post(url, json={"reason": "x"}, headers=GOVERNANCE)
    edit = api.patch(f"/api/v1/controls/{control['id']}", json={"name": "New"}, headers=GOVERNANCE)
    assert (again.status_code, edit.status_code) == (409, 409)


def test_edit_a_policy_and_a_control_and_audit_what_changed(
    api: TestClient, db_connection: Connection
) -> None:
    policy = _policy(api)
    control = _control(api, policy["id"])

    updated = api.patch(
        f"/api/v1/policies/{policy['id']}", json={"name": "Data retention"}, headers=GOVERNANCE
    )
    edited = api.patch(
        f"/api/v1/controls/{control['id']}",
        json={"evidence_requirement": "A deletion log"},
        headers=GOVERNANCE,
    )

    assert updated.json()["data"]["name"] == "Data retention"
    assert edited.json()["data"]["evidence_requirement"] == "A deletion log"
    assert ("policy.updated", None) in _audit(db_connection, "policy")
    assert ("control.updated", None) in _audit(db_connection, "control")


def test_the_vocabulary_lists_rule_types_and_attributes(api: TestClient) -> None:
    data = api.get("/api/v1/policy/vocabulary", headers=DATA_OWNER).json()["data"]

    assert {t["key"] for t in data["rule_types"]} >= {"retention_window", "harvest_fresh"}
    asset = next(s for s in data["subject_types"] if s["type"] == "asset")
    attributes = {a["name"]: a for a in asset["attributes"]}
    assert "name" not in attributes and "id" not in attributes
    assert attributes["is_stored"]["kind"] == "boolean"
    assert {o["value"] for o in attributes["data_category"]["options"]} >= {"personal"}


def test_previewing_a_selector_counts_what_it_matches(api: TestClient) -> None:
    preview = api.post(
        "/api/v1/controls/preview-selector",
        json={"selector": {"subject": "asset", "where": {"is_stored": True}}},
        headers=GOVERNANCE,
    )

    assert preview.status_code == 200
    assert preview.json()["data"]["count"] <= preview.json()["data"]["total"]
