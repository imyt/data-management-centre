# Enterprise Data Management Centre

A desktop-first enterprise data governance platform built for organizational stewardship, metamodel extensibility, immutable asset versioning, and compliance accountability.

---

## Architecture Overview

* **Database:** **PostgreSQL 18** (Docker image: `postgres:18-alpine`)
  * Native `uuidv7()` primary keys embedded directly in core (zero `uuid-ossp` extension dependency; eliminates B-tree index fragmentation).
  * Native `pg_trgm` GIN indexing for sub-100ms global search and `Cmd+K` command palette queries.
  * Zero external Redis/Valkey cache: ACID draft locking and background jobs handled directly in PostgreSQL.
* **Backend:** **Python 3.12+ / FastAPI**
  * SQLAlchemy 2.0 Async declarative ORM (`Mapped[]`, `mapped_column`, native `uuidv7()`).
  * Alembic migration engine with PostgreSQL 18 baseline.
  * Stateless JWT authentication supporting RACI personas (`DATA_STEWARD`, `BUSINESS_OWNER`, `APP_OWNER`, `DATA_CONSUMER`, `PLATFORM_ADMIN`).
  * Asset Head / Version decoupling with exclusive draft concurrency leases and side-by-side visual diff generator.
* **Frontend:** **React 19 + TypeScript (Strict SPA) + Vite**
  * **Tailwind CSS v4** (`@tailwindcss/vite` with `@theme` and zero-config CSS variables).
  * Consolidated **`radix-ui`** package (single package replacing fragmented `@radix-ui/react-*` components).
  * Desktop 3-pane split-view workspace:
    * Left pane: Collapsible Community/Domain organizational tree.
    * Center pane: High-density Asset data grid with status badges, version chips, and lock indicators.
    * Right pane: Inspect / Action drawer (Overview, Live Draft Editor with lease lock, Visual Diff Viewer, Audit Ledger).
  * Global `Cmd+K` / `Ctrl+K` command palette (`cmdk`).
  * Live persona switcher for immediate role testing.

---

## Quickstart

### 1. Start PostgreSQL 18 Container
```bash
docker compose up -d db
```

### 2. Run Backend & Migrations
```bash
cd backend
# Create virtual environment and install dependencies
uv venv
uv pip install -e .

# Run Alembic migrations to apply PostgreSQL 18 schema
.venv\Scripts\alembic upgrade head

# Seed initial roles, personas, metamodel, and taxonomy
.venv\Scripts\python -m app.services.seed_data

# Run automated test suite
.venv\Scripts\pytest -v

# Start FastAPI development server (http://localhost:8000/docs)
.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

### 3. Run Frontend
```bash
cd ../frontend
npm install
npm run dev
# App will launch on http://localhost:5173
```

---

## Seed Accounts (Password: `password123`)
* `admin@governance.com` — Platform Administrator
* `steward@governance.com` — Data Steward
* `business.owner@governance.com` — Business / Domain Owner
* `app.owner@governance.com` — Application / System Owner
* `consumer@governance.com` — Data Consumer
