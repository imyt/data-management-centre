import * as React from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { Link } from "react-router"

import type { CreatedAsset, HarvestStatusRead, SnapshotRead } from "@/api"
import { getHarvestStatusOptions, getJobOptions, runHarvestMutation } from "@/api/@tanstack/react-query.gen"
import { Button, StatusBadge } from "@/components/patterns"
import { problemMessage } from "@/features/applications/problem"
import { invalidateHarvest } from "@/features/harvest/queries"
import { UnmappedObjects } from "@/features/harvest/unmapped-objects"

function formatWhen(value: string) {
  return new Date(value).toLocaleString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

function plural(count: number, one: string, many: string) {
  return `${count} ${count === 1 ? one : many}`
}

function runSummary(run: SnapshotRead) {
  return [plural(run.schemas, "schema", "schemas"), plural(run.tables, "table", "tables"), plural(run.columns, "column", "columns")].join(
    ", ",
  )
}

/** A data store's harvest: last run, failures, Run harvest, and what is not yet mapped to an asset. */
export function HarvestSection({ dataStoreId, storeName }: { dataStoreId: string; storeName: string }) {
  const queryClient = useQueryClient()
  const status = useQuery(getHarvestStatusOptions({ path: { data_store_id: dataStoreId } }))
  const [jobId, setJobId] = React.useState<string | null>(null)
  const [error, setError] = React.useState<string | null>(null)
  const [created, setCreated] = React.useState<CreatedAsset[]>([])
  const start = useMutation(runHarvestMutation())

  const job = useQuery({
    ...getJobOptions({ path: { job_id: jobId ?? "" } }),
    enabled: jobId !== null,
    refetchInterval: (query) => {
      const state = query.state.data?.data.status
      return state === "queued" || state === "running" ? 1500 : false
    },
  })
  const jobState = job.data?.data.status
  const waiting = start.isPending || (jobId !== null && (jobState === undefined || jobState === "queued" || jobState === "running"))

  React.useEffect(() => {
    if (jobId !== null && jobState !== undefined && jobState !== "queued" && jobState !== "running") {
      void invalidateHarvest(queryClient)
    }
  }, [jobId, jobState, queryClient])

  if (status.isPending) return <p className="text-xs text-text-tertiary">Loading harvest status…</p>
  if (status.isError) {
    return (
      <p role="alert" className="text-xs text-danger">
        Harvest status could not be loaded.{" "}
        <button type="button" className="underline" onClick={() => void status.refetch()}>
          Try again
        </button>
      </p>
    )
  }

  const data: HarvestStatusRead = status.data.data
  const actions = status.data.allowed_actions
  const run = data.last_run

  async function onRun() {
    setError(null)
    try {
      const accepted = await start.mutateAsync({ path: { data_store_id: dataStoreId } })
      setJobId(accepted.data.id)
    } catch (e) {
      setError(problemMessage(e))
    }
  }

  return (
    <div aria-label={`Harvest of ${storeName}`} role="group" className="mt-2 flex flex-col gap-2 rounded-md bg-surface p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-muted-foreground">
          {run === null ? (
            "Not harvested yet."
          ) : run.status === "succeeded" ? (
            <>
              Last harvest <span className="mono tabular-nums">{formatWhen(run.taken_at)}</span> · {runSummary(run)}
            </>
          ) : (
            <>
              Harvest failed <span className="mono tabular-nums">{formatWhen(run.taken_at)}</span>
            </>
          )}
        </p>
        {actions.includes("run_harvest") && (
          <Button size="sm" variant="secondary" onClick={() => void onRun()} loading={waiting}>
            {waiting ? (jobState === "running" ? "Harvesting…" : "Queued…") : "Run harvest"}
          </Button>
        )}
      </div>

      {run?.status === "failed" && (
        <p role="alert" className="text-sm text-danger">
          {run.error}
          {data.objects && <span className="text-muted-foreground"> The objects below are from the last successful harvest.</span>}
        </p>
      )}
      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}
      {jobId !== null && jobState === "queued" && (
        <p className="text-xs text-text-tertiary">Waiting for the worker to pick this up.</p>
      )}

      {created.length > 0 && (
        <p role="status" className="text-sm">
          Declared {created.length === 1 ? "an asset" : `${created.length} assets`}:{" "}
          {created.map((c, i) => (
            <React.Fragment key={c.asset_id}>
              {i > 0 && ", "}
              <Link className="underline" to={`/assets?asset=${c.asset_id}`}>
                {c.asset_name}
              </Link>
            </React.Fragment>
          ))}
          . The Data Owner is asked to confirm in their Inbox.
        </p>
      )}

      {data.objects && (
        <div className="flex flex-col gap-2">
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            {data.objects.unmapped_tables === 0 && data.objects.unmapped_columns === 0 ? (
              <StatusBadge status="passing" label="Everything is mapped" size="sm" />
            ) : (
              <StatusBadge
                status="pending"
                label={`${plural(data.objects.unmapped_tables, "unmapped table", "unmapped tables")}`}
                size="sm"
              />
            )}
            <span className="mono tabular-nums">
              {data.objects.tables - data.objects.unmapped_tables}/{data.objects.tables}
            </span>{" "}
            tables mapped to assets
          </div>
          {data.objects.unmapped_tables > 0 && (
            <UnmappedObjects dataStoreId={dataStoreId} canMap={actions.includes("map_objects")} onCreated={setCreated} />
          )}
        </div>
      )}
    </div>
  )
}
