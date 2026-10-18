import { useQuery } from "@tanstack/react-query"

import type { SubjectType } from "@/api"
import { listEvaluationResultsOptions } from "@/api/@tanstack/react-query.gen"
import type { StageState } from "@/components/patterns"

/** The Assess stage of a subject in one line for the StageTracker, from its latest results. */
export function useAssessState(subjectType: SubjectType, subjectId: string): StageState {
  const query = useQuery(listEvaluationResultsOptions({ query: { subject_type: subjectType, subject_id: subjectId, limit: 50 } }))
  const results = query.data?.data
  if (!results) return { summary: "Not started", tone: "progress" }
  if (results.length === 0) return { summary: "Not evaluated", tone: "progress" }
  const failing = results.filter((r) => r.outcome === "fail").length
  if (failing > 0) return { summary: `${failing} failing`, tone: "progress" }
  if (results.some((r) => r.outcome === "error")) return { summary: "Could not evaluate", tone: "progress" }
  if (results.some((r) => r.is_stale)) return { summary: "Stale", tone: "progress" }
  return { summary: "All passing", tone: "complete" }
}
