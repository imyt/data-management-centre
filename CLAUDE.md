# Data Management Centre (DMC)

Internal governance control plane for data controls. Single tenant. React frontend, FastAPI backend, PostgreSQL.

## Read first

- `PRD.md`: what DMC does and for whom.
- `ARCHITECTURE.md`: system design.
- `DESIGN.md`: UI principles, identity, patterns.

## Layout

- `frontend/`: React app. See `frontend/CLAUDE.md`.
- `backend/`: FastAPI app, one module per domain. See `backend/CLAUDE.md`.

## Commands

- Frontend (pnpm): `cd frontend && npm run dev | lint | test | build | e2e`
- Backend (uv): `cd backend && uv sync`, then `uv run uvicorn dmc_api.main:app --reload`, `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run lint-imports`
- API contract: after any API change, run `npm run api:sync` in `frontend/` and commit `contracts/openapi.json` and `frontend/src/api/` together

## Ways of working

- Work in thin vertical slices: data model, API, UI and a test for one capability at a time.
- Use the domain vocabulary exactly: applied control (not obligation), Know, Assess, Act, Assure.
- An action is done only when a later evaluation verifies it.
- Do not add multi-tenancy, data fabric references or regulation-specific rules until decided.
- When a decision changes, update `PRD.md`, `ARCHITECTURE.md` or `DESIGN.md` in the same change.
