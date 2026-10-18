# Backend rules

Follow `../ARCHITECTURE.md`, especially sections 5 to 8.

- One module per domain (identity, inventory, connectors, policy, evaluation, workflow, reporting, notification, audit). Cross-module access goes through the module's service interface; enforce with `import-linter` contracts.
- Every response model inherits the shared base, which carries `allowed_actions`, `reason` for derived items, `evaluated_at` where relevant, and cursor paging for lists. A test asserts this for every route.
- `evaluation_result` is append-only. Never update or delete rows; write a new result.
- Policies select by attributes, never by named apps or assets.
- Evaluations are idempotent, keyed by applied control, subject and fact snapshot.
- Keep `error` (could not evaluate) separate from `fail`.
- Every schema change ships with an Alembic migration.
- Write the reason a user or the engine took a risk decision into the audit trail in the same transaction.
