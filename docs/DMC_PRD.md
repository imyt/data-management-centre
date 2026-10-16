# Data Management Centre (DMC) — Product Requirements Document

**Version:** 3.1 (draft) | **Status:** For review | **Stack:** React, FastAPI, PostgreSQL | **Delivery:** internal build

---

## 1. Overview

The Data Management Centre (DMC) is the enterprise **governance control plane**. It orchestrates governance outcomes through metadata stewardship, policy execution, compliance assessment, risk management and remediation workflows.

**North Star:** Know → Assess → Act → Prove. Continuous governance, not periodic governance.

**Principle:** DMC governs data; it never stores the data itself, only metadata, evaluations, findings and evidence.

## 2. Problem Statement

- Governance knowledge (owners, glossary, CDEs, regulations) lives in spreadsheets and disconnected catalogs.
- Policies are documents, not executable rules, so compliance is checked periodically and manually.
- Findings, remediation and evidence are scattered across email and ticketing tools, which makes audits slow and painful.
- Nobody can quickly answer "what is impacted if this regulation or asset changes?"

## 3. Goals and Non-Goals

**Goals**
1. A single registry of governance assets with clear ownership.
2. Obligations and policies expressed as versioned, executable rules.
3. Automated, continuous evaluation producing findings.
4. Case management and playbooks to drive remediation.
5. Tamper-evident evidence and attestation to prove compliance.
6. Impact analysis and trust scoring for executives and stewards.

**Non-goals**
- Not a data catalog, lineage scanner or DQ engine (integrates with them).
- Not a data store or data movement platform.
- Not a general-purpose ticketing or ITSM tool. Jira and ServiceNow may exist for other purposes, but every action and workflow related to data controls is managed in DMC.

## 4. Personas

| Persona | Needs |
|---|---|
| Data Owner | See owned assets, respond to findings, attest |
| Data Steward | Maintain glossary, CDEs, classifications; triage findings |
| Compliance Officer | Map regulations to obligations and policies; manage exceptions |
| Governance Lead | Run playbooks, monitor case backlog |
| Auditor | Retrieve evidence and attestations with full history |
| Executive | Trust scores, risk posture, regulatory exposure |
| Platform Admin | Connectors, RBAC, system configuration |

## 5. Capability Map

**Level 1:** Governance Knowledge Management · Policy & Obligation Management · Compliance Intelligence · Governance Operations · Risk & Trust Management · Workflow & Orchestration · Insights & Executive Reporting

**Level 2:** Glossary, CDEs, Ownership, Regulations, Controls, Policy-as-Code, Assessments, Findings, Cases, Evidence, Attestation, Exceptions, Trust Scores, Playbooks, Event Processing.

## 6. Canonical Model

Governance Asset → Obligation → Policy Rule → Evaluation → Finding → Case → Evidence → Attestation

## 7. Functional Requirements

Priority: **P0** must-have, **P1** should-have, **P2** later.

### 7.1 Governance Knowledge (Registry, Glossary, CDEs)
| ID | Requirement | Pri |
|---|---|---|
| GK-1 | CRUD for governance assets (data products, datasets, models, reports) with type, domain, classification, jurisdiction | P0 |
| GK-2 | Assign owner and steward per asset; flag ownership gaps | P0 |
| GK-3 | Business glossary with terms, definitions, status and approval workflow | P0 |
| GK-4 | Critical Data Element (CDE) registry linked to terms and assets | P0 |
| GK-5 | Data classification and jurisdiction tagging | P0 |
| GK-6 | Bulk import (CSV) and connector-based ingestion | P0 |
| GK-7 | Full change history on every entity | P1 |

### 7.2 Policy & Obligation Management
| ID | Requirement | Pri |
|---|---|---|
| PO-1 | Regulation and Control registers, versioned | P0 |
| PO-2 | Obligations linking regulations to controls and applicable asset scopes | P0 |
| PO-3 | Policy rules authored as code with draft → review → active lifecycle | P0 |
| PO-4 | Applicability rules (which assets a rule applies to) | P0 |
| PO-5 | Exception management with approver, justification and expiry | P0 |
| PO-6 | Policy and regulation version history; evaluations pin the version used | P0 |

### 7.3 Compliance Intelligence
| ID | Requirement | Pri |
|---|---|---|
| CI-1 | Evaluation service runs rules on events and schedules | P0 |
| CI-2 | Each evaluation records inputs, rule version, result and timestamp | P0 |
| CI-3 | Failed evaluations create or update findings (deduplicated) | P0 |
| CI-4 | Continuous compliance dashboard by regulation, domain and asset | P1 |

### 7.4 Governance Operations
| ID | Requirement | Pri |
|---|---|---|
| GO-1 | Findings with severity, status, SLA and assignee | P0 |
| GO-2 | Cases group findings; tasks, comments, due dates | P0 |
| GO-3 | Evidence upload/link with content hash and retention policy | P0 |
| GO-4 | Evidence validation step by a reviewer | P1 |
| GO-5 | Attestation by owner with signed, immutable record | P0 |
| GO-6 | Waivers and regulatory response tracking | P1 |
| GO-7 | Audit pack export (findings, evidence, attestations) | P1 |

### 7.5 Workflow & Playbooks
DMC is the system of record for all control-related actions and workflows.

| ID | Requirement | Pri |
|---|---|---|
| WF-1 | Playbook definitions: triggers, steps, assignees, SLAs | P0 |
| WF-2 | Initial playbooks: Ownership Gap, Data Quality Breach, Residency Breach | P0 |
| WF-3 | AI Governance and Regulatory Escalation playbooks | P1 |
| WF-4 | Playbook runs are traceable and resumable | P0 |
| WF-5 | Optional cross-references to external tickets (Jira, ServiceNow); DMC remains the system of record | P2 |

### 7.6 Knowledge Graph and Impact Analysis
| ID | Requirement | Pri |
|---|---|---|
| KG-1 | Derived graph linking assets, controls, obligations, regulations, consumers, findings and risks | P0 |
| KG-2 | Impact query: "what is affected if X changes?" | P0 |
| KG-3 | Graph is rebuilt/updated from Registry events (never edited directly) | P0 |

### 7.7 Risk & Trust
| ID | Requirement | Pri |
|---|---|---|
| RT-1 | Trust score capability. Definition deferred (subject, inputs, calculation, ownership to be decided) | TBD |
| RT-2 | Risk rollups by domain, regulation and jurisdiction | P1 |

### 7.8 Reporting
| ID | Requirement | Pri |
|---|---|---|
| RP-1 | Executive dashboard: ownership coverage, open findings, time to remediate | P0 |
| RP-2 | Scheduled report export (PDF/CSV) | P2 |

### 7.9 Platform
| ID | Requirement | Pri |
|---|---|---|
| PL-1 | SSO (OIDC/SAML), RBAC, ABAC by domain and jurisdiction | P0 |
| PL-2 | Append-only audit log of all changes and reads of sensitive records | P0 |
| PL-3 | Notifications (email, Slack/Teams, in-app) | P1 |
| PL-4 | Connector framework with run history and error handling | P0 |
| PL-5 | Public REST API and webhooks | P1 |

### 7.10 Guardrailed Automation
Automation is introduced with human approval first, then selectively auto-approved.
- Auto-assignment of owners and cases
- Auto-remediation for low-risk, pre-approved actions
- AI-suggested policy rules from regulation text (always reviewed by a human)
- Guardrails: approval thresholds, kill switch, full audit, dry-run mode

## 8. Key User Journey: Residency Breach

1. **Event:** a data product carrying a residency restriction is published to a region where it is not permitted.
2. **Evaluation:** the residency policy rule fires against the Data Product Published event.
3. **Finding:** high-severity finding created and linked to the asset and obligation.
4. **Case + playbook:** Residency Breach Playbook opens a case, assigns the owner, notifies compliance.
5. **Remediation:** owner migrates the product or requests an exception.
6. **Evidence:** proof of migration (config snapshot, scan result) is attached and hashed.
7. **Validation:** steward validates evidence; a re-evaluation passes.
8. **Attestation:** owner attests; case closes.

## 9. Non-Functional Requirements

| Area | Target (initial, to be validated) |
|---|---|
| Evaluation latency | p95 under 5 s from event to finding |
| Throughput | 1M evaluations/day at launch, scalable 10x |
| API latency | p95 under 300 ms for reads |
| Availability | 99.9% |
| Durability | RPO 15 min, RTO 4 h |
| Security | Encryption in transit and at rest; secrets in a vault |
| Auditability | Append-only audit log; evidence immutable with hash |
| Retention | Configurable per record type; default 7 years for evidence and attestations |
| Accessibility | WCAG 2.1 AA |

## 10. Integrations

- **Metadata:** data catalogs, lineage tools, schema registries
- **Quality:** DQ tools feeding threshold-breach events
- **Identity:** OIDC/SAML provider
- **Ticketing:** Jira, ServiceNow (optional cross-references only)
- **Messaging:** email, Slack/Teams
- **ML/AI:** model registry (Model Registered event)

## 11. Success Metrics

Candidate metrics; targets to be set later.

| Area | Metric |
|---|---|
| Registry | % of assets with an assigned owner |
| Policy engine | Rules evaluated per day |
| Operations | Mean time to remediate findings |
| Graph | Time to complete an impact analysis |
| Automation | % of low-risk findings auto-remediated |

## 12. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Integration effort underestimated | Build the connector framework early; start with 2 source systems |
| Policy DSL too complex for users | Templates and a rule library; UI builder later |
| Alert fatigue from too many findings | Severity model, dedup, SLA-based escalation |
| Low adoption by owners | Simple owner inbox, Slack/Teams notifications and actions |
| Over-engineering (microservices) | Modular monolith first; split on measured need |
| AI automation errors | Human approval by default, dry-run, kill switch |

## 13. Open Questions

1. Which source systems are in scope for connectors?
2. Rule DSL: custom YAML/JSON or OPA/Rego?
3. Trust score: definition, inputs and ownership (deferred).
4. Regulations in scope: to be decided later.
5. Does DMC's own metadata have any hosting-location constraints?
