# ADR 0003: One backend app with core and domain modules

- Status: accepted
- Date: 2026-10-18
- Supersedes: ADR 0002 decisions 1 to 3 (layout, tiers per package, import-linter contracts). Decisions 4 to 8 (errors, operation IDs, contract pipeline, hey-api on TypeScript 6, pnpm) still hold, except that the `ErrorResponse` shape in decision 4 is now RFC 9457 problem details (see "Not done yet").

## Context

ADR 0002 set up `backend/` as a uv workspace with `apps/api` and one package per bounded context (`dmc_common`, `dmc_platform`), so that contexts could be split into services before production. The new `ARCHITECTURE.md` (§1, §4, §5) drops that requirement. It asks for one backend codebase, `backend/app/` with `core/` and `modules/`, where modules can *become* services later without a rewrite. The boundaries are kept by a public `service.py` per module and by import-linter.

## Decisions

1. **Layout.**
   ```
   backend/
     pyproject.toml        one project (package "app", uv_build); ruff, pytest, import-linter
     app/
       main.py             app factory, router wiring
       openapi.py          render_openapi, used by scripts/export_openapi.py and the contract test
       core/               config, errors, handlers (error mapping, request ID), schemas, pagination, health
       modules/<module>/   one package per ARCHITECTURE §5 module, added with its first slice
         service.py        the module's public interface: the only file other modules import
         router.py  schemas.py  domain.py  repository.py  (models.py with the first table)
     migrations/           Alembic, added with the first slice that persists data
     scripts/export_openapi.py
     tests/core/  tests/modules/<module>/
   ```
2. **Flat files inside a module.** The router → service → repository rules from `backend.instructions.md` still apply, but each tier is a file, not a folder.
3. **Import-linter contracts** in `backend/pyproject.toml`:
   - `layers`: `app.openapi` > `app.main` > `app.modules` > `app.core`. Core never imports a module.
   - `protected`: `app.modules.*` may be imported only by `app.main` (for wiring routers) and, from other modules, only through `app.modules.<name>.service`. Both contracts were checked against deliberate violations.
4. **No behaviour change in the move.** `contracts/openapi.json` is byte-identical, all 18 tests are kept, and the CI commands are unchanged.

## Consequences

- Run the API with `uv run uvicorn app.main:app --reload`.
- `examples` stays as the reference module until the first real module lands, then it is deleted with its tests (as ADR 0002 said).
- The nine modules (`identity`, `inventory`, `connectors`, `policy`, `evaluation`, `workflow`, `reporting`, `notification`, `audit`) are created with their first slices, not ahead of time.

## Not done yet

ARCHITECTURE.md asks for these. Each is a behaviour or dependency change, so each gets its own PR:

- ~~Response envelope `{data, allowed_actions, meta}` (§8), and a test that every route uses it.~~ Done: `Envelope` and `ListEnvelope` in `app/core/schemas.py`; `tests/test_response_envelope.py` walks every route (exempt: `getHealth`).
- ~~RFC 9457 problem details instead of `ErrorResponse`.~~ Done: `ProblemDetail` served as `application/problem+json`, with `request_id` and validation `errors` extensions; domain errors use `type` `urn:dmc:problem:<code>`.
- `Idempotency-Key` on retryable writes; `202` with a job id and `/api/v1/jobs/{id}`.
- SQLAlchemy 2, Alembic with one schema per module, the outbox, and the Postgres job queue in a worker.
- mypy, and Alembic upgrade and downgrade in CI (§13).
