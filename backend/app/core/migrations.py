"""Alembic wiring and the `dmc-migrate` command (ADR 0004 §3, ADR 0005).

    uv run dmc-migrate upgrade [REVISION]        default: head
    uv run dmc-migrate downgrade REVISION        e.g. -1 or base
    uv run dmc-migrate revision -m "add inventory" [--autogenerate]
    uv run dmc-migrate current | history | check

Uses DMC_MIGRATION_DATABASE_URL (the dmc_migrator role). The API and worker never migrate; on
start-up they call `ensure_database_is_current` and refuse to run against an older schema.
"""

import argparse
import logging
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Connection

from app.core.config import get_settings

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


class DatabaseOutOfDateError(RuntimeError):
    pass


def alembic_config(url: str) -> Config:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.set_main_option("file_template", "%%(year)d%%(month).2d%%(day).2d_%%(rev)s_%%(slug)s")
    config.attributes["url"] = url
    return config


def ensure_database_is_current(connection: Connection) -> None:
    """Raise unless the database is at the head revision of the code's migrations."""
    expected = set(ScriptDirectory(str(MIGRATIONS_DIR)).get_heads())
    actual = set(MigrationContext.configure(connection).get_current_heads())
    if actual != expected:
        raise DatabaseOutOfDateError(
            f"Database is at {sorted(actual) or 'no revision'}, the code expects "
            f"{sorted(expected)}. Run `uv run dmc-migrate upgrade` first."
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dmc-migrate", description="Run database migrations.")
    commands = parser.add_subparsers(dest="command", required=True)
    upgrade = commands.add_parser("upgrade", help="upgrade to a revision (default: head)")
    upgrade.add_argument("revision", nargs="?", default="head")
    downgrade = commands.add_parser("downgrade", help="downgrade to a revision (-1, base, …)")
    downgrade.add_argument("revision")
    revision = commands.add_parser("revision", help="create a new migration file")
    revision.add_argument("-m", "--message", required=True)
    revision.add_argument("--autogenerate", action="store_true")
    commands.add_parser("current", help="show the database's revision")
    commands.add_parser("history", help="list migrations")
    commands.add_parser("check", help="fail if the models have changes no migration covers")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    url = get_settings().migration_database_url
    if not url:
        print("Set DMC_MIGRATION_DATABASE_URL (see backend/.env.example).", file=sys.stderr)
        return 2
    config = alembic_config(url)

    match args.command:
        case "upgrade":
            command.upgrade(config, args.revision)
        case "downgrade":
            command.downgrade(config, args.revision)
        case "revision":
            command.revision(config, message=args.message, autogenerate=args.autogenerate)
        case "current":
            command.current(config, verbose=True)
        case "history":
            command.history(config)
        case "check":
            command.check(config)
    return 0


if __name__ == "__main__":
    sys.exit(main())
