import type { EvaluationResultRead, Outcome } from "@/api"
import { StatusBadge, type Status } from "@/components/patterns"
import { formatTimestamp } from "@/lib/format"

/** `error` is not a failure: it says the rule could not be checked, so it never wears the failing colours. */
const OUTCOME: Record<Outcome, { status: Status; label?: string }> = {
  pass: { status: "passing" },
  fail: { status: "failing" },
  error: { status: "pending", label: "Could not evaluate" },
  not_applicable: { status: "not_applicable" },
}

export function OutcomeBadge({ outcome, size = "sm" }: { outcome: Outcome; size?: "sm" | "default" }) {
  const { status, label } = OUTCOME[outcome]
  return <StatusBadge status={status} label={label} size={size} />
}

/** The latest result as a badge, with "Stale" beside it once its freshness window has passed. */
export function ResultStatus({ result, size = "sm" }: { result: EvaluationResultRead | undefined; size?: "sm" | "default" }) {
  if (!result) return <StatusBadge status="pending" label="Not evaluated yet" size={size} />
  return (
    <span className="inline-flex flex-wrap items-center gap-1.5">
      <OutcomeBadge outcome={result.outcome} size={size} />
      {result.is_stale && (
        <span className="text-xs font-medium text-status-excepted" title={`Stale since ${result.stale_after}`}>
          Stale
        </span>
      )}
    </span>
  )
}

/** When a result was produced and when it goes stale (DESIGN.md: freshness is visible). */
export function ResultFreshness({ result }: { result: EvaluationResultRead }) {
  const evaluated = new Date(result.evaluated_at)
  const staleAfter = new Date(result.stale_after)
  return (
    <p className="text-xs text-muted-foreground">
      Evaluated{" "}
      <time dateTime={evaluated.toISOString()} title={evaluated.toISOString()} className="mono tabular-nums">
        {formatTimestamp(evaluated)}
      </time>
      {result.is_stale ? (
        <span className="font-medium text-status-excepted">
          {" "}
          · stale since{" "}
          <time dateTime={staleAfter.toISOString()} title={staleAfter.toISOString()} className="mono tabular-nums">
            {formatTimestamp(staleAfter)}
          </time>
          : run the evaluation again
        </span>
      ) : (
        <>
          {" "}
          · current until{" "}
          <time dateTime={staleAfter.toISOString()} title={staleAfter.toISOString()} className="mono tabular-nums">
            {formatTimestamp(staleAfter)}
          </time>
        </>
      )}
    </p>
  )
}
