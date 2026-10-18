#!/usr/bin/env bash
# Create another database with the same owner and grants as dmc and dmc_test, e.g. a test database
# per worktree so parallel test runs (and their migrations) never touch each other:
#   ./db/create-database.sh dmc_test_jobs        (run from infra/, with the db service up)
# Then point DMC_TEST_DATABASE_URL and DMC_TEST_MIGRATION_DATABASE_URL in backend/.env at it.
set -euo pipefail

name="${1:?usage: $0 DATABASE_NAME}"
if [[ ! "$name" =~ ^[a-z_][a-z0-9_]*$ ]]; then
  echo "Database name must be lowercase letters, digits and underscores." >&2
  exit 2
fi
cd "$(dirname "$0")/.."

psql() { docker compose exec -T db psql -v ON_ERROR_STOP=1 -U postgres "$@"; }

if [[ -n "$(psql -d postgres -Atc "SELECT 1 FROM pg_database WHERE datname = '$name'")" ]]; then
  echo "Database $name already exists."
  exit 0
fi
psql -d postgres -c "CREATE DATABASE $name OWNER dmc_migrator"
psql -d "$name" <<SQL
REVOKE ALL ON DATABASE $name FROM PUBLIC;
GRANT CONNECT, TEMPORARY ON DATABASE $name TO dmc_app;
ALTER DEFAULT PRIVILEGES FOR ROLE dmc_migrator GRANT USAGE ON SCHEMAS TO dmc_app;
ALTER DEFAULT PRIVILEGES FOR ROLE dmc_migrator
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO dmc_app;
ALTER DEFAULT PRIVILEGES FOR ROLE dmc_migrator GRANT USAGE, SELECT ON SEQUENCES TO dmc_app;
ALTER DEFAULT PRIVILEGES FOR ROLE dmc_migrator GRANT EXECUTE ON FUNCTIONS TO dmc_app;
SQL
echo "Created $name."
