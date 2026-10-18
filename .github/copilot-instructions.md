# Copilot instructions (repo-wide)

## Project
A data-dense, workflow-driven web platform (desktop only). Modular monorepo that will later split into separate repos, so keep folders independent.

```
backend/     API, auth/RBAC, business logic, migrations
frontend/    React app + design system (see DESIGN.md)
infra/       Docker Compose, IaC, CI helpers
contracts/   openapi.json (exported from FastAPI), the ONLY link between backend and frontend
docs/        ADRs (PRD.md, ARCHITECTURE.md and DESIGN.md are at the root)
```

## Hard rules
- **No cross-folder imports** between `backend/`, `frontend/`, `infra/`. Integrate only through `contracts/openapi.json`.
- **Typed endpoints, committed spec:** every FastAPI endpoint uses Pydantic request and response models and a clean `operation_id`. After any API change, run `npm run api:sync` (exports the spec, regenerates the client) and commit `contracts/openapi.json` and `frontend/src/api/` together. Never hand-edit generated files.
- **Config via environment variables only.** Never hardcode URLs, secrets, or paths. Update `.env.example` when adding one.
- **Never commit secrets.**
- Each folder owns its dependencies, Dockerfile, tests, and CI job.

## Commands
Fill in as the project is scaffolded.
- Frontend (pnpm): `npm run dev`, `npm run test`, `npm run lint`, `npm run build`, `npm run e2e`
- Database (from `infra/`): `docker compose up -d --wait db`
- Backend (from `backend/`, uv): `uv sync`, `uv run dmc-migrate upgrade`, `uv run uvicorn app.main:app --reload`, `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run lint-imports`
- API sync (spec export + hey-api client): `npm run api:sync` from `frontend/`
- Everything: `docker compose up` from `infra/`

## Conventions
- Conventional commits (`feat(frontend): ...`, `fix(backend): ...`). Scope = folder.
- Commit and push directly to `main`; no feature branches or PRs. Keep commits small, and leave `main` green after each one.
- Build in vertical slices: one feature end to end (data model, API, UI, tests), following `docs/ROADMAP.md`.
- Every slice includes tests; user-facing changes include all UI states (loading, empty, error).
- Permissions are enforced in the backend. The UI only reflects them.
- Prefer boring, well-known solutions. Ask before adding a new dependency.

## Before finishing any task
1. Lint and tests pass for every folder you touched.
2. No cross-folder imports, no hardcoded config.
3. If you changed an API, `contracts/openapi.json` is exported and the hey-api client regenerated.
4. If you made a design decision, add a short note in `docs/adr/`.

## Frontend and backend work
- Frontend: follow `.github/instructions/frontend.instructions.md` and `DESIGN.md`.
- Backend: follow `.github/instructions/backend.instructions.md`.
