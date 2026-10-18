"""`dmc-seed`: loads the local data set through the module services (ADR 0004 §8).

    uv run dmc-seed

Writes to DMC_DATABASE_URL and refuses to run in staging or production. Safe to run again.
"""

import sys

from app.core.config import PROTECTED, get_settings
from app.core.db import Database, create_database_engine
from app.modules.identity.service import IdentityService


def main() -> int:
    settings = get_settings()
    if settings.environment in PROTECTED:
        print(
            f"dmc-seed refuses to run in the {settings.environment} environment.", file=sys.stderr
        )
        return 2
    if not settings.database_url:
        print("Set DMC_DATABASE_URL (see backend/.env.example).", file=sys.stderr)
        return 2
    engine = create_database_engine(settings.database_url)
    try:
        with Database(engine).transaction() as session:
            personas = IdentityService(session).seed_personas()
    finally:
        engine.dispose()
    print(f"Seeded {len(personas)} new personas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
