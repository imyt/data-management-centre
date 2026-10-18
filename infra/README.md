# Local infrastructure

Docker Compose for local development (ADR 0004). Today it runs PostgreSQL 18; later rows of the roadmap add the API, worker and frontend.

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
