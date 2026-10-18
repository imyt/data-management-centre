#!/usr/bin/env bash
# Runs once, when the db volume is first created (ADR 0004 §1–2).
#   dmc_migrator  owns the databases and runs migrations (DDL).
#   dmc_app       runtime role for the API and worker: data access only (DML).
#   dmc           application database; dmc_test is the same for pytest.
#   estate        sample "application data store" that harvest reads (seeded by dmc-seed).
# Module schemas are created by Alembic migrations; default privileges below grant them to dmc_app.
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
  -v migrator_password="$DMC_MIGRATOR_PASSWORD" \
  -v app_password="$DMC_APP_PASSWORD" <<'SQL'
CREATE ROLE dmc_migrator LOGIN PASSWORD :'migrator_password';
CREATE ROLE dmc_app LOGIN PASSWORD :'app_password';
CREATE DATABASE dmc OWNER dmc_migrator;
CREATE DATABASE dmc_test OWNER dmc_migrator;
CREATE DATABASE estate;
SQL

for db in dmc dmc_test; do
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$db" -v db="$db" <<'SQL'
REVOKE ALL ON DATABASE :"db" FROM PUBLIC;
GRANT CONNECT, TEMPORARY ON DATABASE :"db" TO dmc_app;
ALTER DEFAULT PRIVILEGES FOR ROLE dmc_migrator GRANT USAGE ON SCHEMAS TO dmc_app;
ALTER DEFAULT PRIVILEGES FOR ROLE dmc_migrator
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO dmc_app;
ALTER DEFAULT PRIVILEGES FOR ROLE dmc_migrator GRANT USAGE, SELECT ON SEQUENCES TO dmc_app;
ALTER DEFAULT PRIVILEGES FOR ROLE dmc_migrator GRANT EXECUTE ON FUNCTIONS TO dmc_app;
SQL
done
