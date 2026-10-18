import type { QueryClient } from "@tanstack/react-query"

const CONTROL_QUERIES = new Set([
  "listPolicies",
  "getPolicy",
  "listControls",
  "getControl",
  "listAppliedControls",
  "getAppliedControl",
])

/** After a write: refetch every policy, control and applied-control query, whatever its filters. */
export function invalidateControls(queryClient: QueryClient) {
  return queryClient.invalidateQueries({
    predicate: (query) => {
      const key = query.queryKey[0] as { _id?: string } | undefined
      return CONTROL_QUERIES.has(key?._id ?? "")
    },
  })
}

/**
 * Applied controls are derived by a background job after a rule changes, so they lag the write by a
 * moment: look again shortly after, and once more for a busy worker.
 */
export function invalidateControlsSoon(queryClient: QueryClient) {
  for (const delay of [1500, 5000]) window.setTimeout(() => void invalidateControls(queryClient), delay)
  return invalidateControls(queryClient)
}
