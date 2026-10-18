import type { QueryClient } from "@tanstack/react-query"

import { invalidateApplications } from "@/features/applications/queries"
import { invalidateAssets } from "@/features/assets/queries"

const HARVEST_QUERIES = new Set(["getHarvestStatus", "listPhysicalObjects"])

/** After a harvest or a mapping: refetch harvest status and objects, and what they feed. */
export async function invalidateHarvest(queryClient: QueryClient) {
  await Promise.all([
    queryClient.invalidateQueries({
      predicate: (query) => HARVEST_QUERIES.has((query.queryKey[0] as { _id?: string } | undefined)?._id ?? ""),
    }),
    invalidateApplications(queryClient),
    invalidateAssets(queryClient),
  ])
}
