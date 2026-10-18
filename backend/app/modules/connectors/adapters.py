"""Harvest adapters: read a platform's structure and statistics, never its data (ARCHITECTURE §11).

An adapter gets a connection URL that `resolve_connection` looked up from the data store's
`connection_ref`. DMC stores the reference, never the secret, and refuses a reference that
resolves to one of its own databases, so a harvest never runs with DMC's own credentials.
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings
from app.modules.connectors.domain import ObjectKind

CONNECT_TIMEOUT_SECONDS = 10
STATEMENT_TIMEOUT_MS = 30_000
_ERROR_LIMIT = 500


class HarvestError(Exception):
    """A harvest could not run; the message is safe to show to users."""


@dataclass(frozen=True)
class HarvestedObject:
    kind: ObjectKind
    path: str
    name: str
    parent_path: str | None = None
    ordinal: int = 0
    data_type: str | None = None
    row_count: int | None = None


@dataclass(frozen=True)
class Catalog:
    objects: list[HarvestedObject] = field(default_factory=list)


class HarvestAdapter(Protocol):
    def harvest(self, connection_url: str) -> Catalog: ...


# --- Connection references

# `env:` references may only name a variable that holds a harvest URL, so a reference cannot be
# pointed at any other setting.
_ENV_REFERENCE = re.compile(r"^DMC_[A-Z0-9_]*HARVEST_URL$")


def _identity(url: str) -> str:
    parsed = make_url(url)
    return f"{parsed.username}@{parsed.host}:{parsed.port}/{parsed.database}"


def _own_database_identities(settings: Settings) -> set[str]:
    urls = (settings.database_url, settings.migration_database_url, settings.estate_migration_url)
    return {_identity(url) for url in urls if url}


def resolve_connection(reference: str, settings: Settings | None = None) -> str:
    """The connection URL a `connection_ref` points at.

    Only `env:<VARIABLE>` is supported until the corporate secrets store is chosen (Phase 4).
    """
    settings = settings or Settings()
    scheme, _, name = reference.partition(":")
    if scheme != "env":
        raise HarvestError(
            f"Connection references of type {scheme!r} are not supported yet; use env:<NAME>."
        )
    if not _ENV_REFERENCE.match(name):
        raise HarvestError("An env: reference must name a DMC_…_HARVEST_URL variable.")
    url = os.environ.get(name) or _from_env_file(name)
    if not url:
        raise HarvestError(f"The connection {reference} is not configured on this server.")
    try:
        identity = _identity(url)
    except Exception as exc:
        raise HarvestError(f"The connection {reference} is not a database URL.") from exc
    if identity in _own_database_identities(settings):
        raise HarvestError(
            "A harvest never uses DMC's own database credentials; point the reference at a "
            "read-only account."
        )
    return url


def _from_env_file(name: str) -> str | None:
    env_file = Settings.model_config.get("env_file")
    if not isinstance(env_file, str) or not Path(env_file).is_file():
        return None
    return dotenv_values(env_file).get(name)


# --- PostgreSQL

_SYSTEM_SCHEMAS = "n.nspname <> 'information_schema' AND n.nspname NOT LIKE 'pg\\_%'"
_SCHEMAS = text(
    f"SELECT n.nspname AS name FROM pg_namespace n WHERE {_SYSTEM_SCHEMAS} ORDER BY n.nspname"
)
_TABLES = text(
    f"""
    SELECT n.nspname AS schema, c.relname AS name, s.n_live_tup AS row_count
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    LEFT JOIN pg_stat_all_tables s ON s.relid = c.oid
    WHERE c.relkind IN ('r', 'p') AND {_SYSTEM_SCHEMAS}
    ORDER BY n.nspname, c.relname
    """
)
_COLUMNS = text(
    f"""
    SELECT n.nspname AS schema, c.relname AS "table", a.attname AS name, a.attnum AS ordinal,
           format_type(a.atttypid, a.atttypmod) AS data_type
    FROM pg_attribute a
    JOIN pg_class c ON c.oid = a.attrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relkind IN ('r', 'p') AND a.attnum > 0 AND NOT a.attisdropped AND {_SYSTEM_SCHEMAS}
    ORDER BY n.nspname, c.relname, a.attnum
    """
)


class PostgresHarvest:
    """Schemas, tables, columns and estimated row counts from the system catalogs."""

    def harvest(self, connection_url: str) -> Catalog:
        # Read-only for the session as well as by the account's grants.
        engine = create_engine(
            connection_url,
            connect_args={
                "connect_timeout": CONNECT_TIMEOUT_SECONDS,
                "options": (
                    "-c default_transaction_read_only=on "
                    f"-c statement_timeout={STATEMENT_TIMEOUT_MS}"
                ),
            },
        )
        try:
            with engine.connect() as connection:
                schemas = connection.execute(_SCHEMAS).all()
                tables = connection.execute(_TABLES).all()
                columns = connection.execute(_COLUMNS).all()
        except SQLAlchemyError as exc:
            raise HarvestError(_describe(exc)) from exc
        finally:
            engine.dispose()

        objects = [HarvestedObject(ObjectKind.SCHEMA, row.name, row.name) for row in schemas]
        objects += [
            HarvestedObject(
                ObjectKind.TABLE,
                f"{row.schema}.{row.name}",
                row.name,
                parent_path=row.schema,
                row_count=row.row_count,
            )
            for row in tables
        ]
        objects += [
            HarvestedObject(
                ObjectKind.COLUMN,
                f"{row.schema}.{row.table}.{row.name}",
                row.name,
                parent_path=f"{row.schema}.{row.table}",
                ordinal=row.ordinal,
                data_type=row.data_type,
            )
            for row in columns
        ]
        return Catalog(objects)


def _describe(exc: SQLAlchemyError) -> str:
    """The database's own message, first line only: never the URL or the password."""
    message = str(getattr(exc, "orig", None) or exc).strip()
    first_line = message.splitlines()[0] if message else type(exc).__name__
    return first_line[:_ERROR_LIMIT]


def adapter_for(platform: str, store_type: str) -> HarvestAdapter:
    if store_type == "relational" and platform.lower().startswith("postgres"):
        return PostgresHarvest()
    raise HarvestError(f"There is no harvest adapter for {platform} ({store_type}) yet.")
