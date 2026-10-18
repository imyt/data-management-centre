import { useQuery } from "@tanstack/react-query"

import type { EvaluationResultRead } from "@/api"
import { listEvaluationResultsOptions } from "@/api/@tanstack/react-query.gen"
import { EmptyState, ErrorState, ExplainWhy, LoadingState, NoAccessState } from "@/components/patterns"
import { problemStatus } from "@/features/applications/problem"
import { factRows, measurement, resultSources } from "@/features/evaluation/facts"
import { OutcomeBadge, ResultFreshness, ResultStatus } from "@/features/evaluation/result-status"
import { RunEvaluationButton } from "@/features/evaluation/run-evaluation"
import { formatTimestamp } from "@/lib/format"

const HISTORY = 10

/** One result in full: what was measured, why that is the verdict, the facts, and how fresh it is. */
export function ResultBody({ result }: { result: EvaluationResultRead }) {
  const measured = measurement(result)
  const facts = factRows(result)
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <ResultStatus result={result} size="default" />
        {measured && (
          <p className="text-sm">
            <span className="mono font-medium tabular-nums">{measured.measured}</span>
            <span className="text-muted-foreground"> measured, limit </span>
            <span className="mono tabular-nums">{measured.threshold}</span>
          </p>
        )}
      </div>
      <p className="text-sm">
        {result.reason}{" "}
        <ExplainWhy reason={result.reason} sources={resultSources(result)} evaluatedAt={result.evaluated_at} />
      </p>
      {facts.length > 0 && (
        <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm">
          {facts.map((fact) => (
            <div key={fact.label} className="contents">
              <dt className="text-xs text-muted-foreground">{fact.label}</dt>
              <dd className="mono tabular-nums">{fact.value}</dd>
            </div>
          ))}
        </dl>
      )}
      <ResultFreshness result={result} />
    </div>
  )
}

/**
 * The evaluation of one applied control: the latest result in full, the results before it, and
 * Run evaluation when the API offers it.
 */
export function ResultPanel({ appliedControlId }: { appliedControlId: string }) {
  const query = useQuery(
    listEvaluationResultsOptions({ query: { applied_control_id: appliedControlId, latest_only: false, limit: HISTORY } }),
  )

  if (query.isPending) return <LoadingState label="Loading the evaluation" />
  if (query.isError) {
    if (problemStatus(query.error) === 403) return <NoAccessState requirement="access to this subject’s domain" />
    return <ErrorState onRetry={() => void query.refetch()} retrying={query.isFetching} />
  }

  const [latest, ...earlier] = query.data.data
  const canRun = query.data.allowed_actions.includes("run_evaluation")

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h4 className="text-sm font-medium">Evaluation</h4>
        {canRun && <RunEvaluationButton target={{ applied_control_id: appliedControlId }} />}
      </div>
      {latest ? (
        <ResultBody result={latest} />
      ) : (
        <EmptyState
          title="Not evaluated yet"
          description="The worker evaluates a control when it applies, and on a schedule. Run the evaluation to check it now."
        />
      )}
      {earlier.length > 0 && (
        <details className="text-sm">
          <summary className="cursor-pointer text-xs text-muted-foreground">
            Earlier results (<span className="mono tabular-nums">{earlier.length}</span>
            {(query.data.meta.total ?? 0) > HISTORY ? ` of ${(query.data.meta.total ?? 0) - 1}` : ""})
          </summary>
          <ul className="mt-2 flex flex-col divide-y rounded-md border">
            {earlier.map((result) => (
              <li key={result.id} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
                <span className="flex items-center gap-2">
                  <OutcomeBadge outcome={result.outcome} />
                  <time dateTime={result.evaluated_at} title={result.evaluated_at} className="mono text-xs tabular-nums">
                    {formatTimestamp(new Date(result.evaluated_at))}
                  </time>
                </span>
                <span className="text-xs text-muted-foreground">{measurement(result)?.measured ?? result.reason}</span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  )
}
