import pytest
from fastapi.testclient import TestClient

from app.core.db import Database
from app.core.jobs import Registry
from app.core.jobs.worker import Worker
from app.modules.identity.service import User
from app.modules.policy import jobs


@pytest.fixture
def api(db_client: TestClient, personas: dict[str, User]) -> TestClient:
    return db_client


@pytest.fixture
def settle(database: Database):  # type: ignore[no-untyped-def]
    """Run policy's event handlers and jobs the way the worker does, in the test's transaction,
    until nothing is left to do."""
    registry = Registry()
    jobs.register(registry)
    worker = Worker(database, registry, keep_leases=False)

    def run() -> None:
        for _ in range(20):
            relayed = worker.relay_events()
            ran = worker.run_next_job()
            if not relayed and not ran:
                return
        raise AssertionError("the worker never settled")

    return run
