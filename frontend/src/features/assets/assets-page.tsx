import * as React from "react"
import { useInfiniteQuery } from "@tanstack/react-query"
import { PlusIcon } from "lucide-react"

import type { AssetSummary, AssetType } from "@/api"
import { listAssetsInfiniteOptions } from "@/api/@tanstack/react-query.gen"
import {
  Button,
  createDataTableColumns,
  DataTable,
  DetailSplit,
  NoAccessState,
  SelectInput,
  StatusBadge,
  TextInput,
  useDetailParam,
} from "@/components/patterns"
import { useSearchParam } from "@/hooks/use-search-param"
import { optionsOf } from "@/features/applications/labels"
import { problemStatus } from "@/features/applications/problem"
import { AssetDetailView, NewAssetView } from "@/features/assets/asset-detail"
import { ASSET_TYPE, OWNERSHIP_STATUS } from "@/features/assets/labels"
import { useScopeDomain } from "@/features/shell/scope"
import { Screen } from "@/features/shell/screen"

/** `?asset=new` opens the declare form in the detail panel. */
const NEW = "new"
const ALL_TYPES = "all"
const PAGE_SIZE = 50

const col = createDataTableColumns<AssetSummary>()
const columns = [
  col.accessor("name", { header: "Asset" }),
  col.accessor((a) => ASSET_TYPE[a.type], { id: "type", header: "Type" }),
  col.accessor((a) => a.domain.name, { id: "domain", header: "Domain" }),
  col.accessor((a) => a.data_category?.name ?? "Not declared", { id: "category", header: "Category" }),
  col.accessor((a) => a.owner?.user.display_name ?? "Unassigned", {
    id: "owner",
    header: "Data Owner",
    cell: ({ row }) => {
      const owner = row.original.owner
      if (!owner) return <span className="text-text-tertiary">Unassigned</span>
      const state = OWNERSHIP_STATUS[owner.status]
      return (
        <span className="flex flex-wrap items-center gap-2">
          {owner.user.display_name}
          <StatusBadge status={state.status} label={state.label} size="sm" />
        </span>
      )
    },
  }),
]

const typeOptions = [{ value: ALL_TYPES, label: "Any type" }, ...optionsOf(ASSET_TYPE)]

function isType(value: string | null): value is AssetType {
  return value !== null && value in ASSET_TYPE
}

/** Assets: the declared assets, filtered on the server, with detail beside the list. */
export function AssetsPage() {
  return (
    <Screen title="Assets">
      <DetailSplit param="asset" label="Asset details" list={<AssetList />}>
        {(id) => (id === NEW ? <NewAssetView /> : <AssetDetailView key={id} id={id} />)}
      </DetailSplit>
    </Screen>
  )
}

function AssetList() {
  const domainId = useScopeDomain()
  const [, open] = useDetailParam("asset")
  const [q, setQ] = useSearchParam("q")
  const [typeParam, setType] = useSearchParam("type")
  const type = isType(typeParam) ? typeParam : undefined
  const [search, setSearch] = React.useState(q ?? "")

  // Search runs on the server; wait for a pause in typing before asking.
  React.useEffect(() => {
    const next = search.trim() || null
    if (next === (q ?? null)) return
    const timer = window.setTimeout(() => setQ(next), 300)
    return () => window.clearTimeout(timer)
  }, [search, q, setQ])

  const query = useInfiniteQuery({
    ...listAssetsInfiniteOptions({
      query: { limit: PAGE_SIZE, q: q ?? undefined, domain_id: domainId ?? undefined, type },
    }),
    // The generated query function treats any object as page params, null included; {} is the first page.
    initialPageParam: {},
    getNextPageParam: (page) => page.meta.next_cursor ?? undefined,
  })

  const first = query.data?.pages[0]
  const rows = React.useMemo(() => query.data?.pages.flatMap((p) => p.data) ?? [], [query.data])
  const canCreate = first?.allowed_actions.includes("create") ?? false
  const filtered = Boolean(q || type || domainId)

  if (query.isError && problemStatus(query.error) === 403) {
    return <NoAccessState requirement="a role that can see assets" />
  }

  return (
    <div className="flex flex-col gap-4 pr-4">
      <div className="flex flex-wrap items-center gap-3">
        <TextInput
          type="search"
          aria-label="Search assets by name"
          placeholder="Search by name"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className="w-64"
        />
        <SelectInput
          id="type-filter"
          aria-label="Filter by type"
          options={typeOptions}
          value={type ?? ALL_TYPES}
          onValueChange={(value) => setType(value === ALL_TYPES ? null : value)}
          className="w-40"
        />
        {first && (
          <span className="mono text-sm text-muted-foreground tabular-nums" aria-live="polite">
            {first.meta.total ?? rows.length} {(first.meta.total ?? rows.length) === 1 ? "asset" : "assets"}
          </span>
        )}
        {canCreate && (
          <Button className="ml-auto" onClick={() => open(NEW)}>
            <PlusIcon aria-hidden="true" />
            Declare asset
          </Button>
        )}
      </div>

      <DataTable<AssetSummary>
        label="Assets"
        columns={columns}
        data={rows}
        getRowId={(a) => a.id}
        loading={query.isPending}
        error={query.isError ? { onRetry: () => void query.refetch(), retrying: query.isFetching } : undefined}
        empty={
          filtered
            ? { title: "No assets match", description: "Try another search, type or scope." }
            : {
                title: "No assets yet",
                description: "Declare a dataset to record its category, context and owners.",
                action: canCreate ? <Button onClick={() => open(NEW)}>Declare asset</Button> : undefined,
              }
        }
        onRowOpen={(a) => open(a.id)}
      />

      {query.hasNextPage && (
        <Button variant="secondary" className="self-center" onClick={() => void query.fetchNextPage()} loading={query.isFetchingNextPage}>
          Load more
        </Button>
      )}
    </div>
  )
}
