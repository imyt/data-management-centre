# DMC build roadmap

**Read with:** [PRD.md](../PRD.md), [ARCHITECTURE.md](../ARCHITECTURE.md), [DESIGN.md](../DESIGN.md) | **Status:** draft | **Date:** 2026-10-18

DMC is built in thin vertical slices: data model, API, UI and tests for one capability at a time (`CLAUDE.md`). Slices follow the governance loop **Know → Assess → Act → Assure**. The first milestone closes that loop for one control on a local machine. After that, slices broaden coverage.

Runtime decisions (local Postgres 18, environments, how frontend and backend pair, migrations, dev authentication, seed data) are in [ADR 0004](adr/0004-environments-database-and-frontend-backend-pairing.md).

---

## Where we are

| Area | State |
|---|---|
| Frontend | Vite + React, tokens, shadcn primitives and the DMC patterns from DESIGN.md (`AppShell`, `PortalHeader`, `DetailSplit`, `EntityHeader`, `StageTracker`, `StatusBadge`, `ExplainWhy`, `ConfirmWithReason`, states), `/gallery` with screenshot and axe tests |
| Backend | One app with `core/` and `modules/` (ADR 0003); errors, request IDs, cursor paging; `examples` reference module; import-linter |
| Contract | `contracts/openapi.json` and a generated hey-api client; a test fails if the spec is stale |
| CI | Path-filtered GitHub Actions for backend and frontend |
| Missing | Database, migrations, worker and job queue, response envelope, RFC 9457 errors, auth, audit, `infra/`, Dockerfiles, mypy |

---

## Phase 0: Foundations

Goal: everything later slices depend on, already working the way it will in every environment. No product screens yet. Each row is roughly one commit.

| # | Work | Source |
|---|---|---|
| 0.1 | `infra/compose.yaml` with `postgres:18`; `infra/db/init/` for roles, the `dmc` and `estate` databases, and module schemas | ADR 0004 §1–2 |
| 0.2 | `app/core/db.py`: SQLAlchemy 2 + psycopg 3, a session per request, `uuidv7()` primary keys; `DMC_DATABASE_URL`, `DMC_MIGRATION_DATABASE_URL`; pytest on Postgres with rollback per test; Postgres 18 service in CI | ADR 0004 §1–2 |
| 0.3 | Alembic in `backend/migrations/`, `dmc-migrate`, revision check at start-up; upgrade, downgrade and upgrade again in CI | ARCHITECTURE §13; ADR 0004 §3 |
| 0.4 | Response envelope `{data, allowed_actions, meta}` and a test that every route uses it; RFC 9457 problem details replace `ErrorResponse` | ARCHITECTURE §8; ADR 0003 "not done yet" |
| 0.5 | `audit` module: hash-chained `audit_event`, written in the same transaction as the change, with `reason` | FR-U1; ARCHITECTURE §9 |
| 0.6 | Outbox and job queue: `outbox_event`, a job table with `SKIP LOCKED`, worker process and scheduler, `/api/v1/jobs/{id}`, `202` + job id, `Idempotency-Key` | ARCHITECTURE §3, §5, §8 |
| 0.7 | `identity` module, first part: users, roles, domain scopes; dev authentication with a persona switcher; scope and role checks in services; `allowed_actions` computed from the same rules | FR-D1 (shape); ADR 0004 §7 |
| 0.8 | `GET /api/v1/meta`, contract hash; API base URL from runtime `/config.json` (same-origin by default), Vite `/api` proxy, `VITE_API_BASE_URL` removed; environment badge and update banner in `PortalHeader` | ADR 0004 §4–5 |
| 0.9 | Frontend: settle the router (React Router 8 is installed), add the hey-api TanStack Query plugin, wire `AppShell` navigation (Inbox, Assets, Applications, Controls, Reports) with empty screens | ARCHITECTURE §10, §14 |
| 0.10 | Structured JSON logs with request and job IDs; health for API and worker | ARCHITECTURE §12 |
| 0.11 | mypy in CI; Dockerfiles for the backend (API and worker share one image) and the frontend (nginx serving the build and proxying `/api/`); `docker compose up` runs everything | ARCHITECTURE §13; ADR 0004 §4 |
| 0.12 | `dmc-seed` with personas and reference data; the `estate` sample tables | ADR 0004 §8 |

**Exit:** `docker compose up` from `infra/` runs Postgres, API, worker and frontend on one origin. CI is green with Postgres. A test write produces an audit event and an outbox event in one transaction, and a job runs in the worker and reports through `/jobs/{id}`.

---

## Phase 1: Know

| Slice | Delivers | Requirements |
|---|---|---|
| **1. Reference data** | Domains, data categories, regions, retention policies, purposes; the scope selector filters by domain | FR-D2 |
| **2. Applications** | Register applications with environments and data stores; Applications list and detail with `StageTracker` (Know stage) | FR-K1, FR-K2 |
| **3. Assets and ownership** | Assets and data elements; declare category, business context, stored flag and retention; assign, confirm, reassign or dispute owners and stewards; **Inbox v1** (ownership confirmations due) | FR-K5, FR-K6 (declared PII, CDE flag), FR-K10, FR-I1 |
| **4. Harvest** | `connectors` module with a Postgres harvest adapter, run as jobs on a schedule and on demand; snapshots and physical objects; harvest status and failures on the data store; map objects to assets and elements, and flag unmapped objects | FR-K3, FR-K4, FR-D3 (first part) |

**Exit:** an Application Owner registers an application whose store is the local `estate` database, harvest fills it in, and a Data Owner confirms ownership of its assets from the Inbox.

## Phase 2: Assess

| Slice | Delivers | Requirements |
|---|---|---|
| **5. Policies and controls** | Policies, the control library, versioned rules with selectors; applied controls derived from attributes and recomputed on change, each with a reason ("Why?" through `ExplainWhy`); Controls area | FR-P1–P4, FR-A5 |
| **6. Evaluation engine** | Evaluation runs on events, schedules and on demand; append-only results keyed by applied control, subject, fact snapshot and rule version; `error` kept separate from `fail`; stale results flagged; first rule types `retention_window`, `harvest_fresh` and `declaration_complete`; Assess stage on asset and application detail | FR-A1–A3, FR-A7, FR-S4 |

**Exit:** a stored asset in `estate` with rows older than its retention policy shows a failing `retention_window` result, with measured value, threshold, reason, facts and freshness.

## Phase 3: Act and Assure

| Slice | Delivers | Requirements |
|---|---|---|
| **7. Actions and verification** | Actions raised from failing results; state machine; "fixed, awaiting verification" triggers an on-demand evaluation; a passing result verifies the action and a failing one reopens it; **Inbox v2** (actions, failing controls) | FR-C1, FR-C2, FR-S1, FR-I1 |
| **8. Exceptions** | Request, approve or reject (with `ConfirmWithReason`), expiry; results under an active exception show as "excepted" | FR-C3, FR-C8 |
| **9. Recurrence and history** | Results history per applied control; recurrence detected after verification; Assure stage on detail views | FR-S2, FR-S4 |

### Milestone A: the loop closes locally

On a fresh `docker compose up` with seed data, in an automated Playwright test that switches personas:

1. **Know:** the application and its `estate` store are registered and harvested; the Data Owner confirms ownership.
2. **Assess:** `retention_window` fails on an asset with overdue records.
3. **Act:** an action is raised and assigned to the Application Owner, who deletes the old rows and marks it fixed.
4. **Assure:** re-evaluation passes and the action becomes verified. The audit trail shows every step with its reason.

## Phase 4: First shared environment

| Work | Notes |
|---|---|
| Choose hosting and infrastructure-as-code | ADR 0004 "not decided here" |
| OIDC with the corporate identity provider; roles and scopes from groups | FR-D1; ADR 0004 §7 |
| Provision `dev` and `staging`: each with managed Postgres 18, secrets, and frontend + API + worker + migration step from one SHA | ADR 0004 §4 |
| Pipeline: commits to `main` deploy to dev automatically; the same build is promoted to staging and then production after approval | Build once, promote |
| Metrics (API latency, queue depth and age, evaluation duration and error rate, harvest success, stale results), alerts, a backup and restore runbook | ARCHITECTURE §12 |
| Lighthouse CI budgets | PRD §8; ARCHITECTURE §13 |

**Exit:** Milestone A runs in staging against its own database, with sign-in through the identity provider.

## Phase 5: Broaden coverage

Ordered by how much of the PRD each slice unlocks. Each one is still a vertical slice.

| Slice | Requirements |
|---|---|
| **10. Search and command palette** (⌘K) | FR-I2 |
| **11. Integrations, declared** with source, target, datasets, method and regions; `declared_vs_observed` for stores and assets | FR-K7, FR-A4 |
| **12. Business processes** and process owner confirmation | FR-K9 |
| **13. PII scanning and classification suggestions**, `classification_vs_pii`, `pii_masked_nonprod` | FR-K6, FR-K11, FR-A4 |
| **14. CDEs and data quality**: thresholds, `dq_threshold`, CDEs without monitoring | FR-K6, FR-A4 |
| **15. Lineage and blast radius** | FR-K12, FR-A6 |
| **16. Reports**: posture over time, coverage, remediation, exceptions | FR-R1, FR-R2, FR-R4, FR-R5 |
| **17. Notifications**: in-app, email digests, preferences | FR-I3; ARCHITECTURE §11 |
| **18. Declaration re-confirmation and expiry** | FR-K13 |
| **19. Security controls**: `encryption_at_rest`, `access_review_current` | FR-A4 |
| **20. Access requests** | FR-C4 |
| **21. Change reviews** | FR-C5 |
| **22. Attestation campaigns** | FR-C6 |
| **23. Bulk actions** with impact preview | FR-C7 |
| **24. Observed flows**, `pii_masked_egress` | FR-K8, FR-A4 |
| **25. Audit packs, top risks, scheduled digests** | FR-R3, FR-R6, FR-R7, FR-U2 |
| **26. Cross-border transfers**: `cross_border_basis` and transfer approval | FR-A4; Data Owner journey step 8 |
| **27. Attributed posture movement** | FR-S3 |
| **28. Decommissioning** | Application Owner journey step 11 |

---

## Decision checkpoints

| Open item | Source | Needed by |
|---|---|---|
| Frontend router (React Router or TanStack Router) | ARCHITECTURE §14 | Phase 0, row 0.9 |
| Retention policy source (central library or per data category) | PRD §10, ARCHITECTURE §14 | Slice 1 (the reference data model); slice 6 at the latest |
| Hosting and infrastructure-as-code | ADR 0004 | Phase 4 |
| Where evidence files live | ADR 0004 | Slice 22 (attestations) or slice 25 (audit packs) |
| Observed-flow sources | PRD §10, ARCHITECTURE §14 | Slice 24 |
| Regulations in scope, which set transfer boundaries | PRD §10, ARCHITECTURE §14 | Slice 26 |
| Trust score definition | PRD §10 | Not scheduled |

Each decision is recorded in `PRD.md`, `ARCHITECTURE.md` or `DESIGN.md` in the same change (`CLAUDE.md`), plus an ADR when it is a technical choice.

## Working rules for every slice

- Work is committed and pushed directly to `main`, in small conventional commits. A slice may take several commits, and each one leaves `main` green.
- A slice includes: migration, module code behind its `service.py`, API with an explicit `operation_id` and the response envelope, `npm run api:sync`, a feature screen built only from `components/patterns` with every state (loading, empty, error, no access, not found), and tests.
- Every write goes through a service that checks role and scope, writes the audit event (with a reason for risk decisions), and emits outbox events in the same transaction.
- Seed data grows with each slice, so Milestone A can always be shown from a fresh `docker compose up`.
