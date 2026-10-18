# ADR 0005: Database layer

- Status: accepted
- Date: 2026-10-18

## Context

Roadmap row 0.2 adds database access to the backend. ADR 0004 fixed the platform: PostgreSQL 18, a runtime role that can only read and write data, a migration role that owns the schemas, and tests against real Postgres. This ADR records how the code uses it.

## Decisions

1. **SQLAlchemy 2 (sync) with psycopg 3.** Routes that touch the database are plain `def` functions, which FastAPI runs in its thread pool. Async SQLAlchemy is not used: it adds failure modes (implicit lazy loads that fail at runtime, greenlet bridging) for little gain at DMC's load, and the worker's `SKIP LOCKED` job loop is simpler synchronous.
2. **One transaction per request.** Routes take `SessionDep` from `app/core/db.py`. The transaction commits when the route returns and rolls back if it raises.
   - The dependency is declared with `Depends(..., scope="function")`. With FastAPI's default scope, a yield dependency's exit code runs **after** the response is sent, so a failed commit would still return 200 to the client. A test (`test_failed_commit_is_an_error_response_not_a_success`) fails if the scope is removed.
3. **Models.** Every model inherits `app.core.db.Base`, whose metadata has a naming convention for indexes and constraints, so migrations can refer to them by stable names. `UUIDv7PrimaryKey` gives `id` a server default of `uuidv7()`. `Timestamps` adds `created_at` and `updated_at`. Each module puts its tables in its own schema (`__table_args__ = {"schema": "<module>"}`).
4. **Configuration.** `DMC_DATABASE_URL` (runtime, `dmc_app`) and `DMC_MIGRATION_DATABASE_URL` (migrations, `dmc_migrator`) are SQLAlchemy URLs. They are required in `dev`, `staging` and `production`. Locally they are optional, so the OpenAPI export and tests that don't need a database run without one; a route that needs the database then fails with a message naming the variable.
5. **Tests.**
   - They use the `dmc_test` database through `DMC_TEST_DATABASE_URL` (the runtime role) and `DMC_TEST_MIGRATION_DATABASE_URL`, read from the environment or `backend/.env`.
   - Each test runs inside a transaction on one connection that is rolled back afterwards. Sessions join it through a savepoint, so a commit inside the code under test only releases the savepoint. The `db_client` fixture gives an app whose requests run in that same transaction.
   - Tests connect as the runtime role, so a missing grant fails a test rather than a deployment.
   - If the database is unreachable, the run fails and says how to start it. Tests are never silently skipped.
6. **CI** starts Postgres with the same `infra/compose.yaml` and init scripts as local development, rather than a separately configured service container.

## Consequences

- Developers run `docker compose up -d --wait db` in `infra/` before `uv run pytest`.
- `examples` stays in memory until it is deleted with the first real module.
