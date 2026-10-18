# DMC backend

One FastAPI app: `app/core` (config, errors, base schemas) and one package per domain module in `app/modules`. Rules: [CLAUDE.md](CLAUDE.md) and the [backend instructions](../.github/instructions/backend.instructions.md). Layout decision: [ADR 0003](../docs/adr/0003-single-backend-app-with-modules.md).

```bash
uv sync                                         # create .venv with the app and dev tools
cp .env.example .env                            # database URLs and local overrides
uv run uvicorn app.main:app --reload            # http://localhost:8000/api/v1/health, docs at /docs
uv run pytest                                   # needs Postgres: docker compose up -d --wait db (in infra/)
uv run ruff check . && uv run ruff format --check .
uv run lint-imports                             # module boundaries
```

After any API change, run `npm run api:sync` from `frontend/`. It exports `contracts/openapi.json` and regenerates `frontend/src/api/`. Commit both together.

Database access, sessions and the test database: [ADR 0005](../docs/adr/0005-database-layer.md).
