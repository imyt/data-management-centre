// Per-environment values the UI needs at runtime (ADR 0004 §4). The deployment serves /config.json
// from its environment variables, so one build promotes from dev to production unchanged.
// Nothing environment-specific goes into a VITE_* variable.
export interface RuntimeConfig {
  /** Origin of the DMC API when it is not served from the frontend's origin, e.g. https://dmc-api.example.com. */
  apiBaseUrl?: string
}

/** Loads /config.json. Missing or malformed means defaults: the API is same-origin under /api. */
export async function loadRuntimeConfig(): Promise<RuntimeConfig> {
  try {
    const response = await fetch("/config.json", { cache: "no-store" })
    if (!response.ok || !response.headers.get("content-type")?.includes("json")) return {}
    const body: unknown = await response.json()
    return parseRuntimeConfig(body)
  } catch {
    return {}
  }
}

export function parseRuntimeConfig(body: unknown): RuntimeConfig {
  if (typeof body !== "object" || body === null) return {}
  const { apiBaseUrl } = body as Record<string, unknown>
  return typeof apiBaseUrl === "string" && apiBaseUrl !== "" ? { apiBaseUrl: apiBaseUrl.replace(/\/+$/, "") } : {}
}
