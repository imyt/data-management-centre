import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.auth import DEV_USER_HEADER
from app.core.db import Database
from app.core.jobs import Registry
from app.core.jobs.worker import Worker
from app.modules.connectors import jobs as connector_jobs
from app.modules.connectors.adapters import Catalog, HarvestedObject, HarvestError
from app.modules.connectors.domain import ObjectKind
from app.modules.evaluation import jobs as evaluation_jobs
from app.modules.identity.service import User
from app.modules.policy import jobs as policy_jobs

GOVERNANCE = {DEV_USER_HEADER: "hannah.becker"}
APP_OWNER = {DEV_USER_HEADER: "marcus.webb"}  # Customer and Finance
DATA_OWNER = {DEV_USER_HEADER: "priya.raman"}  # Customer only
STEWARD = {DEV_USER_HEADER: "lena.okafor"}  # Customer only
PROCESS_OWNER = {DEV_USER_HEADER: "tomas.silva"}  # Finance only
AUDITOR = {DEV_USER_HEADER: "sofia.marin"}

NOW = datetime(2026, 10, 18, 9, 0, tzinfo=UTC)

CATALOG = Catalog(
    [
        HarvestedObject(ObjectKind.SCHEMA, "public", "public"),
        HarvestedObject(ObjectKind.TABLE, "public.customers", "customers", "public", row_count=8),
        HarvestedObject(
            ObjectKind.COLUMN, "public.customers.id", "id", "public.customers", 1, "bigint"
        ),
        HarvestedObject(
            ObjectKind.COLUMN,
            "public.customers.last_login_at",
            "last_login_at",
            "public.customers",
            2,
            "timestamp with time zone",
        ),
        HarvestedObject(
            ObjectKind.COLUMN,
            "public.customers.created_at",
            "created_at",
            "public.customers",
            3,
            "timestamp with time zone",
        ),
    ]
)


class FakeStore:
    """Stands in for the estate: what harvest finds and what the oldest record is."""

    def __init__(self) -> None:
        self.oldest: datetime | None = NOW - timedelta(days=500)
        self.error: str | None = None
        self.asked: list[tuple[str, str, str]] = []

    def harvest(self, connection_url: str) -> Catalog:
        return CATALOG

    def oldest_record(
        self, connection_url: str, schema: str, table: str, column: str
    ) -> datetime | None:
        self.asked.append((schema, table, column))
        if self.error:
            raise HarvestError(self.error)
        return self.oldest


class Clock:
    """The time evaluations see. Starts at NOW; move it to let days pass."""

    def __init__(self) -> None:
        self.now = NOW


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    clock = Clock()
    monkeypatch.setattr("app.modules.evaluation.service._now", lambda: clock.now)
    return clock


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> FakeStore:
    fake = FakeStore()
    monkeypatch.setattr(
        "app.modules.connectors.service.resolve_connection", lambda ref: "postgresql://fake/db"
    )
    monkeypatch.setattr("app.modules.connectors.service.adapter_for", lambda *_: fake)
    monkeypatch.setattr("app.modules.connectors.service.record_age_adapter_for", lambda *_: fake)
    return fake


@pytest.fixture
def api(
    db_client: TestClient, personas: dict[str, User], store: FakeStore, clock: Clock
) -> TestClient:
    return db_client


Settle = Callable[[], None]


@pytest.fixture
def settle(database: Database) -> Settle:
    """Run the worker's event handlers and jobs in the test's transaction until none are left."""
    registry = Registry()
    policy_jobs.register(registry)
    connector_jobs.register(registry, interval=timedelta(days=1))
    evaluation_jobs.register(registry, interval=timedelta(hours=6))
    worker = Worker(database, registry, keep_leases=False)

    def run() -> None:
        for _ in range(60):
            relayed = worker.relay_events()
            ran = worker.run_next_job()
            if not relayed and not ran:
                return
        raise AssertionError("the worker never settled")

    return run


def reference(client: TestClient, path: str, code: str) -> str:
    items = client.get(f"/api/v1/reference/{path}", headers=GOVERNANCE).json()["data"]
    return next(item["id"] for item in items if item["code"] == code)


def new_id() -> str:
    return str(uuid.uuid4())
