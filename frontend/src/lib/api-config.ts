import type { CreateClientConfig } from "@/api/client.gen"

// Runtime config for the generated client (wired in openapi-ts.config.ts).
export const createClientConfig: CreateClientConfig = (config) => ({
  ...config,
  baseUrl: import.meta.env.VITE_API_BASE_URL,
})
