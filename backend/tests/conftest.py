from collections.abc import Iterator

import pytest
from alembic import command
from fastapi.testclient import TestClient
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Connection, Engine, create_engine
from sqlalchemy.exc import OperationalError

from app.core.config import Settings
from app.core.db import Database
from app.core.migrations import alembic_config
from app.main import create_app
from app.modules.identity.service import IdentityService, User


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
def migration_url() -> str:
    url = DatabaseUnderTest().migration_database_url
    if not url:
        pytest.fail("Set DMC_TEST_MIGRATION_DATABASE_URL (see backend/.env.example)")
    return url


@pytest.fixture(scope="session")
def db_engine(migration_url: str) -> Iterator[Engine]:
    """The runtime role's engine on dmc_test, after migrating dmc_test to head."""
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
    command.upgrade(alembic_config(migration_url), "head")
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


@pytest.fixture
def owner_connection(db_engine: Engine, migration_url: str) -> Iterator[Connection]:
    """Like db_connection, but as the migration role that owns the schemas (rolled back after)."""
    engine = create_engine(migration_url)
    with engine.connect() as connection:
        transaction = connection.begin()
        yield connection
        if transaction.is_active:
            transaction.rollback()
    engine.dispose()


@pytest.fixture
def personas(database: Database) -> dict[str, User]:
    """The dev personas, seeded in the test's transaction, by username. Send one's username in
    the X-DMC-Dev-User header to act as them through `db_client`."""
    with database.transaction() as session:
        IdentityService(session).seed_personas()
        return {user.username: user for user in IdentityService(session).list_active_users()}
