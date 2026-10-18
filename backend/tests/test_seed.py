from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Connection, text

from app import seed
from app.core.config import Settings
from app.core.db import Database
from app.estate import TABLES, load_estate
from app.modules.connectors.adapters import Catalog, HarvestedObject
from app.modules.connectors.domain import ObjectKind
from app.modules.connectors.service import ConnectorsService
from app.modules.evaluation.service import EvaluationService
from app.modules.identity.service import User
from app.modules.inventory.service import InventoryService
from app.modules.policy.service import PolicyService


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


def test_the_starter_control_library_is_added_once_and_applied(
    database: Database, personas: dict[str, User]
) -> None:
    with database.transaction() as session:
        seed.seed_sample_application(session)
        first = seed.seed_policies(session)
        again = seed.seed_policies(session)

    assert first == 3 and again == 0
    with database.transaction() as session:
        principal = personas["hannah.becker"].principal()
        service = PolicyService(session)
        codes = [c.code for c in service.list_controls(limit=10, cursor=None).items]
        applied = service.list_applied_controls(principal, limit=10, cursor=None)
    assert codes == ["KNOW-01", "KNOW-02", "RET-01"]
    # The sample application's production store is selected by KNOW-01 by attribute alone.
    assert [(a.control.code, a.subject.type) for a in applied.items] == [("KNOW-01", "data_store")]


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


class _FakeEstate:
    """A harvest that finds one table, whose oldest record is 4000 days old."""

    oldest = datetime.now(UTC) - timedelta(days=4000)

    def harvest(self, connection_url: str) -> Catalog:
        return Catalog(
            [
                HarvestedObject(ObjectKind.SCHEMA, "public", "public"),
                HarvestedObject(ObjectKind.TABLE, "public.customers", "customers", "public"),
                HarvestedObject(
                    ObjectKind.COLUMN,
                    "public.customers.created_at",
                    "created_at",
                    "public.customers",
                    1,
                    "timestamp with time zone",
                ),
            ]
        )

    def oldest_record(
        self, connection_url: str, schema: str, table: str, column: str
    ) -> datetime | None:
        return self.oldest


def test_estate_tables_become_stored_assets_that_fail_their_retention_window(
    database: Database, personas: dict[str, User], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.modules.connectors.service.resolve_connection", lambda ref: "postgresql://fake/db"
    )
    estate = _FakeEstate()
    with database.transaction() as session:
        seed.seed_sample_application(session)
        connectors = ConnectorsService(session, adapter=estate, record_reader=estate)
        declared = seed.seed_estate_assets(session, connectors)
        again = seed.seed_estate_assets(session, connectors)
        seed.seed_policies(session)
        written = seed.seed_evaluations(session, EvaluationService(session, connectors=connectors))
        rewritten = seed.seed_evaluations(
            session, EvaluationService(session, connectors=connectors)
        )

    assert (declared, again) == (1, 0)  # only public.customers is in the fake catalog
    assert written == 1 and rewritten == 0  # the second pass finds the same facts
    with database.transaction() as session:
        principal = personas["hannah.becker"].principal()
        page = EvaluationService(session).list_results(principal, limit=10, cursor=None)
    [result] = page.items
    assert result.control.code == "RET-01" and result.subject.name == "customers"
    assert result.outcome == "fail"
    assert result.measured == 4000 and result.threshold == 3650
