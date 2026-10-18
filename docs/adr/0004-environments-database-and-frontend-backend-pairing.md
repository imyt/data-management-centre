# ADR 0004: Environments, the database, and frontend/backend pairing

- Status: accepted
- Date: 2026-10-18

## Context

The build starts now (see [ROADMAP.md](../ROADMAP.md)). Three needs shape the runtime setup:

1. **A local database now.** Developers need a real database on their machine from the first slice that persists data.
2. **Several environments later.** DMC will run in more than one environment (dev, staging, production), each with its own database and secrets.
3. **Pairing.** Each environment's frontend must talk to that environment's backend, and only that one. A staging UI must never reach a production API, or the reverse.

What exists today:

- `ARCHITECTURE.md` §1–§3 fixes the shape: one frontend, one backend codebase, one PostgreSQL database with a schema per module, and a worker from the same codebase using a Postgres job queue. The frontend is a static build "served behind the corporate gateway".
- The backend reads `DMC_*` settings (`environment`, `log_level`, `cors_origins`) and has no database settings yet.
- The frontend reads `VITE_API_BASE_URL` in `src/lib/api-config.ts`. Vite inlines `VITE_*` variables **at build time**, so the backend's address is baked into the bundle. That forces one frontend build per environment, and a build can be deployed against the wrong API by mistake.
- The design relies on Postgres features: schemas per module, `jsonb`, `SELECT … FOR UPDATE SKIP LOCKED` for jobs, append-only tables, and a hash-chained audit trail.

## Decisions

### 1. Local database: PostgreSQL 18 in Docker Compose, not SQLite

- `infra/compose.yaml` runs `postgres:18`. Postgres is the only infrastructure dependency (`ARCHITECTURE.md` §1): no Redis, and no message broker.
- Version 18 because the design uses its features directly:
  - built-in `uuidv7()` for primary keys, which are time-ordered, so append-heavy tables (`evaluation_result`, `audit_event`, `outbox_event`, the job table) insert in index order and can be partitioned by time;
  - `OLD`/`NEW` in `RETURNING`, which gives the audit trail's `before` and `after` in one statement;
  - asynchronous I/O and B-tree skip scan, for reporting reads.

  New clusters also have data checksums on by default.
- The 18 image keeps its data under a versioned path. Mount the volume at `/var/lib/postgresql`, not at `/var/lib/postgresql/data` as older images expected.
- Every environment runs the same major version. The target managed Postgres offers 18 (confirmed 2026-10-18), so local, CI and deployed environments all run 18.
- Locally there is one database, `dmc`, with one schema per backend module (`identity`, `inventory`, `policy`, `evaluation`, `workflow`, `audit`, …), the same layout as every other environment.
- A second local database, `estate`, holds a small sample data set (applications' tables with ages and row counts). Harvest and retention checks run against it, so the full Know → Assess → Act → Assure loop works offline.
- SQLite is ruled out. It lacks schemas, `SKIP LOCKED`, `jsonb` operators and roles, so tests would pass against a database we never ship.
- Tests run against real Postgres: the compose service locally and a Postgres 18 service container in CI. Each test runs in a transaction that is rolled back at the end.

### 2. Database access: one URL per environment, two roles

- `DMC_DATABASE_URL` is the runtime connection (SQLAlchemy 2.x with psycopg 3), used by both the API and the worker. `DMC_MIGRATION_DATABASE_URL` is used only by the migration step.
- **Runtime role:** read and write data only (DML) on the module schemas. **Migration role:** owns the schemas and runs DDL. The app never connects as the migration role.
- Locally, `infra/db/init/` creates the roles and the `dmc`, `dmc_test` and `estate` databases when the container first starts, and sets default privileges so every schema and table the migration role creates is usable by the runtime role. In deployed environments, infrastructure code does the same. Module schemas themselves are created by migrations, so a new module needs no change to the init scripts.
- The architecture rule that no module writes another module's tables is enforced in code (`import-linter`, service interfaces), not by one database role per module. Splitting roles per module is deferred until a module actually becomes a service.

### 3. Migrations: Alembic, run as a separate step

- One Alembic environment in `backend/migrations/` (`ARCHITECTURE.md` §4). Each migration touches the schemas of the module it belongs to.
- In deployed environments, migrations run as a **pre-deploy step** (`dmc-migrate`, with the migration role) before new API and worker processes start. Neither the API nor the worker migrates when it starts. On start-up, each checks that the database revision matches the code and refuses to run if it doesn't.
- CI runs `upgrade head`, then `downgrade base`, then `upgrade head` again on an empty Postgres 18 (`ARCHITECTURE.md` §13). It also checks that the models match the migrations.
- Schema changes are backward compatible with the previous release (expand, then contract), so rolling back the app does not require rolling back the database.

### 4. Pairing: one origin per environment

Each environment is one unit: **frontend + API + worker + migration step + its own Postgres and secrets**, all deployed from the same commit SHA.

- The corporate gateway, or a small nginx container in front of the static build, serves the SPA and routes `/api/` to the API in **the same environment**. The browser only ever sees one origin, for example `https://dmc-staging.<corp>/` and `https://dmc-staging.<corp>/api/v1/...`.
- The generated client uses a **relative base URL**. The frontend never knows a backend address, so it cannot point at the wrong one. `VITE_API_BASE_URL` is removed.
- **Locally**, the Vite dev server proxies `/api` to `http://localhost:8000`, so local setup has the same shape as deployed environments and CORS isn't needed. `DMC_CORS_ORIGINS` stays as an escape hatch, empty by default.
- **Build once, promote.** Nothing environment-specific is baked into the bundle, so the same frontend build and the same backend image move from dev to staging to production. Builds are tagged with the git SHA.
- If a value other than the API address ever has to differ per environment in the UI (for example the identity provider's client ID), the gateway or nginx container serves `/config.json` from environment variables and the app loads it before mounting. It never goes into a `VITE_*` variable.

### 5. Pairing check: `GET /api/v1/meta`

The API exposes an unauthenticated `meta` endpoint (`operation_id: getMeta`), next to `health` in `app/core`:

```json
{ "environment": "staging", "version": "0.4.0", "commit": "24a18c3", "contract": "sha256:…" }
```

- `contract` is the hash of the `contracts/openapi.json` the API was built from. The frontend build embeds the hash of the spec its client was generated from.
- On load, the frontend calls `meta`. If the hashes differ, it shows a banner that can't be dismissed: "DMC has been updated. Reload to continue." This catches a stale cached bundle and half-finished rollouts.
- Outside production, `PortalHeader` shows the environment name as a persistent badge, so nobody mistakes staging for production.
- Like `health`, `meta` is a platform endpoint and is exempt from the response envelope (`ARCHITECTURE.md` §8). The envelope contract test lists both as the only exceptions.

### 6. Environment-aware configuration and its guardrails

- `DMC_ENVIRONMENT` gains `dev` alongside `local`, `test`, `staging` and `production`.
- Settings validation fails at start-up for unsafe combinations: dev authentication, seed data or debug payload logging in `staging` or `production`; and a missing database URL anywhere except unit tests.
- Secrets come from the corporate secrets store as environment variables. `.env` files are for local use only, and every variable stays listed in `.env.example`.

### 7. Authentication during development: a dev identity provider behind the real interface

- `DMC_AUTH_MODE=dev|oidc`. In `dev` mode, a persona switcher in the UI (shown only in `local` and `dev`) sets a request header that picks one of the seeded users from `PRD.md` §2: Data Owner, Application Owner, Data Steward, Process Owner, Governance team, Leadership and Auditor. In `oidc` mode, bearer tokens are validated against the corporate identity provider.
- Both modes produce the same principal (user ID, roles, domain scopes), so `allowed_actions`, scope checks, the audit trail and the Inbox are built and tested against the real shape from the first slice.
- `dev` mode can only start in `local`, `test` or `dev` (decision 6).

### 8. Seed data

- `dmc-seed` loads a small, realistic data set (users and roles, domains, data categories, regions, retention policies, a few applications and assets, and the `estate` sample tables). It goes through the module services rather than raw SQL, so seeded data follows the same rules and writes the same audit events.
- `dmc-seed` refuses to run in `staging` or `production`.

## Consequences

- Developers need Docker for the local database. `docker compose up db` from `infra/` is the only prerequisite beyond `uv` and `pnpm`.
- `frontend/src/lib/api-config.ts`, `src/env.d.ts`, `.env.example` and `vite.config.ts` change: the base URL becomes relative and the dev server gets an `/api` proxy. This replaces the `VITE_API_BASE_URL` part of ADR 0002 decision 6.
- The unit of deployment is the environment, not the app. A frontend and a backend from different commits never run together in a deployed environment.
- Each environment has its own database, so moving data between environments is always a deliberate step. Production data never goes to lower environments.

## Not decided here

- Hosting (Kubernetes or a managed container service) and the infrastructure-as-code tool. Deployed databases are provisioned on the managed Postgres 18.
- Where evidence files live. `ARCHITECTURE.md` stores evidence as a `uri` plus `sha256`, and the storage behind the URI is chosen when attestations and audit packs need it.
