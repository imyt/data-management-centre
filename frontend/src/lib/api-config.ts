import type { CreateClientConfig } from "@/api/client.gen"
import { fetchAsDevUser } from "@/lib/dev-user"

// Runtime config for the generated client (wired in openapi-ts.config.ts).
// Generated paths already start with /api/v1, so an empty base URL means same-origin; locally the
// Vite dev server proxies /api to the backend. main.tsx sets a separate API origin from /config.json
// when the deployment has one (src/lib/runtime-config.ts).
// Every request carries the chosen dev persona, if any (src/lib/dev-user.ts).
export const createClientConfig: CreateClientConfig = (config) => ({
  ...config,
  baseUrl: "",
  fetch: fetchAsDevUser,
})
