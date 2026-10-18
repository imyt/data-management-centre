import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import Connection, Engine, text

from app.core.config import Settings
from app.core.migrations import (
    DatabaseOutOfDateError,
    alembic_config,
    ensure_database_is_current,
    main,
)
from app.main import create_app


def test_migrations_upgrade_downgrade_and_upgrade_again(
    db_engine: Engine, migration_url: str
) -> None:
    config = alembic_config(migration_url)

    command.downgrade(config, "base")
    command.upgrade(config, "head")

    with db_engine.connect() as connection:
        ensure_database_is_current(connection)


def test_models_have_no_changes_missing_a_migration(db_engine: Engine, migration_url: str) -> None:
    command.check(alembic_config(migration_url))


def test_out_of_date_database_is_refused(db_connection: Connection) -> None:
    db_connection.execute(text("UPDATE alembic_version SET version_num = 'not-a-revision'"))

    with pytest.raises(DatabaseOutOfDateError, match="dmc-migrate upgrade"):
        ensure_database_is_current(db_connection)


def test_app_starts_against_a_current_database(db_engine: Engine) -> None:
    url = db_engine.url.render_as_string(hide_password=False)
    settings = Settings(_env_file=None, environment="test", database_url=url)

    with TestClient(create_app(settings)) as client:
        assert client.get("/api/v1/health").status_code == 200


def test_dmc_migrate_needs_a_migration_url(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("app.core.migrations.get_settings", lambda: Settings(_env_file=None))

    assert main(["current"]) == 2
    assert "DMC_MIGRATION_DATABASE_URL" in capsys.readouterr().err
