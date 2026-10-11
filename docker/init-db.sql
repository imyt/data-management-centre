-- Initialize Postgres Extensions for Enterprise Data Management Centre (PostgreSQL 18+)
-- Native uuidv7() is built into PostgreSQL 18 core (no uuid-ossp required)
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
