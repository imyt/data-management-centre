# Governance Inbox Feature Module (`@/features/inbox`)

## Ownership
The Inbox module manages:
- Workflow approvals and multi-stage consensus queues
- SLA countdown windows and urgent escalation alerts
- Deep-links into the Catalog inspect drawer for asset approval

## Routes Mounted
- `/inbox` &rarr; mounts `InboxPage` from `pages/inbox-page/`

## State Boundary
- **Server State**: Assets with active draft versions or under-review status queried via TanStack Query.
- **Client State**: `useInboxUiStore` manages queue filtering and selection.

## Public Barrel Contract
Import only from `@/features/inbox`.
