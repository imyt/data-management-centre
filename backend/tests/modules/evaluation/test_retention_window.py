import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError

from app.core.db import Database
from app.modules.connectors.service import ConnectorsService
from app.modules.evaluation.domain import Trigger
from app.modules.evaluation.service import EvaluationService
from app.modules.policy.service import PolicyService

from .conftest import (
    APP_OWNER,
    AUDITOR,
    DATA_OWNER,
    GOVERNANCE,
    NOW,
    PROCESS_OWNER,
    STEWARD,
    Clock,
    FakeStore,
    Settle,
    reference,
)


def _store_id(client: TestClient, code: str = "SHOP") -> str:
    eu = reference(client, "regions", "eu")
    app = client.post(
        "/api/v1/applications",
        headers=APP_OWNER,
        json={
            "name": f"App {code}",
            "code": code,
            "domain_id": reference(client, "domains", "customer"),
            "criticality": "high",
            "hosting": "private_cloud",
        },
    ).json()["data"]
    environment = client.post(
        f"/api/v1/applications/{app['id']}/environments",
        headers=APP_OWNER,
        json={"name": "Production", "type": "production", "region_id": eu},
    ).json()["data"]
    created = client.post(
        f"/api/v1/environments/{environment['id']}/data-stores",
        headers=APP_OWNER,
        json={
            "name": "estate",
            "type": "relational",
            "platform": "PostgreSQL 18",
            "region_id": eu,
            "connection_ref": "env:DMC_ESTATE_HARVEST_URL",
        },
    )
    assert created.status_code == 201, created.text
    return created.json()["data"]["id"]


def _harvest(database: Database, store_id: str) -> None:
    with database.transaction() as session:
        ConnectorsService(session).run_harvest(uuid.UUID(store_id), requested_by=None)


def _control(client: TestClient) -> dict:
    policy = client.post(
        "/api/v1/policies",
        json={"code": "RET", "name": "Retention", "statement": "Keep data no longer than needed."},
        headers=GOVERNANCE,
    ).json()["data"]
    response = client.post(
        "/api/v1/controls",
        json={
            "policy_id": policy["id"],
            "code": "RET-01",
            "name": "Delete at end of retention",
            "rule_type": "retention_window",
            "params": {"grace_days": 0},
            "selector": {"subject": "asset", "where": {"is_stored": True}},
        },
        headers=GOVERNANCE,
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _asset_from_table(client: TestClient, store_id: str, retention: str = "r1y") -> dict:
    """A stored asset for `public.customers`, mapped to its table."""
    response = client.post(
        f"/api/v1/data-stores/{store_id}/mappings/assets",
        headers=GOVERNANCE,
        json={
            "paths": ["public.customers"],
            "retention_policy_id": reference(client, "retention-policies", retention),
            "data_category_id": reference(client, "data-categories", "personal"),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"][0]


def _stored_asset(client: TestClient, retention: str = "r1y") -> dict:
    """A stored asset that no table is mapped to."""
    response = client.post(
        "/api/v1/assets",
        headers=GOVERNANCE,
        json={
            "name": "Loose export",
            "domain_id": reference(client, "domains", "customer"),
            "is_stored": True,
            "retention_policy_id": reference(client, "retention-policies", retention),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


class Estate:
    """A harvested store with one mapped stored asset and the RET-01 control applied to it."""

    def __init__(
        self, client: TestClient, database: Database, settle: Settle, clock: Clock
    ) -> None:
        self.client, self.database, self.settle, self.clock = client, database, settle, clock
        self.store_id = _store_id(client)
        _harvest(database, self.store_id)
        self.asset = _asset_from_table(client, self.store_id)
        self.control = _control(client)
        settle()
        self.applied = self.applied_control_id()

    def applied_control_id(self) -> str:
        response = self.client.get("/api/v1/applied-controls", headers=GOVERNANCE).json()
        [applied] = [a for a in response["data"] if a["control"]["code"] == "RET-01"]
        return applied["id"]

    def run(self, at: datetime | None = None) -> dict[str, int]:
        """Evaluate now (moving the clock to `at` first, if given)."""
        if at is not None:
            self.clock.now = at
        with self.database.transaction() as session:
            summary = EvaluationService(session).run(
                [uuid.UUID(self.applied)], Trigger.ON_DEMAND, requested_by=None
            )
        return summary.counts

    def results(self, *, latest_only: bool = True, headers: dict[str, str] = GOVERNANCE) -> list:
        response = self.client.get(
            "/api/v1/evaluation-results",
            params={"applied_control_id": self.applied, "latest_only": latest_only},
            headers=headers,
        )
        assert response.status_code == 200, response.text
        return response.json()["data"]


@pytest.fixture
def estate(api: TestClient, database: Database, settle: Settle, clock: Clock) -> Estate:
    return Estate(api, database, settle, clock)


# --- The exit criterion: a failing result with everything to explain it


def test_rows_older_than_the_retention_policy_give_a_failing_result_with_its_evidence(
    estate: Estate, store: FakeStore
) -> None:
    store.oldest = NOW - timedelta(days=400)  # the asset's retention policy keeps data 365 days
    estate.run()

    [result] = estate.results()
    assert result["outcome"] == "fail"
    assert result["measured"] == 400 and result["threshold"] == 365 and result["unit"] == "days"
    assert "400 days old, 35 days past" in result["reason"]
    assert "public.customers" in result["reason"]
    assert result["control"] == {
        "id": estate.control["id"],
        "code": "RET-01",
        "rule_type": "retention_window",
        "rule_version": 1,
    }
    facts = result["facts"]
    assert facts["retention"] == {
        "is_stored": True,
        "policy_code": "r1y",
        "policy_name": "1 year",
        "days": 365,
    }
    assert facts["table"]["path"] == "public.customers"
    assert facts["table"]["column"] == "created_at"  # preferred over last_login_at
    assert facts["table"]["oldest_record_at"] == store.oldest.isoformat()
    assert facts["table"]["harvest_snapshot_id"]
    assert datetime.fromisoformat(result["evaluated_at"]) == NOW
    assert datetime.fromisoformat(result["stale_after"]) == NOW + timedelta(hours=48)
    assert store.asked[-1] == ("public", "customers", "created_at")

    detail = estate.client.get(f"/api/v1/evaluation-results/{result['id']}", headers=GOVERNANCE)
    assert detail.json()["meta"]["stale_after"] == result["stale_after"]


def test_records_within_the_window_pass_and_one_day_past_it_fails(
    estate: Estate, store: FakeStore
) -> None:
    store.oldest = NOW - timedelta(days=300)
    estate.run()
    assert [r["outcome"] for r in estate.results()] == ["pass"]

    store.oldest = NOW - timedelta(days=365)  # exactly the window: not past it
    estate.run()
    assert [r["outcome"] for r in estate.results()] == ["pass"]

    store.oldest = NOW - timedelta(days=366)
    estate.run()
    assert [r["outcome"] for r in estate.results()] == ["fail"]


def test_an_empty_table_passes(estate: Estate, store: FakeStore) -> None:
    store.oldest = None
    estate.run()
    [result] = estate.results()
    assert result["outcome"] == "pass" and result["measured"] == 0


# --- Idempotency and history


def test_evaluating_the_same_facts_again_writes_nothing(estate: Estate, store: FakeStore) -> None:
    store.oldest = NOW - timedelta(days=400)
    first = estate.run()
    again = estate.run()
    third = estate.run()

    assert first["written"] == 1 and first["unchanged"] == 0
    assert again["written"] == 0 and again["unchanged"] == 1
    assert third["written"] == 0
    # The result of the worker's own evaluation when the control was applied, and this one.
    assert len(estate.results(latest_only=False)) == 2


def test_a_new_day_or_changed_facts_write_a_new_result_linked_to_the_last(
    estate: Estate, store: FakeStore
) -> None:
    [baseline] = estate.results()  # written by the worker when the control was applied
    assert baseline["transition"] == "first"

    estate.run(NOW + timedelta(days=1))  # same facts, but the age moved on a day
    [second] = estate.results()
    assert second["id"] != baseline["id"]
    assert second["previous_result_id"] == baseline["id"]
    assert second["transition"] == "unchanged"

    store.oldest = NOW - timedelta(days=20)  # the oldest rows were deleted
    estate.run()
    [third] = estate.results()
    assert third["outcome"] == "pass" and third["transition"] == "fail_to_pass"

    history = estate.results(latest_only=False)
    assert [r["id"] for r in history] == [third["id"], second["id"], baseline["id"]]


def test_facts_that_return_to_an_earlier_state_still_write_a_result(
    estate: Estate, store: FakeStore
) -> None:
    store.oldest = NOW - timedelta(days=400)
    estate.run()
    store.oldest = NOW - timedelta(days=10)
    estate.run()
    store.oldest = NOW - timedelta(days=400)
    estate.run()

    results = estate.results(latest_only=False)
    assert [r["outcome"] for r in results] == ["fail", "pass", "fail", "fail"]
    assert [r["transition"] for r in results] == [
        "pass_to_fail",
        "fail_to_pass",
        "unchanged",
        "first",
    ]
    assert estate.results()[0]["id"] == results[0]["id"]


def test_a_new_rule_version_is_judged_afresh(estate: Estate, store: FakeStore) -> None:
    store.oldest = NOW - timedelta(days=400)
    estate.run()
    assert estate.results()[0]["outcome"] == "fail"

    published = estate.client.post(
        f"/api/v1/controls/{estate.control['id']}/rule-versions",
        headers=GOVERNANCE,
        json={
            "params": {"grace_days": 60},
            "selector": {"subject": "asset", "where": {"is_stored": True}},
            "reason": "Deletion runs monthly, so allow two months.",
        },
    )
    assert published.status_code == 201, published.text
    estate.settle()  # re-derives the applied control, which asks for an evaluation

    [latest] = estate.results()
    assert latest["control"]["rule_version"] == 2
    assert latest["outcome"] == "pass" and latest["threshold"] == 425
    assert latest["transition"] == "fail_to_pass"


# --- error is not fail


def test_a_rule_that_cannot_be_evaluated_is_an_error_not_a_failure(
    api: TestClient, database: Database, settle: Settle
) -> None:
    asset = _stored_asset(api)
    _control(api)
    settle()
    with database.transaction() as session:
        ids = [r.id for r in PolicyService(session).active_applied_controls()]
        summary = EvaluationService(session).run(ids, Trigger.ON_DEMAND, requested_by=None)
    [result] = api.get(
        "/api/v1/evaluation-results",
        params={"subject_id": asset["id"], "latest_only": False},
        headers=GOVERNANCE,
    ).json()["data"][:1]

    assert "fail" not in summary.counts
    assert result["outcome"] == "error"
    assert result["measured"] is None and result["threshold"] is None
    assert "No table is mapped" in result["reason"]
    failing = api.get(
        "/api/v1/evaluation-results", params={"outcome": "fail"}, headers=GOVERNANCE
    ).json()["data"]
    assert failing == []


def test_an_unreachable_store_is_an_error_with_the_reason_and_not_repeated_within_a_day(
    estate: Estate, store: FakeStore
) -> None:
    store.error = "connection refused"
    estate.run()
    estate.run()

    [result] = estate.results()
    assert result["outcome"] == "error"
    assert result["reason"] == "connection refused"
    # The worker's own result, and one error: the second run found the same facts.
    assert len(estate.results(latest_only=False)) == 2

    store.error = None
    estate.run()  # the store is back: a real verdict follows the error
    [latest] = estate.results()
    assert latest["outcome"] == "fail" and latest["transition"] == "error_to_fail"


def test_an_unexpected_failure_is_an_error_without_the_internals(
    estate: Estate, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_: object) -> None:
        raise RuntimeError("secret internals")

    monkeypatch.setattr(FakeStore, "oldest_record", boom)
    estate.run()

    [result] = estate.results()
    assert result["outcome"] == "error"
    assert "secret" not in result["reason"]


# --- Freshness


def test_a_result_is_flagged_stale_once_its_window_has_passed(estate: Estate, clock: Clock) -> None:
    [result] = estate.results()
    assert result["is_stale"] is False

    clock.now = NOW + timedelta(hours=47)
    assert estate.results()[0]["is_stale"] is False
    clock.now = NOW + timedelta(hours=48)
    assert estate.results()[0]["is_stale"] is True

    estate.run()  # evaluating again the next day gives a fresh result
    [fresh] = estate.results()
    assert fresh["is_stale"] is False and fresh["id"] != result["id"]


# --- Append-only


def test_results_cannot_be_updated_or_deleted(estate: Estate, db_connection: Connection) -> None:
    estate.run()
    for statement in (
        "UPDATE evaluation.evaluation_result SET outcome = 'pass'",
        "DELETE FROM evaluation.evaluation_result",
    ):
        with pytest.raises(DBAPIError, match="append-only"), db_connection.begin_nested():
            db_connection.execute(text(statement))
    assert len(estate.results(latest_only=False)) == 1


# --- Events, requests, permissions


def test_a_new_applied_control_and_a_new_harvest_trigger_evaluations(
    estate: Estate, database: Database, store: FakeStore
) -> None:
    # `Estate` settled the worker: the control was derived and evaluated without any request.
    [first] = estate.results(latest_only=False)
    with database.transaction() as session:
        triggers = (
            session.execute(text("SELECT trigger FROM evaluation.evaluation_run ORDER BY id"))
            .scalars()
            .all()
        )
    assert triggers[0] == "event"
    assert first["outcome"] == "fail"  # the fake store's oldest record is 500 days old

    store.oldest = NOW - timedelta(days=10)
    _harvest(database, estate.store_id)
    estate.settle()  # the harvest event queues an evaluation of the assets stored in the store
    assert estate.results()[0]["outcome"] == "pass"
    assert len(estate.results(latest_only=False)) == 2


def test_changing_an_assets_retention_policy_evaluates_it_again(
    estate: Estate, store: FakeStore
) -> None:
    store.oldest = NOW - timedelta(days=100)
    estate.run()
    assert estate.results()[0]["outcome"] == "pass"

    patched = estate.client.patch(
        f"/api/v1/assets/{estate.asset['asset_id']}",
        headers=GOVERNANCE,
        json={"retention_policy_id": reference(estate.client, "retention-policies", "r30d")},
    )
    assert patched.status_code == 200, patched.text
    estate.settle()

    [latest] = estate.results()
    assert latest["outcome"] == "fail" and latest["threshold"] == 30


def test_running_an_evaluation_on_demand_is_queued_audited_and_run_by_the_worker(
    estate: Estate, db_connection: Connection
) -> None:
    response = estate.client.post(
        "/api/v1/evaluations", json={"applied_control_id": estate.applied}, headers=DATA_OWNER
    )
    assert response.status_code == 202, response.text
    assert response.headers["location"].startswith("/api/v1/jobs/")

    audited = db_connection.execute(
        text("SELECT actor FROM audit.audit_event WHERE action = 'evaluation.requested'")
    ).all()
    assert len(audited) == 1

    estate.settle()
    runs = db_connection.execute(
        text("SELECT requested_by FROM evaluation.evaluation_run WHERE trigger = 'on_demand'")
    ).all()
    assert len(runs) == 1 and runs[0].requested_by.startswith("user:")

    by_subject = estate.client.post(
        "/api/v1/evaluations",
        json={"subject_type": "asset", "subject_id": estate.asset["asset_id"]},
        headers=GOVERNANCE,
    )
    assert by_subject.status_code == 202


@pytest.mark.parametrize(
    ("headers", "status"), [(AUDITOR, 403), (PROCESS_OWNER, 403), (APP_OWNER, 202), (STEWARD, 202)]
)
def test_only_those_who_answer_for_the_subject_may_run_an_evaluation(
    estate: Estate, headers: dict[str, str], status: int
) -> None:
    response = estate.client.post(
        "/api/v1/evaluations", json={"applied_control_id": estate.applied}, headers=headers
    )
    assert response.status_code == status, response.text


def test_the_run_action_is_offered_where_it_would_be_allowed(estate: Estate) -> None:
    def actions(headers: dict[str, str]) -> list[str]:
        return estate.client.get(
            "/api/v1/evaluation-results",
            params={"subject_type": "asset", "subject_id": estate.asset["asset_id"]},
            headers=headers,
        ).json()["allowed_actions"]

    assert actions(DATA_OWNER) == ["run_evaluation"]
    assert actions(AUDITOR) == []
    # A list that is not about one subject offers nothing.
    wide = estate.client.get("/api/v1/evaluation-results", headers=GOVERNANCE).json()
    assert wide["allowed_actions"] == []


def test_results_are_hidden_from_those_outside_the_subjects_domain(estate: Estate) -> None:
    assert len(estate.results()) == 1
    assert estate.results(headers=PROCESS_OWNER) == []
    [result] = estate.results()
    forbidden = estate.client.get(
        f"/api/v1/evaluation-results/{result['id']}", headers=PROCESS_OWNER
    )
    assert forbidden.status_code == 403


def test_unknown_targets_are_refused(estate: Estate) -> None:
    missing = estate.client.post(
        "/api/v1/evaluations", json={"applied_control_id": str(uuid.uuid4())}, headers=GOVERNANCE
    )
    both = estate.client.post(
        "/api/v1/evaluations",
        json={"applied_control_id": estate.applied, "subject_type": "asset"},
        headers=GOVERNANCE,
    )
    neither = estate.client.post("/api/v1/evaluations", json={}, headers=GOVERNANCE)
    assert (missing.status_code, both.status_code, neither.status_code) == (404, 400, 400)


def test_the_scheduled_sweep_queues_every_applied_control(
    estate: Estate, database: Database
) -> None:
    with database.transaction() as session:
        queued = EvaluationService(session).sweep(job_id=uuid.uuid4())
    assert queued == 1
