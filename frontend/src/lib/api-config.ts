import type { CreateClientConfig } from "@/api/client.gen"

// Runtime config for the generated client (wired in openapi-ts.config.ts).
// Generated paths already start with /api/v1, so an empty base URL means same-origin; locally the
// Vite dev server proxies /api to the backend. main.tsx sets a separate API origin from /config.json
// when the deployment has one (src/lib/runtime-config.ts).
export const createClientConfig: CreateClientConfig = (config) => ({
  ...config,
  baseUrl: "",
})
