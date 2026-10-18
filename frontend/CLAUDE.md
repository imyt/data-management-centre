# Frontend rules

Follow `../DESIGN.md`.

- Screens live in `src/features/*` and import UI only from `@/components/patterns`. Never import from `@/components/ui` in features.
- Add a missing pattern to `src/components/patterns` and show every state of it in the gallery (`src/features/gallery`).
- Colours, spacing and radius come from tokens. No raw hex or arbitrary Tailwind values.
- Status is always `StatusBadge`. Derived decisions get `ExplainWhy`. Risk decisions go through `ConfirmWithReason`.
- Detail views use `DetailSplit` with the selection in the URL so every view is deep-linkable.
- Every data view handles loading, empty, error, no access and not found.
- Render actions from the API's `allowed_actions`; never infer permissions in the client.
- IDs, counts and timestamps use the mono font with tabular figures.
- Per-environment values come from `/config.json` at runtime, never `VITE_*`. The shell checks `GET /api/v1/meta` against the contract hash embedded at build time (`plugins/contract-hash.ts`, ADR 0008) and shows `UpdateBanner` on a mismatch.
