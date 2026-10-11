# Remediation Page (`/remediation`)

## Overview
Automated governance health cockpit highlighting policy anomalies, thin definitions, unclassified PII, and recertification triggers.

## Route & Parameters
- **Path**: `/remediation`

## Data Dependencies
- `listAssetsApiV1AssetsGetOptions` — queries all assets for automated compliance rule checks

## UI State
- `useRemediationUiStore`: Manages severity filtering (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) and selected anomaly focus.
