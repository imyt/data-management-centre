# Local infrastructure

Docker Compose for local development (ADR 0004). It runs PostgreSQL 18 on its own for development, or the whole stack: database, a one-shot migration step, API, worker and web.

```bash
cp .env.example .env                  # optional; change DMC_DB_PORT if 5432 is taken
docker compose up -d --wait db        # start Postgres 18 and wait until it is ready
docker compose exec db psql -U postgres -d dmc
docker compose down                   # stop; add -v to delete the data and re-run the init scripts
```

On first start, `db/init/` creates:

| Name | What |
|---|---|
| `dmc_migrator` | Owns the databases; runs migrations (DDL) |
| `dmc_app` | Runtime role for the API and worker; data access only |
| `dmc` | Application database |
| `dmc_test` | Database used by the backend tests |
| `estate` | Sample application data store that harvest reads |

Parallel worktrees each get their own test database, so their test runs and migrations never collide:

```bash
./db/create-database.sh dmc_test_<task>    # then point DMC_TEST_* in that worktree's backend/.env at it
```

## The whole stack

```bash
cd infra
docker compose up --build             # db, migrate (once), api, worker, web
```

| Service | What | Host port (variable) |
|---|---|---|
| `db` | Postgres 18 | 5432 (`DMC_DB_PORT`) |
| `migrate` | One-shot `dmc-migrate upgrade` as `dmc_migrator`; `api` and `worker` start only after it succeeds (ADR 0004 §3) | none |
| `api` | `uvicorn app.main:app` as `dmc_app` | 8100 (`DMC_API_PORT`) |
| `worker` | `dmc-worker`, same image as `api` | none |
| `web` | nginx: the Vite build, `/api/` proxied to `api`, `/config.json` written from the environment | 8080 (`DMC_WEB_PORT`) |

Open <http://localhost:8080>; check the pairing with `curl localhost:8080/api/v1/meta`. The defaults for the API and web ports avoid 8000, which `uvicorn --reload` and the Vite proxy use on the host, so the stack can run beside a dev server. Set the variables in `infra/.env` or the shell if a port is taken.

- **One image for the API and worker.** `backend/Dockerfile` builds it; the command picks the process. `DMC_COMMIT` (a build arg) is the git SHA that `/api/v1/meta` reports.
- **Nothing environment-specific is in the frontend image** (ADR 0004 §4). Its `/config.json` comes from `DMC_API_BASE_URL` when the container starts, empty for same-origin `/api/`. Where the API has its own URL, set it there and add the web origin to the API's `DMC_CORS_ORIGINS`.
- **Both images build from the repository root** (`docker build -f backend/Dockerfile .`), because the frontend bundle embeds the hash of `contracts/openapi.json`.
- The compose environment is `dev` with dev authentication, so the persona switcher works. Seed personas with `docker compose run --rm api dmc-seed` once `dmc-seed` loads data (row 0.12).
- To run several copies side by side (for example from parallel worktrees), give each its own project name and ports: `docker compose -p dmc2 up` with `DMC_DB_PORT`, `DMC_API_PORT` and `DMC_WEB_PORT` set.
