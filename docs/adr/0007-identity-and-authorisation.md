# ADR 0007: Identity, authentication and authorisation

- Status: accepted
- Date: 2026-10-18

## Context

Roadmap row 0.7 builds the first part of the `identity` module. ADR 0004 §6–7 already decided that a dev identity provider stands behind the real interface (`DMC_AUTH_MODE=dev|oidc`), that a persona switcher picks a seeded user per role from `PRD.md` §2, and that dev authentication is refused in staging and production. ARCHITECTURE §9 puts authorisation in the service layer ("role permits the operation, scope permits the subject") and computes `allowed_actions` from the same rules. This ADR records how that is built, so the Applications slice and everything after it use one shape.

## Decisions

1. **One principal, in core.** `app.core.auth.Principal` is frozen: `user_id`, `display_name`, `roles` (a `frozenset[Role]`, the seven roles of `PRD.md` §2) and `domain_ids` (a `frozenset[UUID]`, or `None` for every domain). `principal.actor` is `"user:<id>"`, the audit trail's `actor`. Both auth modes produce exactly this; routes take it through `PrincipalDep`.
2. **Core resolves users through a protocol.** Core never imports modules (import-linter), so it defines `UserDirectory` (`principal_for(session, username)`, `default_dev_username`). The identity module implements it (`IdentityDirectory`) and `app.main` wires it with `configure_authentication`. The principal is resolved in the request's own session and transaction.
3. **Dev mode.** The `X-DMC-Dev-User` header names a seeded user by `username`. Without the header, `local` and `dev` act as the default persona (Hannah Becker, Governance team, every domain); `test` requires the header, so tests say who acts. An unknown or inactive user is a 401 problem (`urn:dmc:problem:unauthenticated`). `GET /api/v1/dev/users` lists the personas and answers 404 unless `DMC_AUTH_MODE=dev`; the frontend shows the switcher only when it answers.
4. **OIDC is a stub until Phase 4.** In `oidc` mode every authenticated route answers 501. Settings validation refuses `DMC_AUTH_MODE=dev` in `staging` and `production` (ADR 0004 §6).
5. **Identity data.** Schema `identity`: `user_account` (`username` unique, `display_name`, `email`, `active`, `all_domains`), `role_assignment` (one row per role, checked against the role list) and `domain_scope` (user, domain id). Domain ids reference the inventory module's domains; there are no cross-schema foreign keys (ARCHITECTURE §5). Users are created through `IdentityService.create_user`, which writes `identity.user_created` to the audit trail in the same transaction.
6. **Personas are seed data, not migration data.** `dmc-seed` (`app/seed.py`) creates the seven personas through the service, refuses to run in staging and production, and is safe to run again (ADR 0004 §8). Persona domain scopes use fixed domain ids (Customer, Finance, People in `identity/personas.py`) that the inventory seed reuses.
7. **Authorisation is declared once per module and checked in services.** A module declares `Permission("edit", {Role.APPLICATION_OWNER, Role.GOVERNANCE})` constants. Services call `require(principal, PERMISSION, domain_id)` before a change: the wrong role or a domain outside the principal's scope raises `PermissionDeniedError` (403). Responses set `allowed_actions(principal, [PERMISSIONS…], domain_id)`, which applies the same check, so the UI never offers what the service refuses. Reads filter with `principal.in_scope(domain_id)`. A subject without a domain is checked by role only.
8. **Frontend.** The generated client's `fetch` (`src/lib/api-config.ts` → `src/lib/dev-user.ts`) adds `X-DMC-Dev-User` from local storage to every request. Switching persona stores the username and resets every TanStack Query cache, so nothing fetched as one persona is shown to another. `AccountMenu` (a pattern) shows the current user from `/me` and, when `/dev/users` answers, the personas.

## Consequences

- Every later slice is built and tested against real roles and scopes from the first commit. Tests act as a persona with the `personas` fixture and the header.
- Mapping identity-provider groups to roles and scopes (ARCHITECTURE §5) is still to do; it fills the same tables when OIDC lands in Phase 4.
- Roles are global and scopes are per user, not per role. If a user needs a role in one domain only, `role_assignment` gains a domain column; `Principal` would then carry scoped roles.
- No API manages users or role assignments yet; personas come from `dmc-seed`.
