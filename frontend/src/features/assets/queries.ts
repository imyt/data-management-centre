import type { QueryClient } from "@tanstack/react-query"

const ASSET_QUERIES = new Set(["listAssets", "getAsset", "listInbox"])

/** After a write: refetch every assets list and detail, and the Inbox, whatever their filters. */
export function invalidateAssets(queryClient: QueryClient) {
  return queryClient.invalidateQueries({
    predicate: (query) => {
      const key = query.queryKey[0] as { _id?: string } | undefined
      return ASSET_QUERIES.has(key?._id ?? "")
    },
  })
}
