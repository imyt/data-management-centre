# Inbox Page (`/inbox`)

## Overview
Workflow review queue displaying awaiting stage approvals, multi-persona governance sign-offs, and SLA timer countdowns.

## Route & Parameters
- **Path**: `/inbox`

## Data Dependencies
- `listAssetsApiV1AssetsGetOptions` — queries draft and under-review assets
- `usePersona` — determines current signed-in role permissions and queue prioritization

## UI State
- `useInboxUiStore`: Manages task filter (`PENDING` | `APPROVED` | `ALL`) and active task selection.
