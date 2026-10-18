# DMC backend

A uv workspace: `apps/api` (FastAPI wiring) and one package per bounded context in `packages/`. Rules: [backend instructions](../.github/instructions/backend.instructions.md). Layout decision: [ADR 0002](../docs/adr/0002-backend-layout-and-contract-pipeline.md).

```bash
uv sync                                         # create .venv with all packages and dev tools
cp .env.example .env                            # optional local overrides
uv run uvicorn dmc_api.main:app --reload        # http://localhost:8000/api/v1/health, docs at /docs
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run lint-imports                             # package boundaries
```

After any API change, run `npm run api:sync` from `frontend/`. It exports `contracts/openapi.json` and regenerates `frontend/src/api/`. Commit both together.
