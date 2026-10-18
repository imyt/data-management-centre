# ADR 0009: Background work in Postgres: jobs, outbox and idempotency keys

- Status: accepted
- Date: 2026-10-18

## Context

ARCHITECTURE §1 and §3 run background work (harvests, scans, evaluations, exports, notifications, scheduled sweeps) in a worker process from the same codebase, on a Postgres job queue, with no other infrastructure. §5 has modules react to each other through domain events in an outbox, written in the same transaction as the change. §8 has long operations answer `202` with a job id to poll at `/api/v1/jobs/{id}`, and retryable writes accept an `Idempotency-Key`. Roadmap row 0.6 builds all of it before the first module needs it.

## Decisions

1. **It lives in core, in a `platform` schema.** Every module needs it and none owns it. `app/core/jobs/` holds the queue (`queue.py`), the registry, the worker loop, `GET /jobs/{id}` and the housekeeping job; `app/core/outbox.py` and `app/core/idempotency.py` hold the outbox and the keys. Their tables are `platform.job`, `platform.worker_heartbeat`, `platform.outbox_event`, `platform.outbox_delivery` and `platform.idempotency_key`. `migrations/env.py` imports core's models as well as every module's.
2. **Core never imports modules.** Core declares a `Registry` of job handlers by kind, event handlers by type, and schedules. `app/worker.py` is the worker's composition root, like `app/main.py` is the API's: `build_registry()` registers each module's handlers. Import-linter puts `app.worker` beside `app.seed`, above the modules.
3. **Writes join the caller's transaction.** `enqueue(session, kind, payload, ...)` and `publish(session, type, payload)` add a row with the session that makes the change, so a job or event exists only if the change commits.
4. **The job queue.**
   - A job is `queued`, `running`, `succeeded`, `failed` or `cancelled`. Kinds and event types are named `<module>.<verb>`.
   - A worker claims the oldest due job of a kind it handles with `UPDATE … WHERE id = (SELECT … FOR UPDATE SKIP LOCKED LIMIT 1)`, in its own short transaction. That sets `running`, increments `attempts` and takes a lease: `locked_by` (the worker's id) and `locked_at`.
   - The handler runs in a second transaction with the job's writes. Marking the job `succeeded` (with its `result`) happens in that same transaction, so the work and its success commit together. Before that, the worker re-reads the job `FOR UPDATE` and checks the lease is still its own. If it is not, everything rolls back.
   - A failed attempt is recorded in a third transaction. The job goes back to `queued` with `run_after = now() + 10s × 2^(attempt − 1)`, capped at an hour, until `max_attempts` (default 5) is used up; then it is `failed`. `PermanentJobError` fails it at once. `error` keeps the last failure.
   - While a handler runs, a thread refreshes `locked_at` every third of the lease (`DMC_JOB_LEASE_SECONDS`, default 300). Workers requeue `running` jobs whose lease has not been refreshed for a whole lease, or fail them if they are out of attempts. Only a dead or hung worker loses a lease, so long jobs are safe.
   - `enqueue(..., idempotency_key=...)` queues at most one job per kind and key (`UNIQUE (kind, idempotency_key)`); a repeat returns the first job.
   - `JobContext.set_progress(percent)` writes `progress` in its own transaction, so `GET /jobs/{id}` shows it while the job runs.
5. **The outbox.**
   - The worker locks a batch of pending events with `FOR UPDATE SKIP LOCKED` and hands each one to every handler registered for its type.
   - Each handler runs in a savepoint that also inserts `outbox_delivery (event_id, handler)`. A handler's writes and its delivery record commit together, and a handler that has a delivery record is skipped. When an event is retried, handlers that already succeeded don't run again.
   - If any handler fails, the event's `attempts`, `last_error` and `available_at` (the same backoff as jobs) are updated and it is tried again later. When all handlers have succeeded, `processed_at` is set. An event type with no handlers is marked processed.
   - Handlers should be quick, because the batch stays locked until it is done. Heavy work belongs in a job the handler enqueues, keyed `event:<event id>`, which also makes the enqueue idempotent.
   - Events are delivered in roughly `created_at` order. Ordering is not guaranteed across retries or workers.
6. **The scheduler** is code, not a table. `registry.every(interval, kind, payload)` divides time into slots of `interval` from the epoch. Each pass, a worker enqueues the current slot's job with the idempotency key `schedule:<name>:<slot>`. Workers racing for a slot queue one job between them. A worker that was down for several slots enqueues only the current one. The platform's own schedule is `platform.purge`, hourly: it deletes expired idempotency keys, processed events older than 7 days and heartbeats older than 7 days.
7. **The worker** is `uv run dmc-worker`.
   - At start-up it checks the database revision as the API does (`ensure_database_is_current`).
   - Each pass does stalled-job recovery (every half lease), then schedules, then one batch of events, then one job. It polls every `DMC_WORKER_POLL_SECONDS` (default 1) when idle.
   - SIGINT or SIGTERM stops it after the current job; a second signal exits at once, and the lease expiry then recovers the job.
   - It upserts `platform.worker_heartbeat` (`beat_at`) at least every 10 seconds, and sets `stopped_at` when it stops, for the health reporting in row 0.10.
   - It logs like the API (`configure_logging`); records carry `worker_id`, and `job_id` and `job_kind` or `event_id` and `event_type` while it works on one (`log_context`).
8. **The API.**
   - `GET /api/v1/jobs/{id}` returns a `JobResponse` envelope: status, progress, result, error, attempts and timestamps, never the payload. It needs a signed-in caller. Callers see the jobs they created (`created_by = principal.actor`); governance sees every job, including the scheduler's. Anyone else's job answers 404, like a missing one.
   - A route that starts a job returns `accepted(request, job)`: `202`, the `JobResponse` and `Location: /api/v1/jobs/{id}`. It declares `status_code=202, response_model=JobResponse`.
9. **`Idempotency-Key`.**
   - A route opts in by taking `IdempotencyDep` and returning its response through `idempotency.record(response)`. The header is optional (1 to 255 characters) and is documented on the operation.
   - In the request's own transaction, the dependency inserts `(owner, key, request hash)`. `owner` is the caller's `Principal.actor`, and the hash covers the method, path, query and body. `record` stores the status, body, `Content-Type` and `Location` in the same row. If the request fails it rolls back, key included, so the client can retry it.
   - A repeat with the same key and hash replays the stored response with `Idempotent-Replayed: true`. The same key with a different hash is a 409 problem. A concurrent repeat blocks on the first request's uncommitted row, then replays its response.
   - Keys expire after 24 hours. A route that takes the dependency but forgets `record` fails with a 500, so the mistake shows up in its first test.

## Consequences

- No module enqueues or publishes yet. The first slice that does adds its handlers to `build_registry()` and its first `202` route.
- Running jobs cannot be cancelled. Cancelling a queued job (`queue.cancel`) has no route until a job needs one.
- Finished jobs are kept for now. Retention comes with the first job volume that needs it.
- Every pass polls. If latency or idle load matters, `LISTEN`/`NOTIFY` can wake the worker without changing the tables.
- A rolling deploy could run an old worker that marks a new event type processed before a new worker's handler sees it. DMC deploys one worker, so this is accepted. If it changes, workers should leave events with no handlers pending.
