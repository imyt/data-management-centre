from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Connection, Engine, create_engine
from sqlalchemy.exc import OperationalError

from app.core.config import Settings
from app.core.db import Database
from app.main import create_app


class DatabaseUnderTest(BaseSettings):
    """DMC_TEST_* URLs for the dmc_test database (backend/.env.example)."""

    model_config = SettingsConfigDict(env_prefix="DMC_TEST_", env_file=".env", extra="ignore")

    database_url: str | None = None
    migration_database_url: str | None = None


@pytest.fixture
def client() -> TestClient:
    app = create_app(Settings(_env_file=None, environment="test"))
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="session")
def db_engine() -> Iterator[Engine]:
    url = DatabaseUnderTest().database_url
    if not url:
        pytest.fail("Set DMC_TEST_DATABASE_URL (see backend/.env.example)")
    engine = create_engine(url)
    try:
        engine.connect().close()
    except OperationalError as exc:
        pytest.fail(
            f"Cannot reach the test database ({exc.orig}). "
            "Start it with `docker compose up -d --wait db` in infra/."
        )
    yield engine
    engine.dispose()


@pytest.fixture
def db_connection(db_engine: Engine) -> Iterator[Connection]:
    """A connection whose transaction is rolled back after the test, whatever the test commits."""
    with db_engine.connect() as connection:
        transaction = connection.begin()
        yield connection
        if transaction.is_active:
            transaction.rollback()


@pytest.fixture
def database(db_connection: Connection) -> Database:
    return Database(db_connection)


@pytest.fixture
def db_client(database: Database) -> TestClient:
    """An app whose requests run inside the test's rolled-back transaction."""
    app = create_app(Settings(_env_file=None, environment="test"))
    app.state.database = database
    return TestClient(app, raise_server_exceptions=False)
