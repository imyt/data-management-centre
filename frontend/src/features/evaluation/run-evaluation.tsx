import * as React from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import type { RunEvaluationData } from "@/api"
import { getJobOptions, runEvaluationMutation } from "@/api/@tanstack/react-query.gen"
import { Button } from "@/components/patterns"
import { problemMessage } from "@/features/applications/problem"
import { invalidateEvaluation } from "@/features/evaluation/queries"

type Target = NonNullable<RunEvaluationData["body"]>

function outcomeOf(result: unknown): string | null {
  if (typeof result !== "object" || result === null) return null
  const counts = result as Record<string, unknown>
  if (typeof counts.error === "number" && counts.error > 0) return "A new result was recorded: the rule could not be evaluated."
  if (typeof counts.written === "number" && counts.written > 0) return "A new result was recorded."
  if (typeof counts.unchanged === "number" && counts.unchanged > 0) return "Nothing has changed since the latest result."
  return null
}

/** Queues an evaluation, follows the job, and refetches the results when it finishes. */
export function RunEvaluationButton({ target, label = "Run evaluation" }: { target: Target; label?: string }) {
  const queryClient = useQueryClient()
  const start = useMutation(runEvaluationMutation())
  const [jobId, setJobId] = React.useState<string | null>(null)
  const [error, setError] = React.useState<string | null>(null)

  const job = useQuery({
    ...getJobOptions({ path: { job_id: jobId ?? "" } }),
    enabled: jobId !== null,
    refetchInterval: (query) => {
      const state = query.state.data?.data.status
      return state === "queued" || state === "running" ? 1000 : false
    },
  })
  const state = job.data?.data.status
  const running = start.isPending || (jobId !== null && (state === undefined || state === "queued" || state === "running"))

  React.useEffect(() => {
    if (jobId !== null && state !== undefined && state !== "queued" && state !== "running") {
      void invalidateEvaluation(queryClient)
    }
  }, [jobId, state, queryClient])

  async function onRun() {
    setError(null)
    setJobId(null)
    try {
      const accepted = await start.mutateAsync({ body: target })
      setJobId(accepted.data.id)
    } catch (e) {
      setError(problemMessage(e))
    }
  }

  const failed = state === "failed" || state === "cancelled"
  return (
    <div className="flex flex-col items-end gap-1">
      <Button size="sm" variant="secondary" onClick={() => void onRun()} loading={running}>
        {running ? (state === "running" ? "Evaluating…" : "Queued…") : label}
      </Button>
      {running && state === "queued" && <p className="text-xs text-text-tertiary">Waiting for the worker to pick this up.</p>}
      {state === "succeeded" && <p role="status" className="text-xs text-muted-foreground">{outcomeOf(job.data?.data.result) ?? "Evaluated."}</p>}
      {(error || failed) && (
        <p role="alert" className="text-xs text-danger">
          {error ?? "The evaluation did not finish. Try again."}
        </p>
      )}
    </div>
  )
}
