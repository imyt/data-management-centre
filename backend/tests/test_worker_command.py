import pytest
from sqlalchemy import Connection

from app import worker
from app.core.config import Settings
from app.core.jobs.housekeeping import PURGE
from app.core.migrations import DatabaseOutOfDateError
from app.modules.connectors.jobs import HARVEST_ALL
from app.modules.connectors.service import HARVEST


def test_registry_has_the_platforms_jobs_and_schedules() -> None:
    registry = worker.build_registry()

    assert {PURGE, HARVEST, HARVEST_ALL} <= set(registry.jobs)
    assert [schedule.kind for schedule in registry.schedules.values()] == [PURGE, HARVEST_ALL]
    assert "inventory.data_store_created" in registry.events


def test_dmc_worker_needs_a_database_url(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(worker, "get_settings", lambda: Settings(_env_file=None))

    assert worker.main([]) == 2
    assert "DMC_DATABASE_URL" in capsys.readouterr().err


def test_dmc_worker_refuses_an_out_of_date_database(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    db_connection: Connection,
) -> None:
    url = db_connection.engine.url.render_as_string(hide_password=False)
    monkeypatch.setattr(worker, "get_settings", lambda: Settings(_env_file=None, database_url=url))

    def out_of_date(connection: Connection) -> None:
        raise DatabaseOutOfDateError("Run `uv run dmc-migrate upgrade` first.")

    monkeypatch.setattr(worker, "ensure_database_is_current", out_of_date)

    assert worker.main([]) == 1
    assert "dmc-migrate upgrade" in capsys.readouterr().err
