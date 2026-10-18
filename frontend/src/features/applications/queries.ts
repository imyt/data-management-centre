import type { QueryClient } from "@tanstack/react-query"

const APPLICATION_QUERIES = new Set(["listApplications", "getApplication"])

/** After a write: refetch every applications list and detail, whatever their filters. */
export function invalidateApplications(queryClient: QueryClient) {
  return queryClient.invalidateQueries({
    predicate: (query) => {
      const key = query.queryKey[0] as { _id?: string } | undefined
      return APPLICATION_QUERIES.has(key?._id ?? "")
    },
  })
}
