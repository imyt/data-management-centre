---
description: Add a FastAPI endpoint through all three tiers, with tests and contract sync
agent: backend-dev
---

Add this endpoint: ${input:endpoint:For example, "GET /assets with filters and cursor pagination"}

Resource: ${input:resource:For example, asset}

Create or extend, in order: schemas, model and migration (if needed), repository, service, router, and tests. Include the permission check and audit record for any mutation. Set a clean `operation_id`. When done, run lint, types, tests, and `npm run api:sync`, then summarize.
