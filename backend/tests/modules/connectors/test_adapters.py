import pytest
from sqlalchemy import Engine
from sqlalchemy.engine import make_url

from app.core.config import Settings
from app.modules.connectors.adapters import (
    HarvestError,
    PostgresHarvest,
    adapter_for,
    resolve_connection,
)
from app.modules.connectors.domain import ObjectKind

OWN = "postgresql+psycopg://dmc_app:dmc_app@localhost:5432/dmc"


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        database_url=OWN,
        migration_database_url="postgresql+psycopg://dmc_migrator:x@localhost:5432/dmc",
    )


def test_an_env_reference_resolves_to_the_named_harvest_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = "postgresql+psycopg://dmc_harvest:secret@localhost:5432/estate"
    monkeypatch.setenv("DMC_SHOP_HARVEST_URL", url)
    assert resolve_connection("env:DMC_SHOP_HARVEST_URL", _settings()) == url


@pytest.mark.parametrize(
    ("reference", "message"),
    [
        ("vault:dmc/orders-db", "not supported yet"),
        ("env:DMC_DATABASE_URL", "HARVEST_URL"),
        ("env:PATH", "HARVEST_URL"),
        ("env:DMC_MISSING_HARVEST_URL", "not configured"),
    ],
)
def test_a_reference_that_cannot_be_used_is_refused(
    reference: str, message: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DMC_MISSING_HARVEST_URL", raising=False)
    with pytest.raises(HarvestError, match=message):
        resolve_connection(reference, _settings())


def test_a_reference_to_dmcs_own_database_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DMC_SNEAKY_HARVEST_URL", OWN)
    with pytest.raises(HarvestError, match="never uses DMC"):
        resolve_connection("env:DMC_SNEAKY_HARVEST_URL", _settings())


def test_adapters_are_chosen_by_platform() -> None:
    assert isinstance(adapter_for("PostgreSQL 18", "relational"), PostgresHarvest)
    with pytest.raises(HarvestError, match="no harvest adapter"):
        adapter_for("Amazon S3", "object_storage")


def test_the_postgres_adapter_reads_schemas_tables_and_columns(
    db_engine: Engine, migration_url: str
) -> None:
    catalog = PostgresHarvest().harvest(migration_url)
    by_path = {o.path: o for o in catalog.objects}
    assert by_path["inventory"].kind == ObjectKind.SCHEMA
    table = by_path["inventory.application"]
    assert table.kind == ObjectKind.TABLE and table.parent_path == "inventory"
    column = by_path["inventory.application.code"]
    assert column.kind == ObjectKind.COLUMN
    assert column.parent_path == "inventory.application"
    assert column.data_type == "text"
    assert not any(o.path.startswith(("pg_", "information_schema")) for o in catalog.objects)


def test_a_connection_failure_is_reported_without_the_password() -> None:
    url = make_url("postgresql+psycopg://dmc_harvest:hunter2@localhost:1/estate")
    with pytest.raises(HarvestError) as raised:
        PostgresHarvest().harvest(url.render_as_string(hide_password=False))
    assert "hunter2" not in str(raised.value)
    assert str(raised.value)
