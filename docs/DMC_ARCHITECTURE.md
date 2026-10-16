# Data Management Centre (DMC) — Architecture

**Version:** 3.1 (draft) | **Companion to:** DMC_PRD.md | **Stack:** React, FastAPI, PostgreSQL | **Delivery:** internal build

---

## 1. Principles

1. **Control plane, not data plane.** DMC stores metadata, evaluations, findings and evidence. It never stores the governed data.
2. **Modular monolith first.** One deployable, one module per bounded context. Split out services only on measured need.
3. **Postgres is the source of truth.** The graph and reports are derived.
4. **Event-driven core.** State changes emit events through a transactional outbox.
5. **Everything is versioned.** Policies, regulations and obligations are versioned; evaluations pin the version they used.
6. **Provable by design.** Append-only audit log, hashed immutable evidence, signed attestations.

## 2. System Context

```
 Users (React SPA)            External systems
 Owners, Stewards,            Catalogs · Lineage · DQ tools ·
 Compliance, Execs            Model registry · IdP · Jira/SNOW (links)
        |                                  |
        v                                  v
 +--------------------------------------------------------------+
 |                    DMC (FastAPI modular monolith)            |
 |                                                              |
 |  API layer (REST + webhooks)   Auth (OIDC, RBAC/ABAC)        |
 |  ------------------------------------------------------------|
 |  Registry | Obligation | Policy | Assessment | Operations     |
 |  Risk&Trust | Graph (derived) | Workflow | Reporting          |
 |  ------------------------------------------------------------|
 |  Integration layer (connectors) | Event bus (outbox)         |
 +--------------------------------------------------------------+
        |                |                       |
        v                v                       v
   PostgreSQL       Object storage          Cache / queue
  (schema per      (evidence files)        (Redis, later
    context)                                Kafka/NATS)
```

## 3. Layering

Not a strict top-down stack. Dependencies flow through the **event bus**:

```
 Dashboards (React)
        |
 API layer
        |
 Workflow & Orchestration <----+
        |                      |
 Governance Operations         |  events
        |                      |
 Compliance Intelligence ------+
        |
 Policy Engine
        |
 Governance Knowledge (Registry)
        |
 Integration layer  <---  Source systems
```

Rules:
- Modules call each other only through public module interfaces or events, never through another module's tables.
- Registry events (e.g. Data Product Published) trigger Policy evaluation; evaluation results trigger Operations and Workflow.

## 4. Bounded Contexts and Modules

| Module | Responsibility | Owns (schema) |
|---|---|---|
| Registry | Assets, glossary, CDEs, ownership, classifications, jurisdictions | `registry` |
| Obligation | Regulations, controls, obligations | `obligation` |
| Policy | Policy rules, applicability, exceptions, versions | `policy` |
| Assessment | Evaluation runs and results | `assessment` |
| Operations | Findings, cases, tasks, evidence, attestations, waivers | `ops` |
| Workflow | Playbooks, runs, steps | `workflow` |
| Risk & Trust | Risk rollups; trust score (definition deferred) | `trust` |
| Graph | Derived relationships for impact analysis | `graph` |
| Reporting | Read models for dashboards | `reporting` |
| Platform | Auth, audit log, outbox, notifications, connectors | `platform` |

## 5. Domain Model

**Aggregate roots:** GovernanceAsset, BusinessTerm, CriticalDataElement, Regulation, Control, Obligation, PolicyRule, Exception, Evaluation, Finding, Case, Evidence, Attestation, Playbook

**Value objects:** Classification, Jurisdiction, Severity, Ownership

**Canonical chain:**
Governance Asset → Obligation → Policy Rule → Evaluation → Finding → Case → Evidence → Attestation

Key relationships:
- Obligation belongs to a Regulation and maps to one or more Controls.
- PolicyRule implements an Obligation; applicability selects governed assets.
- Evaluation references one asset and one pinned PolicyRule version.
- Finding is created from a failed Evaluation; one open Finding per (asset, rule).
- Case groups Findings; Evidence attaches to Cases; Attestation closes them.

## 6. Data Model (PostgreSQL)

All tables carry `created_at`, `updated_at`, `created_by`, and `version` where relevant. IDs are UUIDs.

```sql
-- registry
governance_asset(id, type, name, domain, owner_id, steward_id,
                 classification, jurisdictions text[], source_system,
                 external_ref, status, attributes jsonb)
business_term(id, name, definition, status, domain, owner_id)
critical_data_element(id, name, term_id, description, criticality)
asset_cde(asset_id, cde_id)

-- obligation
regulation(id, name, jurisdiction, version, effective_from, effective_to, status)
control(id, name, description, version, status)
obligation(id, regulation_id, title, description, version, status)
obligation_control(obligation_id, control_id)

-- policy
policy_rule(id, key, version, status, obligation_id,
            definition jsonb, applicability jsonb, severity,
            effective_from, effective_to)         -- unique(key, version)
policy_exception(id, rule_id, asset_id, justification,
                 approved_by, expires_at, status)

-- assessment
evaluation(id, asset_id, rule_id, rule_version, result,
           inputs jsonb, trigger_event_id, evaluated_at)

-- ops
finding(id, asset_id, rule_id, obligation_id, severity, status,
        first_seen, last_seen, sla_due, assignee_id)
case_(id, title, status, priority, owner_id, playbook_run_id, opened_at, closed_at)
case_finding(case_id, finding_id)
task(id, case_id, title, assignee_id, due_at, status)
evidence(id, case_id, kind, uri, sha256, validated_by,
         validated_at, valid_until, retention_until)             -- immutable after insert
attestation(id, case_id, attested_by, statement,
            evidence_hashes text[], signature, attested_at)  -- immutable

-- workflow
playbook(id, key, version, definition jsonb, status)
playbook_run(id, playbook_id, trigger_event_id, state jsonb, status)

-- platform
audit_log(id, actor, action, entity_type, entity_id,
          before jsonb, after jsonb, at)             -- append-only
outbox_event(id, type, payload jsonb, created_at,
             published_at, attempts)
connector(id, kind, config jsonb, status)
connector_run(id, connector_id, started_at, finished_at, status, stats jsonb, error)
```

Integrity measures:
- `audit_log`, `evidence` and `attestation` are protected by DB triggers that reject UPDATE and DELETE.
- Foreign keys across schemas are avoided; cross-module references are by ID only, which keeps modules separable later.

## 7. Event Model

Events are written to `platform.outbox_event` in the same transaction as the state change, then published by a relay.

| Event | Producer | Typical consumers |
|---|---|---|
| DataProductPublished | Registry / connectors | Assessment |
| OwnershipChanged | Registry | Assessment, Workflow, Graph |
| RegulationUpdated | Obligation | Policy (flag rules for review), Graph |
| PolicyUpdated | Policy | Assessment (re-evaluate scope) |
| QualityThresholdBreached | Connectors (DQ) | Assessment, Workflow |
| ModelRegistered | Connectors | Assessment, Workflow (AI Governance) |
| ExceptionExpired | Policy (scheduler) | Assessment, Operations |
| EvaluationFailed | Assessment | Operations |
| FindingCreated | Operations | Workflow, Notifications |
| CaseClosed | Operations | Reporting |

Event envelope: `{id, type, version, occurred_at, correlation_id, payload}`. Consumers are idempotent (dedupe on event id).

Transport: in-process dispatcher with outbox initially; Kafka or NATS if cross-service delivery or volume demands it.

## 8. Integration Layer

- **Connector framework:** a Python interface with `discover()`, `fetch()`, `map()` and `health()`; each connector runs as a scheduled or event-triggered job with run history.
- **Normalization:** external metadata is mapped to Registry models; unmapped fields stay in `attributes jsonb`.
- **Idempotency:** `(source_system, external_ref)` is the natural key for upserts.
- **Inbound:** pull connectors (catalog, lineage, DQ) and webhooks (push events).
- **Outbound:** optional cross-references to external tickets (Jira, ServiceNow; DMC remains the system of record for control-related work), notifications (email, Slack/Teams), webhooks.
- **Resilience:** retries with backoff, dead-letter table, per-connector rate limits.

## 9. Policy Engine

**Rule definition (YAML/JSON DSL, stored as JSON):**

```yaml
key: residency.restricted-data
version: 3
obligation: residency-restriction
applicability:
  all:
    - asset.type in [data_product, dataset]
    - asset.classification == "restricted"
    - asset.jurisdictions is not empty
condition:
  all:
    - asset.attributes.hosting_region in allowed_regions(asset.jurisdictions)
severity: high
on_fail: finding
```

**Lifecycle:** draft → in review → active → retired. Active rules are immutable; changes create a new version.

**Evaluation flow:**
1. Event arrives (or schedule fires).
2. Select candidate rules via applicability index.
3. Check active exceptions; skip with a recorded "excepted" result.
4. Evaluate condition against asset snapshot.
5. Persist Evaluation (inputs, rule version, result).
6. On fail, upsert Finding (dedupe on asset + rule); on pass, auto-resolve any open Finding.

**Engine choice:** start with a small in-process evaluator (safe expression language, no arbitrary code). Evaluate OPA/Rego later if rule complexity demands it. The evaluator sits behind an interface so it can be swapped.

## 10. Knowledge Graph

- A **derived read model**, never a source of truth.
- Initial implementation: `graph.node` and `graph.edge` tables in Postgres, updated by event consumers, queried with recursive CTEs.
- Node types: Asset, Term, CDE, Control, Obligation, Regulation, Consumer, Finding, Risk.
- Edge examples: `asset -implements-> control`, `obligation -derived_from-> regulation`, `asset -consumed_by-> consumer`.
- Impact query: traverse from a changed node to affected assets, owners and open findings.
- Move to a dedicated graph database only if traversal depth or volume makes Postgres impractical. The graph can be rebuilt from Registry at any time.

## 11. Trust Score (deferred)

Definition (subject, inputs, calculation, ownership) is not yet decided and is out of scope for now.

What the current design already supports:
- Ownership and findings are DMC-native data.
- Evidence carries an optional `valid_until`, so freshness can be used later.
- DQ results are the only external input still to be decided (source and feed format).

## 12. Security and Compliance

- **AuthN:** OIDC/SAML SSO; service accounts with scoped tokens for connectors.
- **AuthZ:** RBAC for roles, ABAC for domain and jurisdiction scoping (enforced in the service layer).
- **Audit:** every write recorded in `audit_log`; sensitive reads logged.
- **Evidence:** stored in object storage with SHA-256 recorded in DB; immutability via write-once policy; retention enforced by a job.
- **Secrets:** vault or cloud secret manager; connector credentials encrypted.
- **Encryption:** TLS in transit, encryption at rest for DB and object storage.

## 13. API Design

- REST, versioned under `/api/v1`, OpenAPI generated by FastAPI.
- Resource style: `/assets`, `/terms`, `/regulations`, `/obligations`, `/policies`, `/evaluations`, `/findings`, `/cases`, `/evidence`, `/attestations`, `/playbooks`, `/graph/impact`.
- Cursor pagination, filtering, ETag/If-Match for optimistic concurrency.
- Webhooks for finding, case and attestation events.
- Async operations (bulk import, re-evaluation) return a job id.

## 14. Backend Implementation (FastAPI)

DMC must be split into multiple backend and frontend components before production. So each bounded context is its own package from day one, in one monorepo (uv workspace), with boundaries enforced by tooling.

### 14.1 Repository layout

```
dmc/
  .github/                  # workflows, copilot-instructions.md
  apps/
    api/                    # FastAPI app: mounts routers, wiring only
    worker/                 # outbox relay, schedulers, connector jobs
    web/                    # React SPA (DESIGN.md lives here)
  packages/                 # Python, one per bounded context (uv workspace)
    dmc_common/             # base: ids, time, errors, pagination
    dmc_platform/           # base: auth, audit, outbox
    dmc_events/             # base: event contracts (schemas, versions)
    dmc_registry/
    dmc_obligation/
    dmc_policy/
    dmc_assessment/
    dmc_operations/
    dmc_workflow/
    dmc_trust/
    dmc_graph/
    dmc_reporting/
    dmc_connectors/         # connector interface + connectors
  libs/                     # JS shared libs: ui, api-client
  db/                       # roles and grants bootstrap SQL
  pyproject.toml            # uv workspace root
```

### 14.2 Package anatomy

```
dmc_policy/
  pyproject.toml            # declares its own dependencies
  src/dmc_policy/
    public.py               # the ONLY module other packages may import
    domain/                 # entities, rules, evaluator interface
    application/            # use cases
    infrastructure/         # SQLAlchemy models, repositories (`policy` schema)
    api/                    # FastAPI router (imported by apps only)
    events/                 # events published, handlers for events consumed
    migrations/             # Alembic branch for its own schema
  tests/
```

`public.py` exposes a small interface and plain DTOs (Pydantic models, IDs). Never ORM models or domain entities.

```python
# dmc_policy/public.py
class PolicyQueries(Protocol):
    def applicable_rules(self, asset: AssetRef) -> list[RuleRef]: ...
```

### 14.3 Dependency rules

```
apps (api, worker)
   |
   v
dmc_workflow
   v
dmc_operations | dmc_assessment | dmc_graph | dmc_reporting | dmc_trust
   v
dmc_policy | dmc_obligation
   v
dmc_registry
   v
dmc_platform | dmc_events
   v
dmc_common
```

1. A package may import downwards only. Packages on the same row never import each other.
2. Cross-context calls go through the other package's `public.py`, and only when an answer is needed right now.
3. To react to something that happened, use events (lower contexts publish, upper ones consume).
4. Only IDs and DTOs cross a boundary.
5. No cycles. Base packages never import a context.

### 14.4 Enforcement

| Layer | Mechanism | Catches |
|---|---|---|
| Database | One Postgres role per context with grants only on its schema; no cross-schema foreign keys; migrations owned by the package | Reading another context's tables |
| Dependencies | uv workspace: each package declares its dependencies; tests run per package (`uv run --package dmc_policy pytest`) | Undeclared imports |
| Direction | import-linter `layers` contract (below) | Upward or sibling imports, cycles |
| Internals | import-linter `forbidden` contract per package | Importing anything except `public.py` |
| Events | Contract tests in CI: every producer and consumer validated against `dmc_events` schemas | Breaking event changes |
| Review | CODEOWNERS per package; rules repeated in `.github/copilot-instructions.md` | Agent or human drift before CI |

```ini
[importlinter]
root_packages =
    dmc_workflow
    dmc_operations
    dmc_assessment
    dmc_graph
    dmc_reporting
    dmc_trust
    dmc_policy
    dmc_obligation
    dmc_registry
    dmc_platform
    dmc_events
    dmc_common

[importlinter:contract:direction]
name = Contexts only import downwards
type = layers
layers =
    dmc_workflow
    dmc_operations | dmc_assessment | dmc_graph | dmc_reporting | dmc_trust
    dmc_policy | dmc_obligation
    dmc_registry
    dmc_platform | dmc_events
    dmc_common

[importlinter:contract:policy-internals]
name = Outside code may only use dmc_policy.public
type = forbidden
source_modules =
    dmc_workflow
    dmc_operations
    dmc_assessment
    dmc_graph
    dmc_reporting
    dmc_trust
    dmc_obligation
    dmc_registry
forbidden_modules =
    dmc_policy.domain
    dmc_policy.application
    dmc_policy.infrastructure
    dmc_policy.api
    dmc_policy.events
```

Apps are not listed as `source_modules`, so they may import each package's `api` router for wiring. The `forbidden` contract is repeated per package; generate these blocks with a small script rather than maintaining them by hand.

### 14.5 Designing for the split

- **`public.py` is the seam.** Today it is an in-process call. When a context becomes its own service, a remote client implements the same interface, and the app wiring picks which one to use. Callers don't change.
- **Events carry over unchanged,** so prefer them wherever a call isn't strictly needed.
- **Few deployables, not one per context.** Today `api` and `worker` load every package. An indicative production split:
  - *Knowledge:* registry, obligation, policy
  - *Compliance operations:* assessment, operations, workflow
  - *Insights:* graph, reporting, trust
- Each group gets its own API and worker. Because schemas are isolated and have no cross-schema foreign keys, each can move to its own database when needed.
- The frontend split follows the same idea (section 15).

Tech notes: SQLAlchemy 2.x, Alembic, Pydantic v2, background work via a worker process (Celery, Arq or Dramatiq), Redis for cache and queues.

## 15. Frontend (React)

- TypeScript, React Router, TanStack Query.
- UI: shadcn/ui with Inter for text and Geist Mono for IDs, hashes and rule definitions.
- Design system defined in `DESIGN.md`: "Paper" warm neutrals, teal accent, balanced corner radius, Apple-like restraint.
- Desktop only, no mobile layouts. Screens range from 12" laptops to 34" ultrawide, so content width is capped and extra width goes to side panels rather than stretched tables.
- Component gallery as an in-app route instead of Storybook.
- Structure for a later split: `apps/web/src/features/<area>/` per main area (registry, policy, findings and so on), each owning its routes, components and queries. Shared code is limited to `libs/ui` (shadcn/ui components and design tokens) and `libs/api-client` (generated from the OpenAPI spec).
- Enforced with eslint-plugin-boundaries: features may not import each other, and no direct `fetch` calls outside `api-client`. A feature can later become its own app behind a shared shell.
- Main areas: Registry browser, Glossary and CDEs, Regulations and Obligations, Policy editor, Findings and Case workbench, Playbook runner, Evidence and Attestation, Impact explorer, Executive dashboards, Admin (connectors, roles).
- Owner inbox as the default landing page for owners and stewards.
- Role-aware navigation driven by the permissions returned from the API.

## 16. Deployment and Operations

- Containers on Kubernetes (or a managed container service): `api`, `worker`, `web`.
- Managed PostgreSQL with PITR; object storage for evidence.
- Environments: dev, staging, prod; GitHub Actions in the monorepo with path-filtered jobs per app and package (tests, lint, import-linter, migration checks).
- Development in VS Code with GitHub Copilot; repo-level guidance lives in `.github/copilot-instructions.md`.
- Observability: structured logs, OpenTelemetry traces, metrics (evaluation latency, outbox lag, connector failures), alerting on SLO burn.
- Backups tested regularly; restore runbook documented.

## 17. Non-Functional Targets

| Area | Target |
|---|---|
| Event to finding latency | p95 under 5 s |
| Evaluation throughput | 1M/day, 10x headroom via workers |
| API read latency | p95 under 300 ms |
| Availability | 99.9% |
| RPO / RTO | 15 min / 4 h |

Scaling path: add workers first; partition `evaluation` and `audit_log` by time; add read replicas for reporting.

## 18. Evolution Path

| Trigger | Action |
|---|---|
| Evaluation load impacts API | Split Assessment into its own service and worker pool |
| Graph queries too slow | Move Graph to a graph database, still fed by events |
| Cross-team ownership of modules | Split along bounded-context lines (IDs-only references make this cheap) |
| Event volume or multi-service needs | Replace the in-process dispatcher with Kafka or NATS |
| Complex policy needs | Introduce OPA/Rego behind the evaluator interface |

## 19. Worked Example: Residency Breach

| Step | Component | Result |
|---|---|---|
| 1 | Connector detects a restricted product published to a non-permitted region | `DataProductPublished` event in outbox |
| 2 | Assessment consumes event; selects `residency.restricted-data` v3 | Rule applicable |
| 3 | Evaluation runs; condition fails | `evaluation` row, result = fail |
| 4 | Operations upserts finding | `finding` (severity high), event `FindingCreated` |
| 5 | Workflow starts Residency Breach playbook | `playbook_run`, case opened, owner assigned, notification sent |
| 6 | Owner migrates the product and uploads proof | `evidence` with SHA-256 |
| 7 | Steward validates; re-evaluation passes | Finding auto-resolves |
| 8 | Owner attests | Immutable `attestation` referencing evidence hashes; `CaseClosed` |

## 20. Decisions Log

| # | Decision | Rationale |
|---|---|---|
| D1 | Modular monolith, not microservices | Lower operational complexity for an internal build |
| D2 | Postgres as single source of truth | Simplicity, transactions, outbox pattern |
| D3 | Graph is a derived read model | Avoids dual write; rebuildable |
| D4 | Evidence and attestation immutable | Audit defensibility |
| D5 | Policy DSL behind an evaluator interface | Allows Rego later |
| D6 | Cross-module references by ID only | Keeps modules extractable |
| D7 | One package per bounded context from day one, in a monorepo, boundaries enforced in CI and at the database | Must split into multiple components before production |

## 21. Open Items

1. Final rule DSL syntax and expression language.
2. Task queue choice (Celery, Arq or Dramatiq).
3. Evidence storage product and write-once mechanism.
4. Trust score definition (deferred).
5. Signature mechanism for attestations (internal signing key vs external e-signature).
6. Regulations in scope (to be decided) and any hosting-location constraints on DMC's own metadata.
