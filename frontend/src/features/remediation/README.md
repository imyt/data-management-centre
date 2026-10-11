# Remediation Feature Module (`@/features/remediation`)

## Ownership
The Remediation module owns:
- Automated anomaly scanning and compliance rule audits
- Policy breach reconciliations (missing confidentiality, unclassified PII, thin markdown)
- Remediation velocity tracking and metrics

## Routes Mounted
- `/remediation` &rarr; mounts `RemediationPage` from `pages/remediation-page/`

## State Boundary
- **Server State**: Asset metadata fetched via TanStack Query.
- **Client State**: `useRemediationUiStore` manages issue filtration and focus.

## Public Barrel Contract
Import only from `@/features/remediation`.
