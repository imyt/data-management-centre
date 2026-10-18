# ADR 0006: The audit trail

- Status: accepted
- Date: 2026-10-18

## Context

PRD FR-U1 asks for an append-only audit trail of every change and decision, with actor, time, reason and before and after values. FR-C8 says every risk decision needs a reason. ARCHITECTURE §9 makes the trail hash-chained (`prev_hash`, `hash`) so tampering is detectable. Roadmap row 0.5 builds it before any module writes data, so every later write can use it from the start.

## Decisions

1. **One table, `audit.audit_event`,** owned by the `audit` module: `seq` (identity, chain order), `at`, `actor`, `action` (`<entity>.<verb>`, e.g. `exception.approved`), `subject_type`, `subject_id`, `reason`, `before`, `after` (`jsonb`), `prev_hash`, `hash`, and a `uuidv7()` id. An index on `(subject_type, subject_id, seq)` serves per-entity history (FR-K, FR-S4).
2. **Same transaction as the change.** Other modules call `AuditService(session).record(...)` from `app.modules.audit.service`, passing the session that makes the change. If the change rolls back, so does its event, and the reverse.
3. **Reasons.** `record(..., reason_required=True)` refuses a risk decision without a non-blank reason. Callers set this for accept risk, approve exception, approve access and approve transfer.
4. **The chain.** Each event's `hash` is SHA-256 over canonical JSON (sorted keys, no whitespace) of its fields plus `prev_hash`. The first event's `prev_hash` is 64 zeros. `before` and `after` are normalised to plain JSON before they are hashed and stored (UUIDs, datetimes and decimals become strings), so what is stored is exactly what was hashed. `verify_chain()` re-hashes every event in `seq` order and reports the first one that does not match.
5. **No forks.** Writers take a transaction-level advisory lock (`pg_advisory_xact_lock`) before reading the previous hash, and hold it until they commit. Concurrent writers therefore append one at a time, and `seq` order equals commit order. The cost is that transactions which write audit events serialise from that point until they commit. That is acceptable at DMC's write volume; if it ever isn't, the fix is batching the chain in the worker, not dropping the lock.
6. **Append-only, enforced twice.**
   - Triggers reject `UPDATE`, `DELETE` and `TRUNCATE` for every role, the owner included.
   - The migration revokes `UPDATE`, `DELETE` and `TRUNCATE` from the runtime role `dmc_app`.

   Only someone who owns the table and deliberately disables its triggers can change a row, and the chain then shows it.

## Consequences

- Tamper-evident, not tamper-proof: an edited, inserted or removed event breaks verification. Removing the newest events leaves a shorter chain that is still valid. Catching that needs the latest hash anchored outside the database (for example in signed daily digests or the audit pack), which comes with the audit pack work (FR-R6, FR-U2).
- Reads of the trail (an `/audit` endpoint, entity history panels) come with authorisation in row 0.7 and later slices. Nothing exposes the trail over the API yet.
- Retention and partitioning of `audit_event` by time are deferred until volume needs them. Both keep the chain order (`seq`).
