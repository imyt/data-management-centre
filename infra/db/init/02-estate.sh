#!/usr/bin/env bash
# The estate sample database (ADR 0004 §8), kept apart from DMC's schema. Safe to run again, so
# a volume created before this script existed can pick it up:
#   docker compose exec -T db bash /docker-entrypoint-initdb.d/02-estate.sh
#   dmc_migrator  owns estate; `dmc-seed` creates its sample tables as this role.
#   dmc_harvest   read-only: SELECT on every table the owner creates, nothing else.
# The tables themselves come from backend/app/estate.py.
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
  -v harvest_password="${DMC_HARVEST_PASSWORD:-dmc_harvest}" <<'SQL'
SELECT 'CREATE ROLE dmc_harvest LOGIN PASSWORD ' || quote_literal(:'harvest_password')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'dmc_harvest')
\gexec
ALTER DATABASE estate OWNER TO dmc_migrator;
SQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname estate <<'SQL'
REVOKE ALL ON DATABASE estate FROM PUBLIC;
GRANT CONNECT ON DATABASE estate TO dmc_harvest;
GRANT USAGE ON SCHEMA public TO dmc_harvest;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO dmc_harvest;
ALTER DEFAULT PRIVILEGES FOR ROLE dmc_migrator IN SCHEMA public GRANT SELECT ON TABLES TO dmc_harvest;
SQL
