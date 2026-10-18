# Backend rules

Follow `../ARCHITECTURE.md`, especially sections 5 to 8.

- One module per domain (identity, inventory, connectors, policy, evaluation, workflow, reporting, notification, audit). Cross-module access goes through the module's service interface; enforce with `import-linter` contracts.
- Every response model inherits the shared base, which carries `allowed_actions`, `reason` for derived items, `evaluated_at` where relevant, and cursor paging for lists. A test asserts this for every route.
- `evaluation_result` is append-only. Never update or delete rows; write a new result.
- Policies select by attributes, never by named apps or assets.
- Evaluations are idempotent, keyed by applied control, subject and fact snapshot.
- Keep `error` (could not evaluate) separate from `fail`.
- Every schema change ships with an Alembic migration.
- Every change and decision calls `AuditService(session).record(...)` (`app.modules.audit.service`) with the session that makes the change, so both commit together. Risk decisions pass `reason_required=True` (ADR 0006).
- Routes take `PrincipalDep` (`app.core.auth`) and pass the `Principal` to the service; audit with `actor=principal.actor`. Never read the dev-user header or roles anywhere else.
- Authorisation lives in services. Each module declares its `Permission("action", {Role...})` constants once; services call `require(principal, PERMISSION, subject_domain_id)` before every change (wrong role or out-of-scope domain → `PermissionDeniedError`, 403), and reads filter with `principal.in_scope(domain_id)`.
- Responses set `allowed_actions=allowed_actions(principal, [PERMISSIONS...], subject_domain_id)` from the same constants, so the UI never offers what the service would refuse (ADR 0007).
