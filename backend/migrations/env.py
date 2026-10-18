"""Alembic environment. Run through `uv run dmc-migrate`, which passes the database URL."""

import importlib
import importlib.util
import pkgutil

from alembic import context
from sqlalchemy import create_engine, pool

import app.modules
from app.core.db import Base

config = context.config


# Core's own tables, in the `platform` schema.
CORE_MODELS = ("app.core.jobs.models", "app.core.outbox", "app.core.idempotency")


def _import_all_models() -> None:
    """Import core's and every module's `models`, so their tables are on Base.metadata."""
    for name in CORE_MODELS:
        importlib.import_module(name)
    for module in pkgutil.iter_modules(app.modules.__path__):
        if importlib.util.find_spec(f"app.modules.{module.name}.models") is not None:
            importlib.import_module(f"app.modules.{module.name}.models")


_import_all_models()
target_metadata = Base.metadata
# Only the schemas our models declare; Postgres's own and `public` are left alone.
MODULE_SCHEMAS = {table.schema for table in target_metadata.tables.values() if table.schema}


def _include_name(name: str | None, type_: str, parent_names: object) -> bool:
    if type_ == "schema":
        return name in MODULE_SCHEMAS
    return True


def run_migrations() -> None:
    engine = create_engine(config.attributes["url"], poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            include_name=_include_name,
            compare_type=True,
            transaction_per_migration=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    raise SystemExit("Offline (SQL script) migrations are not supported; run against a database.")
run_migrations()
