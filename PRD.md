# Data Management Centre: product requirements

## 1. Overview

Data Management Centre (DMC) is the internal governance control plane for data controls. It knows what data exists and where, checks continuously whether that data meets its controls, runs the work to fix what doesn't, and proves that the fixes worked.

DMC is the system of record for every action and workflow related to data controls. Other tools (ticketing, service management) may exist for other purposes, but control work starts, runs and closes in DMC.

DMC is an internal build for a single organisation. It is not a commercial product and does not need multi-tenancy.

### Problem

- Ownership, classification and data flows are documented inconsistently, so nobody can say with confidence which data needs which controls.
- Controls are checked periodically and manually, so failures and drift go unnoticed between reviews.
- Remediation is tracked as activity ("ticket closed") rather than outcome ("control now passes").
- Leadership and auditors receive evidence assembled by hand, late, and without a link to the underlying facts.

### Goals

- Every application and data asset has a confirmed owner, classification and context.
- Every required control is derived automatically from what the data is, not configured by hand per system.
- Controls are evaluated continuously, with results anyone can trace to facts and evidence.
- Owners see exactly what needs them, and act in one place.
- Fixes count only when the policy engine confirms them.
- Posture, coverage and remediation outcomes are visible to leadership and auditors without manual assembly.

### Non-goals

- Multi-tenancy or external customers.
- Regulation-specific rule packs, until the regulations in scope are decided.
- Mobile or tablet use. DMC is desktop only, from 12" laptops to 34" ultrawide monitors.
- General-purpose ticketing for work unrelated to data controls.

## 2. Users and roles

| Role | Accountable for | Typical work in DMC |
|---|---|---|
| Data Owner | The data and its risk | Confirms ownership, approves classification, designates CDEs and DQ thresholds, approves access, accepts risk, attests |
| Application Owner | Technical implementation in their application | Registers the application, declares stores, datasets, integrations and processes, fixes technical findings, proposes compensating controls, runs retention and deletion |
| Data Steward | Day-to-day upkeep | Works actions assigned by owners, maintains metadata |
| Process Owner | A business process | Confirms which applications support the process and in what role |
| Governance team | Policies and the control library | Writes and reviews policies and controls, manages evidence sources, monitors engine health |
| Leadership | Oversight | Reads posture, risk and remediation reports |
| Auditor | Independent assurance | Reads evidence, results history and audit packs; read-only |

The Data Owner owns the risk; the Application Owner owns the implementation. Every applied control records both.

## 3. Concepts

| Term | Meaning |
|---|---|
| Asset | A governed data object: a dataset, report, model or file. Datasets are the most common asset |
| Data element | A field or column within an asset; can be flagged PII and CDE |
| CDE | Critical data element: an element whose quality is monitored against thresholds |
| Data category | What kind of data an asset holds (personal data, payment data, reference data) |
| Business context | Why the data exists in this application (order fulfilment, pricing) |
| Application | A system that stores or processes data, with one or more environments |
| Data store | A database, bucket, file share or SaaS object inside an application environment, with a region |
| Integration | A flow of data from a source (application or external party) to a target, declared and/or observed |
| Business process | A business activity an application supports |
| Policy | A statement of what must be true, owned by the governance team |
| Control | A checkable requirement implementing a policy, with an applicability selector |
| Applied control | A control applied to a specific subject (application, asset, element or flow) |
| Evaluation result | One check of one applied control at one point in time, with its facts and evidence |
| Action | Work to fix a failing applied control; done only when verified |
| Exception | Time-bound acceptance of a failing control, with justification and approval |
| Posture | Share of applied controls passing within a scope |
| Obligation | Reserved for external duties from regulations or contracts, once in scope |

## 4. The governance loop

Every asset and application moves through four stages. The stages describe the entity's state; they are not top-level navigation.

| Stage | Question | Covers |
|---|---|---|
| Know | What is this, and who is accountable? | Ownership, classification, stores, datasets, elements, integrations, processes, regions |
| Assess | Does it meet its controls? | Policy engine results: data quality, retention, masking, cross-border movement, security controls, declaration checks; blast radius of failures |
| Act | What is being done about it? | Actions, exceptions, access decisions, change reviews, attestations |
| Assure | Did the action work, and does it keep working? | Verified outcomes, recurrence, posture movement attributed to actions |

An action is complete only when a later evaluation confirms the fix. Until then it is "fixed, awaiting verification".

## 5. Information architecture

Global navigation: **Inbox, Assets, Applications, Controls, Reports.**

- **Inbox**: everything waiting on the current user, across all entities.
- **Assets**: list and detail. Detail shows the stage tracker and, per stage, the relevant sections.
- **Applications**: list and detail, with the same stage tracker.
- **Controls**: control library, applied controls, exceptions, evaluations (engine runs and errors), policies.
- **Reports**: posture, coverage, risk and blast radius, remediation, exceptions and certification, audit packs, scheduled digests.

A scope selector (all domains or one domain) filters every view. Search and a command palette (⌘K) reach any entity directly.

### Application detail

| Stage | Sections |
|---|---|
| Know | Data stores (harvest status), datasets (category, business context, stored, retention), inbound integrations (declared versus observed), business processes |
| Assess | Data quality on CDEs, retention checks, applied controls |
| Act | Actions and exceptions |
| Assure | Verified outcomes |

### Asset detail

| Stage | Sections |
|---|---|
| Know | Ownership, classification, applications, data elements, lineage |
| Assess | Applied controls and results, data quality |
| Act | Actions, exceptions, access requests |
| Assure | Verified outcomes, recurrence |

## 6. User journeys

Journeys follow one model: owners set intent and handle exceptions; DMC does routine checking and routing.

### Data Owner

1. **Claim ownership.** Review assets assigned to them; accept, reassign or dispute each; name stewards.
2. **Classify.** Review suggested classification and PII findings; approve or override; set criticality.
3. **Designate CDEs.** Mark critical elements and set DQ thresholds.
4. **Review posture.** See failing controls across owned assets, with the reason and evidence for each.
5. **Direct remediation.** Create or approve actions and assign them; track until verified.
6. **Accept risk.** Approve or reject exceptions with a reason and expiry.
7. **Decide access.** Approve, reject or approve with conditions, by purpose and with expiry.
8. **Approve transfers.** Approve the transfer basis for personal or restricted data crossing regions.
9. **Attest.** Confirm the evidence DMC holds for owned assets on a schedule.

### Application Owner

1. **Register the application.** Purpose, hosting, criticality, owners, environments.
2. **Connect data stores.** Link every database so metadata is harvested; fix harvest failures.
3. **Declare datasets.** Data category, business context, stored or not, and retention when stored.
4. **Declare inbound integrations.** Source, datasets, method, frequency and regions; resolve undeclared feeds that DMC observes.
5. **Link business processes.** Name the processes supported and the application's role; the process owner confirms.
6. **Implement controls.** See applied controls derived for the application; connect evidence sources.
7. **Remediate findings.** Fix failing technical controls (retention, masking, encryption, DQ monitoring); DMC re-checks automatically.
8. **Request exceptions.** Propose compensating controls when a control cannot be met; the Data Owner decides.
9. **Review changes.** New integrations or data flows go through a change review before release.
10. **Run the data lifecycle.** Retention deletions and data subject requests, with proof back to DMC.
11. **Decommission.** Dispose of or migrate all data with evidence before the application can be retired.

### Data Steward

Work assigned actions, maintain metadata, and respond to DQ failures on CDEs.

### Process Owner

Confirm or reject application links to their process, and the application's role in it.

### Governance team

Maintain policies and controls, tune applicability selectors, manage evidence sources, review engine errors and stale results, and review control design periodically.

### Leadership and auditors

Read posture trends, coverage gaps, top risks by blast radius, remediation outcomes and audit packs.

## 7. Functional requirements

### 7.1 Inventory and Know

- **FR-K1** Register applications with purpose, hosting, criticality, lifecycle state, owners and environments.
- **FR-K2** Link data stores to application environments, each with platform, region and connection reference.
- **FR-K3** Harvest metadata (schemas, tables, columns, row counts, oldest records where available) from every linked store on a schedule and on demand; show last harvest time and failures.
- **FR-K4** Map harvested objects to assets and data elements; flag unmapped objects.
- **FR-K5** Declare datasets with data category, business context, stored flag, and retention policy when stored.
- **FR-K6** Flag data elements as PII (from scanners or declaration) and as CDE (by Data Owner).
- **FR-K7** Declare inbound integrations with source, target, datasets, method, frequency and regions.
- **FR-K8** Record observed flows from logs and network sources; compare them with declarations.
- **FR-K9** Link applications to business processes with a role; require process owner confirmation.
- **FR-K10** Assign and confirm Data Owner, Steward and Application Owner; support reassignment and disputes.
- **FR-K11** Suggest classification from scanner findings; require Data Owner approval.
- **FR-K12** Show lineage and downstream consumers of each asset.
- **FR-K13** Require declarations to be re-confirmed on a schedule; expired declarations raise a Know gap.

### 7.2 Policies and controls

- **FR-P1** Maintain policies and a control library; each control has a policy, rule, applicability selector, evidence requirement and control owner.
- **FR-P2** Applicability selectors use attributes (classification, data category, PII, CDE, environment type, region, stored flag), never named entities.
- **FR-P3** Derive applied controls automatically from the selectors; recompute when classification, links or attributes change.
- **FR-P4** Version rules; keep results explainable against the version that produced them.
- **FR-P5** Review control design periodically, recorded as an action on the governance team.

### 7.3 Assess

- **FR-A1** Evaluate applied controls continuously: on fact changes, on a schedule, and on demand after a fix.
- **FR-A2** Record each evaluation as an append-only result with outcome, measured value, threshold, reason, facts, evidence and freshness.
- **FR-A3** Distinguish "error" (could not evaluate) from "fail", and route errors to the evidence source owner.
- **FR-A4** Built-in checks, at minimum:
  - data quality on CDEs against thresholds, and CDEs without monitoring
  - retention: stored datasets with records older than their retention policy
  - PII masking in non-production stores, and in flows to targets outside an approved list
  - cross-border movement of personal or restricted data without an approved transfer basis
  - declaration completeness, and declared-versus-observed mismatches (stores, stored flag, integrations, regions, classification)
  - harvest freshness and failures
  - security controls such as encryption at rest and periodic access review
- **FR-A5** Show the reason for every result and every derived applied control ("Why?").
- **FR-A6** Show the blast radius of a failure: downstream assets, reports, models and processes affected.
- **FR-A7** Flag results older than their freshness window as out of date.

### 7.4 Act

- **FR-C1** Raise actions from failing results, manually or automatically, with assignee, due date and SLA.
- **FR-C2** Action states: open, in progress, fixed (awaiting verification), verified, reopened, cancelled.
- **FR-C3** Exceptions with justification, compensating control, approver, expiry and monitoring; failing results under an active exception show as "excepted".
- **FR-C4** Access requests decided by purpose, with conditions and automatic expiry.
- **FR-C5** Change reviews for new integrations or flows of sensitive data, required before release.
- **FR-C6** Attestation campaigns by scope; owners confirm evidence or flag issues.
- **FR-C7** Bulk actions with impact preview, permission checks across all selected rows, and partial-failure reporting.
- **FR-C8** Every risk decision requires a reason, written to the audit trail.

### 7.5 Assure

- **FR-S1** Link each fixed action to the result that verifies it; only verified actions count as done.
- **FR-S2** Detect recurrence: controls that pass after a fix and later fail again.
- **FR-S3** Attribute posture movement to verified actions.
- **FR-S4** Show the history of every applied control's results and evidence.

### 7.6 Reports

- **FR-R1** Posture over time by domain, application, asset and control.
- **FR-R2** Coverage: assets and applications missing owners, classification, harvest or applied controls.
- **FR-R3** Top risks ranked by blast radius.
- **FR-R4** Remediation: time to verified fix, SLA performance, recurrence, attributed posture change.
- **FR-R5** Exceptions by age and expiry; attestation completion by owner.
- **FR-R6** Audit packs: exportable evidence and results for a scope and period.
- **FR-R7** Scheduled digests to leadership.

### 7.7 Inbox, search and notifications

- **FR-I1** A personal inbox of approvals, failing controls, actions, exceptions and confirmations due.
- **FR-I2** Global search and command palette across all entities.
- **FR-I3** Notifications only for actionable items; digests by default; user-controlled channels.

### 7.8 Administration

- **FR-D1** Users, roles and scopes from the corporate identity provider.
- **FR-D2** Domains, data categories, regions, retention policies and approved target lists as reference data.
- **FR-D3** Connector and evidence source configuration, with health status.

### 7.9 Audit

- **FR-U1** An append-only audit trail of every change and decision, with actor, time, reason and before and after values.
- **FR-U2** Evidence stored with content hashes; tampering is detectable.

## 8. Non-functional requirements

| Area | Requirement |
|---|---|
| Performance | Pages interactive in under 1 s; UI actions acknowledge in under 100 ms; checked in CI |
| Scale | Lists handle 100,000+ rows with server-side search, filter and cursor paging |
| Freshness | Every result shows when it was evaluated; stale results are flagged |
| Accessibility | WCAG 2.2 AA; full keyboard operation |
| Security | Corporate SSO; role- and scope-based authorisation enforced on the server; least privilege |
| Privacy | Sample values and PII masked by default; reveal is permissioned and logged |
| Auditability | Append-only audit trail and results; reproducible evaluations from recorded facts |
| Reliability | Evaluations are idempotent; failed jobs retry safely; no result is lost |
| Clients | Current Chrome and Edge on desktop; 12" to 34" screens |
| Localisation | Local time with UTC available; locale-aware formats |

## 9. Success measures

Targets to be set once baselines exist.

- Coverage: share of applications and assets with confirmed owner, classification and harvest.
- Posture: share of applied controls passing, by domain.
- Time from failure to verified fix.
- Share of closed actions that are verified rather than only marked fixed.
- Recurrence rate of fixed controls.
- Share of observed integrations that are declared.

## 10. Open questions

- Which regulations are in scope, and therefore which regions count as boundaries for transfers.
- Trust score: definition and whether it is needed alongside posture.
- Source of retention policies: central library or per data category.
- Which log and network sources can supply observed flows.
