import type { QueryClient } from "@tanstack/react-query"

const EVALUATION_QUERIES = new Set(["listEvaluationResults", "getEvaluationResult"])

/** After an evaluation ran: refetch every result query, whatever its filters. */
export function invalidateEvaluation(queryClient: QueryClient) {
  return queryClient.invalidateQueries({
    predicate: (query) => EVALUATION_QUERIES.has((query.queryKey[0] as { _id?: string } | undefined)?._id ?? ""),
  })
}
