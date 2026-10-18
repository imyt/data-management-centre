import * as React from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import type { CreatedAsset, PhysicalObjectRead } from "@/api"
import {
  createAssetsFromTablesMutation,
  listAssetsOptions,
  listPhysicalObjectsOptions,
  listRetentionPoliciesOptions,
  listUsersOptions,
  mapTableMutation,
} from "@/api/@tanstack/react-query.gen"
import { Button, EmptyState, ErrorState, Field, fieldA11y, LoadingState, SelectInput } from "@/components/patterns"
import { problemMessage } from "@/features/applications/problem"
import { invalidateHarvest } from "@/features/harvest/queries"

function rowsLabel(table: PhysicalObjectRead) {
  return table.row_count === null ? "" : `~${table.row_count.toLocaleString("en-GB")} rows`
}

/** The tables harvest found that no asset stores yet, with the actions that map them (FR-K3, FR-K4). */
export function UnmappedObjects({
  dataStoreId,
  canMap,
  onCreated,
}: {
  dataStoreId: string
  canMap: boolean
  onCreated: (assets: CreatedAsset[]) => void
}) {
  const [selected, setSelected] = React.useState<ReadonlySet<string>>(new Set())
  const [mappingPath, setMappingPath] = React.useState<string | null>(null)
  const tables = useQuery(
    listPhysicalObjectsOptions({
      path: { data_store_id: dataStoreId },
      query: { kind: "table", mapped: false, limit: 200 },
    }),
  )

  if (tables.isPending) return <LoadingState label="Loading unmapped tables" />
  if (tables.isError) return <ErrorState onRetry={() => void tables.refetch()} retrying={tables.isFetching} />

  const rows = tables.data.data
  const toggle = (path: string) =>
    setSelected((current) => {
      const next = new Set(current)
      if (next.has(path)) next.delete(path)
      else next.add(path)
      return next
    })
  const chosen = rows.filter((r) => selected.has(r.path))

  return (
    <div className="flex flex-col gap-3">
      {rows.length === 0 ? (
        <EmptyState title="Every table is mapped" description="New tables from the next harvest appear here." />
      ) : (
        <ul aria-label="Unmapped tables" className="flex flex-col divide-y rounded-md border">
          {rows.map((table) => (
            <li key={table.id} className="flex flex-col gap-2 p-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <label className="flex items-center gap-2 text-sm">
                  {canMap && (
                    <input
                      type="checkbox"
                      className="size-4 accent-primary"
                      checked={selected.has(table.path)}
                      onChange={() => toggle(table.path)}
                    />
                  )}
                  <span className="mono">{table.path}</span>
                  <span className="mono text-xs tabular-nums text-muted-foreground">{rowsLabel(table)}</span>
                </label>
                {canMap && mappingPath !== table.path && (
                  <Button variant="ghost" size="sm" onClick={() => setMappingPath(table.path)}>
                    Map to existing asset
                  </Button>
                )}
              </div>
              {mappingPath === table.path && (
                <MapToAsset dataStoreId={dataStoreId} path={table.path} onDone={() => setMappingPath(null)} />
              )}
            </li>
          ))}
        </ul>
      )}

      {canMap && chosen.length > 0 && (
        <CreateAssetsForm
          dataStoreId={dataStoreId}
          paths={chosen.map((c) => c.path)}
          onCreated={(assets) => {
            onCreated(assets)
            setSelected(new Set())
          }}
        />
      )}
    </div>
  )
}

function CreateAssetsForm({
  dataStoreId,
  paths,
  onCreated,
}: {
  dataStoreId: string
  paths: string[]
  onCreated: (assets: CreatedAsset[]) => void
}) {
  const queryClient = useQueryClient()
  const policies = useQuery(listRetentionPoliciesOptions())
  const owners = useQuery(listUsersOptions({ query: { role: "data_owner" } }))
  const create = useMutation(createAssetsFromTablesMutation())
  const [policyId, setPolicyId] = React.useState("")
  const [ownerId, setOwnerId] = React.useState("")
  const [error, setError] = React.useState<string | null>(null)
  const count = paths.length

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (policyId === "") return
    setError(null)
    try {
      const result = await create.mutateAsync({
        path: { data_store_id: dataStoreId },
        body: { paths, retention_policy_id: policyId, owner_id: ownerId === "" ? null : ownerId },
      })
      await invalidateHarvest(queryClient)
      onCreated(result.data)
    } catch (e) {
      setError(problemMessage(e))
    }
  }

  return (
    <form
      aria-label="Declare assets for the selected tables"
      className="flex flex-col gap-3 rounded-md border bg-surface-raised p-3"
      onSubmit={(event) => void onSubmit(event)}
      noValidate
    >
      <p className="text-sm font-medium">
        Declare {count === 1 ? "an asset" : `${count} assets`} for the selected {count === 1 ? "table" : "tables"}
      </p>
      <p className="text-xs text-muted-foreground">
        Each is a stored dataset in this application’s domain, with a data element per column.
      </p>
      <Field label="Retention policy" htmlFor="harvest-retention" required>
        <SelectInput
          {...fieldA11y("harvest-retention", {})}
          options={(policies.data?.data ?? []).map((p) => ({ value: p.id, label: p.name }))}
          value={policyId}
          onValueChange={setPolicyId}
          placeholder="Choose how long the data may be kept"
        />
      </Field>
      <Field label="Data Owner" htmlFor="harvest-owner" hint="They are asked to confirm in their Inbox.">
        <SelectInput
          {...fieldA11y("harvest-owner", { hint: "They are asked to confirm in their Inbox." })}
          options={(owners.data?.data ?? []).map((u) => ({ value: u.id, label: u.display_name }))}
          value={ownerId}
          onValueChange={setOwnerId}
          placeholder="Choose later"
        />
      </Field>
      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}
      <div className="flex justify-end">
        <Button
          type="submit"
          loading={create.isPending}
          disabled={policyId === ""}
          disabledReason="Choose a retention policy."
        >
          Declare {count === 1 ? "asset" : "assets"}
        </Button>
      </div>
    </form>
  )
}

function MapToAsset({ dataStoreId, path, onDone }: { dataStoreId: string; path: string; onDone: () => void }) {
  const queryClient = useQueryClient()
  const assets = useQuery(listAssetsOptions({ query: { limit: 200 } }))
  const map = useMutation(mapTableMutation())
  const [assetId, setAssetId] = React.useState("")
  const [error, setError] = React.useState<string | null>(null)
  const id = `map-${path}`

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (assetId === "") return
    setError(null)
    try {
      await map.mutateAsync({ path: { data_store_id: dataStoreId }, body: { path, asset_id: assetId } })
      await invalidateHarvest(queryClient)
      onDone()
    } catch (e) {
      setError(problemMessage(e))
    }
  }

  return (
    <form
      aria-label={`Map ${path} to an existing asset`}
      className="flex flex-col gap-3 rounded-md border bg-surface-raised p-3"
      onSubmit={(event) => void onSubmit(event)}
      noValidate
    >
      <Field
        label="Asset"
        htmlFor={id}
        required
        hint="Its columns are matched to the asset’s data elements by name; missing ones are added."
      >
        <SelectInput
          {...fieldA11y(id, { hint: "Its columns are matched to the asset’s data elements by name; missing ones are added." })}
          options={(assets.data?.data ?? []).map((a) => ({ value: a.id, label: a.name }))}
          value={assetId}
          onValueChange={setAssetId}
          placeholder="Choose an asset"
        />
      </Field>
      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onDone}>
          Cancel
        </Button>
        <Button type="submit" loading={map.isPending} disabled={assetId === ""} disabledReason="Choose an asset.">
          Map table
        </Button>
      </div>
    </form>
  )
}
