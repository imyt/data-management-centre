import pytest
from sqlalchemy import Connection, text

from app import seed
from app.core.config import Settings
from app.core.db import Database
from app.estate import TABLES, load_estate
from app.modules.identity.service import User
from app.modules.inventory.service import InventoryService


def test_estate_loads_once_and_has_rows_older_than_the_retention_windows(
    owner_connection: Connection,
) -> None:
    first = load_estate(owner_connection)
    again = load_estate(owner_connection)

    assert first.tables_created == len(TABLES) and first.rows_inserted > 0
    assert again.tables_created == 0 and again.rows_inserted == 0

    def older_than(table: str, column: str, days: int) -> int:
        return owner_connection.execute(
            text(
                f"SELECT count(*) FROM {table} WHERE {column} < now() - make_interval(days => :d)"
            ),
            {"d": days},
        ).scalar_one()

    # Beyond r1y (365 days) and r7y (2555 days), and plenty still inside the window.
    assert older_than("support_tickets", "opened_at", 365) > 0
    assert older_than("orders", "placed_at", 2555) > 0
    assert older_than("customers", "last_login_at", 365) > 0
    assert (
        older_than("orders", "placed_at", 30)
        < owner_connection.execute(text("SELECT count(*) FROM orders")).scalar_one()
    )


def test_sample_application_points_at_the_estate_and_is_registered_once(
    database: Database, personas: dict[str, User]
) -> None:
    with database.transaction() as session:
        first = seed.seed_sample_application(session)
        again = seed.seed_sample_application(session)

    assert first is True and again is False
    with database.transaction() as session:
        principal = personas["hannah.becker"].principal()
        page = InventoryService(session).list_applications(
            principal, limit=10, cursor=None, query=seed.SAMPLE_CODE
        )
        (application,) = page.items
        (store,) = application.environments[0].data_stores
    assert store.name == "estate"
    assert store.connection_ref == seed.ESTATE_CONNECTION_REF


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_seed_refuses_protected_environments(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], environment: str
) -> None:
    settings = Settings(
        _env_file=None,
        environment=environment,
        auth_mode="oidc",
        database_url="postgresql+psycopg://x:x@localhost/x",
    )
    monkeypatch.setattr(seed, "get_settings", lambda: settings)

    assert seed.main() == 2
    assert "refuses" in capsys.readouterr().err


def test_seed_needs_a_database_url(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(seed, "get_settings", lambda: Settings(_env_file=None))

    assert seed.main() == 2
    assert "DMC_DATABASE_URL" in capsys.readouterr().err
