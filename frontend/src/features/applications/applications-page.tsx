import * as React from "react"
import { useInfiniteQuery } from "@tanstack/react-query"
import { PlusIcon } from "lucide-react"

import type { ApplicationRead, LifecycleStatus } from "@/api"
import { listApplicationsInfiniteOptions } from "@/api/@tanstack/react-query.gen"
import {
  Button,
  createDataTableColumns,
  DataTable,
  DetailSplit,
  NoAccessState,
  SelectInput,
  TextInput,
  useDetailParam,
} from "@/components/patterns"
import { useSearchParam } from "@/hooks/use-search-param"
import { ApplicationDetailView, NewApplicationView } from "@/features/applications/application-detail"
import { CRITICALITY, HOSTING, LIFECYCLE, optionsOf } from "@/features/applications/labels"
import { problemStatus } from "@/features/applications/problem"
import { useScopeDomain } from "@/features/shell/scope"
import { Screen } from "@/features/shell/screen"

/** `?application=new` opens the register form in the detail panel. */
const NEW = "new"
const ALL_LIFECYCLES = "all"
const PAGE_SIZE = 50

const col = createDataTableColumns<ApplicationRead>()
const columns = [
  col.accessor("code", { header: "Code", meta: { mono: true } }),
  col.accessor("name", { header: "Application" }),
  col.accessor((a) => a.domain.name, { id: "domain", header: "Domain" }),
  col.accessor((a) => CRITICALITY[a.criticality], { id: "criticality", header: "Criticality" }),
  col.accessor((a) => HOSTING[a.hosting], { id: "hosting", header: "Hosting" }),
  col.accessor((a) => LIFECYCLE[a.lifecycle_status], { id: "lifecycle", header: "Lifecycle" }),
]

const lifecycleOptions = [{ value: ALL_LIFECYCLES, label: "Any lifecycle" }, ...optionsOf(LIFECYCLE)]

function isLifecycle(value: string | null): value is LifecycleStatus {
  return value !== null && value in LIFECYCLE
}

/** Applications: the registered applications, filtered on the server, with detail beside the list. */
export function ApplicationsPage() {
  return (
    <Screen title="Applications">
      <DetailSplit param="application" label="Application details" list={<ApplicationList />}>
        {(id) => (id === NEW ? <NewApplicationView /> : <ApplicationDetailView key={id} id={id} />)}
      </DetailSplit>
    </Screen>
  )
}

function ApplicationList() {
  const domainId = useScopeDomain()
  const [, open] = useDetailParam("application")
  const [q, setQ] = useSearchParam("q")
  const [lifecycleParam, setLifecycle] = useSearchParam("lifecycle")
  const lifecycle = isLifecycle(lifecycleParam) ? lifecycleParam : undefined
  const [search, setSearch] = React.useState(q ?? "")

  // Search runs on the server; wait for a pause in typing before asking.
  React.useEffect(() => {
    const next = search.trim() || null
    if (next === (q ?? null)) return
    const timer = window.setTimeout(() => setQ(next), 300)
    return () => window.clearTimeout(timer)
  }, [search, q, setQ])

  const query = useInfiniteQuery({
    ...listApplicationsInfiniteOptions({
      query: { limit: PAGE_SIZE, q: q ?? undefined, domain_id: domainId ?? undefined, lifecycle_status: lifecycle },
    }),
    // The generated query function treats any object as page params, null included; {} is the first page.
    initialPageParam: {},
    getNextPageParam: (page) => page.meta.next_cursor ?? undefined,
  })

  const first = query.data?.pages[0]
  const rows = React.useMemo(() => query.data?.pages.flatMap((p) => p.data) ?? [], [query.data])
  const canCreate = first?.allowed_actions.includes("create") ?? false
  const filtered = Boolean(q || lifecycle || domainId)

  if (query.isError && problemStatus(query.error) === 403) {
    return <NoAccessState requirement="a role that can see applications" />
  }

  return (
    <div className="flex flex-col gap-4 pr-4">
      <div className="flex flex-wrap items-center gap-3">
        <TextInput
          type="search"
          aria-label="Search applications by name or code"
          placeholder="Search by name or code"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className="w-64"
        />
        <SelectInput
          id="lifecycle-filter"
          aria-label="Filter by lifecycle"
          options={lifecycleOptions}
          value={lifecycle ?? ALL_LIFECYCLES}
          onValueChange={(value) => setLifecycle(value === ALL_LIFECYCLES ? null : value)}
          className="w-44"
        />
        {first && (
          <span className="mono text-sm text-muted-foreground tabular-nums" aria-live="polite">
            {first.meta.total ?? rows.length} {(first.meta.total ?? rows.length) === 1 ? "application" : "applications"}
          </span>
        )}
        {canCreate && (
          <Button className="ml-auto" onClick={() => open(NEW)}>
            <PlusIcon aria-hidden="true" />
            Register application
          </Button>
        )}
      </div>

      <DataTable<ApplicationRead>
        label="Applications"
        columns={columns}
        data={rows}
        getRowId={(a) => a.id}
        loading={query.isPending}
        error={query.isError ? { onRetry: () => void query.refetch(), retrying: query.isFetching } : undefined}
        empty={
          filtered
            ? { title: "No applications match", description: "Try another search, lifecycle or scope." }
            : {
                title: "No applications yet",
                description: "Register an application to record its environments and data stores.",
                action: canCreate ? <Button onClick={() => open(NEW)}>Register application</Button> : undefined,
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
