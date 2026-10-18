# ADR 0008: How the contract hash is computed

- Status: accepted
- Date: 2026-10-18
- Refines: [ADR 0004](0004-environments-database-and-frontend-backend-pairing.md) §5

## Context

ADR 0004 §5 pairs a frontend bundle with its API by comparing two hashes: the one the bundle was built with, and the `contract` field of `GET /api/v1/meta`. It says `contract` is "the hash of the `contracts/openapi.json` the API was built from". Two details were left open:

- A backend image does not have to ship `contracts/openapi.json`, so the API may not have the file to read.
- With `core.autocrlf=true` (the default on Windows), a checkout can hold the file with CRLF line endings. Hashing raw bytes would then give different answers on different machines for the same commit.

## Decision

1. **One definition of the hash:** `sha256:` followed by the lowercase hex SHA-256 of the spec's UTF-8 text, after CRLF is replaced with LF. `backend/app/core/contract.py` (`contract_hash`) and `frontend/plugins/contract-hash.ts` (`contractHash`) implement it, and a test on each side pins the same value for the same text.
2. **The API hashes the spec it serves.** `GET /api/v1/meta` hashes `render_spec(app.openapi())`, the same serialization `scripts/export_openapi.py` writes to `contracts/openapi.json`. It computes this once per process. The API never reads the committed file. The contract test (`tests/test_openapi_contract.py`, and `export_openapi.py --check` in CI) fails when the committed file and the served spec differ, so in a green build the two hashes are equal.
3. **The frontend hashes the committed file at build time.** A Vite plugin (`frontend/plugins/contract-hash.ts`) exposes it as `CONTRACT_HASH` from the virtual module `virtual:dmc-contract`. It is not a `VITE_*` variable: nothing environment-specific goes into the bundle (ADR 0004 §4), and the hash depends only on the commit. In `npm run dev` the plugin watches the file, so `npm run api:sync` updates the hash without a restart.
4. **Comparison.** `comparePairing` (`frontend/src/lib/pairing.ts`) shows the update banner when the hashes differ and the environment badge when the environment is not `production`. Until `/meta` answers, or if it fails, it shows neither. The app keeps working as it did before the check existed.

## Consequences

- Any change to the spec, even to a description, changes the hash and so shows the banner to open tabs once the new API is deployed. This is intended: a description change still means the bundle and API come from different commits.
- The backend image does not need `contracts/`. The frontend build needs `../contracts/openapi.json`, which it already needs to generate the client.
