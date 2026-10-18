import { useQuery } from "@tanstack/react-query"

import type { SubjectType } from "@/api"
import { listAppliedControlsOptions, listEvaluationResultsOptions } from "@/api/@tanstack/react-query.gen"
import { EmptyState, ErrorState, ExplainWhy, LoadingState } from "@/components/patterns"
import { ResultPanel } from "@/features/evaluation/result-panel"
import { ResultStatus } from "@/features/evaluation/result-status"

/** The Assess stage of a subject: each control that applies to it, with its latest result and facts. */
export function AssessSection({ subjectType, subjectId }: { subjectType: SubjectType; subjectId: string }) {
  const applied = useQuery(listAppliedControlsOptions({ query: { subject_type: subjectType, subject_id: subjectId, limit: 50 } }))
  const results = useQuery(
    listEvaluationResultsOptions({ query: { subject_type: subjectType, subject_id: subjectId, limit: 50 } }),
  )

  if (applied.isPending || results.isPending) return <LoadingState label="Loading applied controls" />
  if (applied.isError || results.isError) {
    return (
      <ErrorState
        onRetry={() => {
          void applied.refetch()
          void results.refetch()
        }}
        retrying={applied.isFetching || results.isFetching}
      />
    )
  }

  const rows = applied.data.data
  if (rows.length === 0) {
    return (
      <EmptyState
        title="No applied controls yet"
        description="Applied controls appear here once policies select this subject."
      />
    )
  }
  const latest = new Map(results.data.data.map((r) => [r.applied_control_id, r]))

  return (
    <div className="flex flex-col gap-4">
      <ul className="flex flex-col gap-4">
        {rows.map((row) => (
          <li key={row.id} className="rounded-md border p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="flex flex-wrap items-baseline gap-2 text-sm">
                <span className="mono font-medium tabular-nums">{row.control.code}</span>
                <span>{row.control.name}</span>
              </p>
              <span className="flex items-center gap-3">
                <ResultStatus result={latest.get(row.id)} />
                <ExplainWhy
                  label="Why this applies"
                  reason={row.reason}
                  sources={[{ label: `${row.control.code}, rule version ${row.rule_version}` }]}
                />
              </span>
            </div>
            <div className="mt-3 border-t pt-3">
              <ResultPanel appliedControlId={row.id} />
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
