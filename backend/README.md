# DMC backend

One FastAPI app: `app/core` (config, errors, base schemas) and one package per domain module in `app/modules`. Rules: [CLAUDE.md](CLAUDE.md) and the [backend instructions](../.github/instructions/backend.instructions.md). Layout decision: [ADR 0003](../docs/adr/0003-single-backend-app-with-modules.md).

```bash
uv sync                                         # create .venv with the app and dev tools
cp .env.example .env                            # database URLs and local overrides
uv run uvicorn app.main:app --reload            # http://localhost:8000/api/v1/health, docs at /docs
uv run dmc-worker                               # background jobs, outbox relay and schedules; Ctrl+C stops it
uv run pytest                                   # needs Postgres: docker compose up -d --wait db (in infra/)
uv run ruff check . && uv run ruff format --check .
uv run lint-imports                             # module boundaries
uv run dmc-migrate upgrade                      # apply migrations (the API refuses to start without them)
uv run dmc-seed                                 # create the dev personas (refused in staging and production)
uv run dmc-migrate revision -m "add x" --autogenerate   # new migration from model changes
```

Responses: every route returns `{data, allowed_actions, meta}` (`Envelope` or, for lists, `ListEnvelope` with `meta.next_cursor`) from `app/core/schemas.py`. Only the platform endpoints are exempt: `/health` (liveness), `/health/ready` (readiness: the database answers, else 503) and `/meta` (environment, version, commit and contract hash for the frontend's pairing check; ADR 0004 §5, ADR 0008). Errors are RFC 9457 problem details (`application/problem+json`).

Logs: JSON lines on stdout, plain text locally (`DMC_LOG_FORMAT` overrides). Each record carries `request_id` during a request; background work adds its own fields with `with log_context(job_id=str(job.id)):` from `app/core/logs.py`. One `dmc.access` record per request: method, path, status, `duration_ms`.

After any API change, run `npm run api:sync` from `frontend/`. It exports `contracts/openapi.json` and regenerates `frontend/src/api/`. Commit both together.

Database access, sessions and the test database: [ADR 0005](../docs/adr/0005-database-layer.md).

Background work ([ADR 0009](../docs/adr/0009-jobs-outbox-and-idempotency.md)): `enqueue(session, kind, payload)` (`app.core.jobs`) queues a job and `publish(session, type, payload)` (`app.core.outbox`) writes a domain event, both in the caller's transaction. Handlers and schedules are registered in `app/worker.py`. Routes that start a long operation return `accepted(request, job)` (`202` with `Location: /api/v1/jobs/{id}`); retryable writes take `IdempotencyDep` (`app.core.idempotency`) and return through `idempotency.record(...)`.
