import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from app.core.auth import DEV_USER_HEADER
from app.core.db import Database
from app.core.jobs import JobContext
from app.core.outbox import Event
from app.modules.connectors import jobs
from app.modules.connectors.adapters import Catalog, HarvestedObject, HarvestError
from app.modules.connectors.domain import ObjectKind
from app.modules.connectors.service import ConnectorsService
from app.modules.identity.service import User

GOVERNANCE = {DEV_USER_HEADER: "hannah.becker"}
APP_OWNER = {DEV_USER_HEADER: "marcus.webb"}  # Customer and Finance
DATA_OWNER = {DEV_USER_HEADER: "priya.raman"}  # Customer only
STEWARD = {DEV_USER_HEADER: "lena.okafor"}
AUDITOR = {DEV_USER_HEADER: "sofia.marin"}

CATALOG = Catalog(
    [
        HarvestedObject(ObjectKind.SCHEMA, "public", "public"),
        HarvestedObject(ObjectKind.TABLE, "public.customers", "customers", "public", row_count=8),
        HarvestedObject(ObjectKind.TABLE, "public.orders", "orders", "public", row_count=10),
        HarvestedObject(
            ObjectKind.COLUMN, "public.customers.id", "id", "public.customers", 1, "bigint"
        ),
        HarvestedObject(
            ObjectKind.COLUMN, "public.customers.email", "email", "public.customers", 2, "text"
        ),
        HarvestedObject(ObjectKind.COLUMN, "public.orders.id", "id", "public.orders", 1, "bigint"),
    ]
)


class FakeAdapter:
    def __init__(self, error: str | None = None) -> None:
        self.error = error

    def harvest(self, connection_url: str) -> Catalog:
        if self.error:
            raise HarvestError(self.error)
        return CATALOG


@pytest.fixture(autouse=True)
def _resolvable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.modules.connectors.service.resolve_connection", lambda ref: "postgresql://fake/db"
    )


@pytest.fixture
def api(db_client: TestClient, personas: dict[str, User]) -> TestClient:
    return db_client


type Harvest = Callable[..., None]


@pytest.fixture
def harvest(database: Database) -> Iterator[Harvest]:
    """Run a harvest the way the worker does, in the test's transaction."""

    def run(store_id: str, adapter: FakeAdapter | None = None) -> None:
        with database.transaction() as session:
            ConnectorsService(session, adapter=adapter or FakeAdapter()).run_harvest(
                uuid.UUID(store_id), requested_by=None
            )

    yield run


def _ref(client: TestClient, path: str, code: str) -> str:
    items = client.get(f"/api/v1/reference/{path}", headers=GOVERNANCE).json()["data"]
    return next(item["id"] for item in items if item["code"] == code)


def _store(
    client: TestClient, domain: str = "customer", code: str = "SHOP", headers: dict = APP_OWNER
) -> str:
    """An application in `domain` with one PostgreSQL data store; returns the store id."""
    eu = _ref(client, "regions", "eu")
    app = client.post(
        "/api/v1/applications",
        headers=headers,
        json={
            "name": f"App {code}",
            "code": code,
            "domain_id": _ref(client, "domains", domain),
            "criticality": "high",
            "hosting": "private_cloud",
        },
    )
    assert app.status_code == 201, app.text
    environment = client.post(
        f"/api/v1/applications/{app.json()['data']['id']}/environments",
        headers=headers,
        json={"name": "Production", "type": "production", "region_id": eu},
    ).json()["data"]
    store = client.post(
        f"/api/v1/environments/{environment['id']}/data-stores",
        headers=headers,
        json={
            "name": "estate",
            "type": "relational",
            "platform": "PostgreSQL 18",
            "region_id": eu,
            "connection_ref": "env:DMC_ESTATE_HARVEST_URL",
        },
    )
    assert store.status_code == 201, store.text
    return store.json()["data"]["id"]


def _status(client: TestClient, store_id: str, headers: dict[str, str] = APP_OWNER) -> dict:
    response = client.get(f"/api/v1/data-stores/{store_id}/harvest", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _store_of_application(client: TestClient) -> dict:
    applications = client.get("/api/v1/applications", headers=APP_OWNER).json()["data"]
    detail = client.get(f"/api/v1/applications/{applications[0]['id']}", headers=APP_OWNER).json()
    return detail["data"]["environments"][0]["data_stores"][0]


def _audit(connection: Connection) -> list[str]:
    rows = connection.execute(
        text("SELECT action FROM audit.audit_event WHERE subject_type = 'data_store' ORDER BY seq")
    )
    return [row.action for row in rows]


def _retention_policy(client: TestClient) -> dict:
    return client.get("/api/v1/reference/retention-policies", headers=GOVERNANCE).json()["data"][0]


def test_a_store_that_was_never_harvested_has_no_run(api: TestClient) -> None:
    store_id = _store(api)
    body = _status(api, store_id)
    assert body["data"]["last_run"] is None
    assert body["data"]["objects"] is None
    assert body["data"]["recent_runs"] == []
    assert body["allowed_actions"] == ["map_objects", "run_harvest"]
    page = api.get(f"/api/v1/data-stores/{store_id}/objects", headers=APP_OWNER).json()
    assert page["data"] == []


def test_a_harvest_stores_a_snapshot_and_updates_the_store(
    api: TestClient, harvest: Harvest, db_connection: Connection
) -> None:
    store_id = _store(api)
    harvest(store_id)

    data = _status(api, store_id)["data"]
    assert data["last_run"]["status"] == "succeeded"
    assert (data["last_run"]["schemas"], data["last_run"]["tables"]) == (1, 2)
    assert data["last_run"]["columns"] == 3
    assert data["objects"] == {
        "schemas": 1,
        "tables": 2,
        "columns": 3,
        "unmapped_tables": 2,
        "unmapped_columns": 3,
    }

    store = _store_of_application(api)
    assert store["harvest_status"] == "succeeded"
    assert store["last_harvested_at"] is not None
    assert _audit(db_connection)[-1] == "data_store.harvested"


def test_a_failed_harvest_shows_why_and_keeps_the_last_good_objects(
    api: TestClient, harvest: Harvest, db_connection: Connection
) -> None:
    store_id = _store(api)
    harvest(store_id)
    harvest(store_id, FakeAdapter(error="password authentication failed for user dmc_harvest"))

    data = _status(api, store_id)["data"]
    assert data["last_run"]["status"] == "failed"
    assert "authentication failed" in data["last_run"]["error"]
    assert [r["status"] for r in data["recent_runs"]] == ["failed", "succeeded"]
    # The objects are still those of the last run that worked.
    assert data["objects"]["tables"] == 2
    assert _store_of_application(api)["harvest_status"] == "failed"
    assert _audit(db_connection)[-2:] == ["data_store.harvested", "data_store.harvest_failed"]


def test_a_store_with_no_adapter_fails_with_a_reason(api: TestClient, database: Database) -> None:
    store_id = _store(api)
    with database.transaction() as session:
        # No adapter override: the platform decides.
        session.execute(text("UPDATE inventory.data_store SET platform = 'Oracle 23'"))
        ConnectorsService(session).run_harvest(uuid.UUID(store_id), requested_by=None)
    last = _status(api, store_id)["data"]["last_run"]
    assert last["status"] == "failed"
    assert "no harvest adapter" in last["error"]


def test_unmapped_objects_are_listed_and_filtered(api: TestClient, harvest: Harvest) -> None:
    store_id = _store(api)
    harvest(store_id)
    tables = api.get(
        f"/api/v1/data-stores/{store_id}/objects?kind=table&mapped=false", headers=APP_OWNER
    ).json()
    assert [o["path"] for o in tables["data"]] == ["public.customers", "public.orders"]
    assert tables["meta"]["total"] == 2
    assert tables["data"][0]["mapping"] is None
    assert tables["data"][0]["row_count"] == 8

    columns = api.get(
        f"/api/v1/data-stores/{store_id}/objects?parent_path=public.customers", headers=APP_OWNER
    ).json()
    assert [o["name"] for o in columns["data"]] == ["email", "id"]
    first = api.get(
        f"/api/v1/data-stores/{store_id}/objects?kind=table&limit=1", headers=APP_OWNER
    ).json()
    assert first["meta"]["next_cursor"]
    second = api.get(
        f"/api/v1/data-stores/{store_id}/objects?kind=table&limit=1"
        f"&cursor={first['meta']['next_cursor']}",
        headers=APP_OWNER,
    ).json()
    assert [o["path"] for o in second["data"]] == ["public.orders"]
    assert second["meta"]["next_cursor"] is None


def test_creating_assets_from_tables_maps_them_and_asks_the_data_owner(
    api: TestClient, harvest: Harvest, personas: dict[str, User], db_connection: Connection
) -> None:
    """The slice's exit: harvest fills it in, and the Data Owner confirms from the Inbox."""
    store_id = _store(api)
    harvest(store_id)

    created = api.post(
        f"/api/v1/data-stores/{store_id}/mappings/assets",
        headers=APP_OWNER,
        json={
            "paths": ["public.customers"],
            "retention_policy_id": _retention_policy(api)["id"],
            "owner_id": str(personas["priya.raman"].id),
        },
    )
    assert created.status_code == 201, created.text
    [asset] = created.json()["data"]
    assert asset["asset_name"] == "customers"

    detail = api.get(f"/api/v1/assets/{asset['asset_id']}", headers=APP_OWNER).json()["data"]
    assert detail["is_stored"] is True
    assert detail["domain"]["code"] == "customer"
    assert sorted(e["name"] for e in detail["data_elements"]) == ["email", "id"]
    assert detail["owner"]["status"] == "pending"

    objects = _status(api, store_id)["data"]["objects"]
    assert (objects["unmapped_tables"], objects["unmapped_columns"]) == (1, 1)
    mapped = api.get(
        f"/api/v1/data-stores/{store_id}/objects?mapped=true&kind=table", headers=APP_OWNER
    ).json()["data"]
    assert mapped[0]["mapping"]["asset_name"] == "customers"
    columns = api.get(
        f"/api/v1/data-stores/{store_id}/objects?parent_path=public.customers", headers=APP_OWNER
    ).json()["data"]
    assert all(c["mapping"]["data_element_id"] for c in columns)

    [item] = api.get("/api/v1/inbox", headers=DATA_OWNER).json()["data"]
    assert item["subject_id"] == asset["asset_id"]
    confirmed = api.post(
        f"/api/v1/assets/{asset['asset_id']}/ownership/owner/confirm", headers=DATA_OWNER
    )
    assert confirmed.status_code == 200
    assert api.get("/api/v1/inbox", headers=DATA_OWNER).json()["data"] == []
    assert "data_store.table_mapped" in _audit(db_connection)


def test_mapping_a_table_to_an_existing_asset_adds_the_missing_elements(
    api: TestClient, harvest: Harvest
) -> None:
    store_id = _store(api)
    harvest(store_id)
    asset = api.post(
        "/api/v1/assets",
        headers=APP_OWNER,
        json={"name": "Customer master", "domain_id": _ref(api, "domains", "customer")},
    ).json()["data"]
    api.post(
        f"/api/v1/assets/{asset['id']}/data-elements",
        headers=APP_OWNER,
        json={"name": "email", "data_type": "text", "is_pii": True},
    )

    mapped = api.post(
        f"/api/v1/data-stores/{store_id}/mappings",
        headers=APP_OWNER,
        json={"path": "public.customers", "asset_id": asset["id"]},
    )
    assert mapped.status_code == 200, mapped.text
    assert mapped.json()["data"]["mapping"]["asset_name"] == "Customer master"
    elements = api.get(f"/api/v1/assets/{asset['id']}", headers=APP_OWNER).json()["data"][
        "data_elements"
    ]
    by_name = {e["name"]: e for e in elements}
    assert sorted(by_name) == ["email", "id"]
    assert by_name["email"]["is_pii"] is True  # the declared element was matched, not replaced

    # Mapping it again to the same asset is fine; to another one is a conflict.
    again = api.post(
        f"/api/v1/data-stores/{store_id}/mappings",
        headers=APP_OWNER,
        json={"path": "public.customers", "asset_id": asset["id"]},
    )
    assert again.status_code == 200
    other = api.post(
        "/api/v1/assets",
        headers=APP_OWNER,
        json={"name": "Other", "domain_id": _ref(api, "domains", "customer")},
    ).json()["data"]
    conflict = api.post(
        f"/api/v1/data-stores/{store_id}/mappings",
        headers=APP_OWNER,
        json={"path": "public.customers", "asset_id": other["id"]},
    )
    assert conflict.status_code == 409


def test_only_tables_of_the_last_harvest_can_be_mapped(api: TestClient, harvest: Harvest) -> None:
    store_id = _store(api)
    url = f"/api/v1/data-stores/{store_id}/mappings/assets"
    body: dict[str, Any] = {
        "paths": ["public.customers"],
        "retention_policy_id": _retention_policy(api)["id"],
    }
    assert api.post(url, headers=APP_OWNER, json=body).status_code == 400  # not harvested yet
    harvest(store_id)
    body["paths"] = ["public.nope"]
    assert api.post(url, headers=APP_OWNER, json=body).status_code == 404
    body["paths"] = ["public.customers.id"]  # a column, not a table
    assert api.post(url, headers=APP_OWNER, json=body).status_code == 404


def test_run_harvest_queues_a_job_and_is_audited(
    api: TestClient, db_connection: Connection
) -> None:
    store_id = _store(api)
    response = api.post(f"/api/v1/data-stores/{store_id}/harvest", headers=APP_OWNER)
    assert response.status_code == 202
    job = response.json()["data"]
    assert job["kind"] == "connectors.harvest"
    assert response.headers["Location"].endswith(f"/jobs/{job['id']}")
    payload = db_connection.execute(
        text("SELECT payload FROM platform.job WHERE id = :id"), {"id": job["id"]}
    ).scalar_one()
    assert payload["data_store_id"] == store_id
    assert "data_store.harvest_requested" in _audit(db_connection)


def test_roles_and_scope_decide_who_may_harvest_and_map(api: TestClient, harvest: Harvest) -> None:
    store_id = _store(api)
    harvest(store_id)
    for headers in (DATA_OWNER, STEWARD, AUDITOR):
        assert (
            api.post(f"/api/v1/data-stores/{store_id}/harvest", headers=headers).status_code == 403
        )
    assert _status(api, store_id, DATA_OWNER)["allowed_actions"] == ["map_objects"]
    assert _status(api, store_id, STEWARD)["allowed_actions"] == []
    assert _status(api, store_id, AUDITOR)["allowed_actions"] == []
    denied = api.post(
        f"/api/v1/data-stores/{store_id}/mappings/assets",
        headers=STEWARD,
        json={"paths": ["public.orders"], "retention_policy_id": _retention_policy(api)["id"]},
    )
    assert denied.status_code == 403

    finance = _store(api, "finance", "LEDGER", GOVERNANCE)
    assert api.get(f"/api/v1/data-stores/{finance}/harvest", headers=DATA_OWNER).status_code == 403
    assert api.post(f"/api/v1/data-stores/{finance}/harvest", headers=DATA_OWNER).status_code == 403
    missing = api.get(f"/api/v1/data-stores/{uuid.uuid4()}/harvest", headers=APP_OWNER)
    assert missing.status_code == 404


# --- Jobs, events and the schedule


def _context(session: Session, payload: dict[str, Any]) -> JobContext:
    return JobContext(
        job_id=uuid.uuid4(),
        kind="connectors.harvest",
        payload=payload,
        attempt=1,
        session=session,
        _report_progress=lambda percent: None,
    )


def _harvest_jobs(connection: Connection, store_id: str) -> int:
    return connection.execute(
        text(
            "SELECT count(*) FROM platform.job "
            "WHERE kind = 'connectors.harvest' AND payload->>'data_store_id' = :id"
        ),
        {"id": store_id},
    ).scalar_one()


def test_registering_a_store_queues_its_first_harvest(
    api: TestClient, database: Database, db_connection: Connection
) -> None:
    store_id = _store(api)
    [(event_id, payload)] = db_connection.execute(
        text(
            "SELECT id, payload FROM platform.outbox_event "
            "WHERE type = 'inventory.data_store_created' AND payload->>'data_store_id' = :id"
        ),
        {"id": store_id},
    ).all()
    event = Event(event_id, "inventory.data_store_created", payload, datetime.now(UTC))
    with database.transaction() as session:
        jobs.on_data_store_created(session, event)
        jobs.on_data_store_created(session, event)  # a redelivery queues nothing more
    assert _harvest_jobs(db_connection, store_id) == 1


def test_the_scheduled_sweep_queues_one_harvest_per_store(
    api: TestClient, database: Database, db_connection: Connection
) -> None:
    store_id = _store(api)
    with database.transaction() as session:
        context = _context(session, {})
        result = jobs.harvest_all(context)
        jobs.harvest_all(context)  # a retried sweep queues nothing new
    assert result["queued"] >= 1
    assert _harvest_jobs(db_connection, store_id) == 1


def test_the_harvest_job_reports_the_outcome(
    api: TestClient, database: Database, monkeypatch: pytest.MonkeyPatch
) -> None:
    store_id = _store(api)
    monkeypatch.setattr(
        "app.modules.connectors.service.adapter_for", lambda platform, kind: FakeAdapter()
    )
    with database.transaction() as session:
        result = jobs.harvest(_context(session, {"data_store_id": store_id, "requested_by": None}))
        gone = jobs.harvest(
            _context(session, {"data_store_id": str(uuid.uuid4()), "requested_by": None})
        )
    assert result["status"] == "succeeded"
    assert (result["table"], result["column"]) == (2, 3)
    assert gone["status"] == "skipped"
