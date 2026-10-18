import type { ProblemDetail } from "@/api"

// Generated query and mutation functions throw the parsed response body: RFC 9457 problem details
// for every API error, or something else when the request never reached the API.

function asProblem(error: unknown): Partial<ProblemDetail> & Record<string, unknown> {
  return typeof error === "object" && error !== null ? (error as Record<string, unknown>) : {}
}

export function problemStatus(error: unknown): number | undefined {
  const status = asProblem(error).status
  return typeof status === "number" ? status : undefined
}

/** The API's plain-language explanation, or a generic next step when there is none. */
export function problemMessage(error: unknown): string {
  const problem = asProblem(error)
  if (typeof problem.detail === "string" && problem.detail) return problem.detail
  return "This wasn’t saved. Check your connection, then try again."
}

/**
 * Field-level messages keyed by body field: request validation `errors` (422), or a domain error's
 * `field` extension (400, 409).
 */
export function problemFieldErrors(error: unknown): Record<string, string> {
  const problem = asProblem(error)
  const out: Record<string, string> = {}
  for (const issue of problem.errors ?? []) {
    const [where, field] = issue.loc
    if (where === "body" && typeof field === "string") out[field] = issue.msg
  }
  if (typeof problem.field === "string" && typeof problem.detail === "string") out[problem.field] = problem.detail
  return out
}
