import * as React from "react"
import { useInfiniteQuery } from "@tanstack/react-query"
import { PlusIcon } from "lucide-react"

import type { AppliedControlRead, ControlStatus, ControlSummary } from "@/api"
import { listAppliedControlsInfiniteOptions, listControlsInfiniteOptions } from "@/api/@tanstack/react-query.gen"
import {
  Button,
  createDataTableColumns,
  DataTable,
  DetailSplit,
  ExplainWhy,
  NoAccessState,
  SelectInput,
  StatusBadge,
  TextInput,
  useDetailParam,
} from "@/components/patterns"
import { problemStatus } from "@/features/applications/problem"
import { ControlDetailView, NewControlView } from "@/features/controls/control-detail"
import { subjectLabel } from "@/features/controls/labels"
import { NewPolicyView, NEW_POLICY, PolicyDetailView, PolicyList } from "@/features/controls/policies"
import { Screen } from "@/features/shell/screen"
import { useSearchParam } from "@/hooks/use-search-param"

type View = "applied" | "library" | "policies"

const VIEWS: { id: View; label: string }[] = [
  { id: "applied", label: "Applied controls" },
  { id: "library", label: "Control library" },
  { id: "policies", label: "Policies" },
]

/** `?control=new` opens the add form in the detail panel. */
const NEW = "new"
const ALL = "all"
const PAGE_SIZE = 50

function isView(value: string | null): value is View {
  return VIEWS.some((v) => v.id === value)
}

/** Controls: what applies where and why (Applied controls), the library it comes from, and the policies behind it. */
export function ControlsPage() {
  const [viewParam, setView] = useSearchParam("view")
  const view: View = isView(viewParam) ? viewParam : "applied"

  return (
    <Screen title="Controls">
      <nav aria-label="Controls views" className="flex gap-2">
        {VIEWS.map((v) => (
          <Button
            key={v.id}
            variant={v.id === view ? "secondary" : "ghost"}
            aria-current={v.id === view ? "page" : undefined}
            onClick={() => setView(v.id === "applied" ? null : v.id)}
          >
            {v.label}
          </Button>
        ))}
      </nav>
      {view === "policies" ? (
        <DetailSplit param="policy" label="Policy details" list={<PolicyList />}>
          {(id) => (id === NEW_POLICY ? <NewPolicyView /> : <PolicyDetailView key={id} id={id} />)}
        </DetailSplit>
      ) : (
        <DetailSplit param="control" label="Control details" list={view === "library" ? <LibraryList /> : <AppliedList />}>
          {(id) => (id === NEW ? <NewControlView /> : <ControlDetailView key={id} id={id} />)}
        </DetailSplit>
      )}
    </Screen>
  )
}

const controlColumns = (() => {
  const col = createDataTableColumns<ControlSummary>()
  return [
    col.accessor("code", { header: "Code", meta: { mono: true } }),
    col.accessor("name", { header: "Control" }),
    col.accessor((c) => c.policy.name, { id: "policy", header: "Policy" }),
    col.accessor("rule_type_label", { header: "Rule" }),
    col.accessor((c) => subjectLabel(c.subject_type), { id: "applies", header: "Applies to" }),
    col.accessor("applied_count", { header: "Applied", meta: { align: "right", mono: true } }),
    col.display({
      id: "status",
      header: "Status",
      cell: ({ row }) =>
        row.original.status === "retired" ? <StatusBadge status="not_applicable" label="Retired" size="sm" /> : <span className="text-muted-foreground">Active</span>,
    }),
  ]
})()

const STATUS_OPTIONS = [
  { value: "active", label: "Active" },
  { value: "retired", label: "Retired" },
  { value: ALL, label: "Any status" },
]

function LibraryList() {
  const [, open] = useDetailParam("control")
  const [q, setQ] = useSearchParam("q")
  const [statusParam, setStatus] = useSearchParam("status")
  const status: ControlStatus | undefined = statusParam === ALL ? undefined : statusParam === "retired" ? "retired" : "active"
  const [search, setSearch] = React.useState(q ?? "")

  React.useEffect(() => {
    const next = search.trim() || null
    if (next === (q ?? null)) return
    const timer = window.setTimeout(() => setQ(next), 300)
    return () => window.clearTimeout(timer)
  }, [search, q, setQ])

  const query = useInfiniteQuery({
    ...listControlsInfiniteOptions({ query: { limit: PAGE_SIZE, q: q ?? undefined, status } }),
    initialPageParam: {},
    getNextPageParam: (page) => page.meta.next_cursor ?? undefined,
  })

  const first = query.data?.pages[0]
  const rows = React.useMemo(() => query.data?.pages.flatMap((p) => p.data) ?? [], [query.data])
  const canCreate = first?.allowed_actions.includes("create_control") ?? false

  if (query.isError && problemStatus(query.error) === 403) return <NoAccessState requirement="a role that can see controls" />

  return (
    <div className="flex flex-col gap-4 pr-4">
      <div className="flex flex-wrap items-center gap-3">
        <TextInput
          type="search"
          aria-label="Search controls by name or code"
          placeholder="Search by name or code"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className="w-64"
        />
        <SelectInput
          id="status-filter"
          aria-label="Filter by status"
          options={STATUS_OPTIONS}
          value={statusParam === ALL || statusParam === "retired" ? statusParam : "active"}
          onValueChange={(value) => setStatus(value === "active" ? null : value)}
          className="w-40"
        />
        {first && (
          <span className="mono text-sm text-muted-foreground tabular-nums" aria-live="polite">
            {first.meta.total ?? rows.length} {(first.meta.total ?? rows.length) === 1 ? "control" : "controls"}
          </span>
        )}
        {canCreate && (
          <Button className="ml-auto" onClick={() => open(NEW)}>
            <PlusIcon aria-hidden="true" />
            Add control
          </Button>
        )}
      </div>

      <DataTable<ControlSummary>
        label="Control library"
        columns={controlColumns}
        data={rows}
        getRowId={(c) => c.id}
        loading={query.isPending}
        error={query.isError ? { onRetry: () => void query.refetch(), retrying: query.isFetching } : undefined}
        empty={
          q || statusParam
            ? { title: "No controls match", description: "Try another search or status." }
            : {
                title: "No controls yet",
                description: "A control is a check with a rule and the attributes it applies to.",
                action: canCreate ? <Button onClick={() => open(NEW)}>Add control</Button> : undefined,
              }
        }
        onRowOpen={(c) => open(c.id)}
      />

      {query.hasNextPage && (
        <Button variant="secondary" className="self-center" onClick={() => void query.fetchNextPage()} loading={query.isFetchingNextPage}>
          Load more
        </Button>
      )}
    </div>
  )
}

const appliedColumns = (() => {
  const col = createDataTableColumns<AppliedControlRead>()
  return [
    col.accessor((a) => a.subject.name, { id: "subject", header: "Subject" }),
    col.accessor((a) => subjectLabel(a.subject.type), { id: "kind", header: "Kind" }),
    col.accessor((a) => `${a.control.code} · ${a.control.name}`, { id: "control", header: "Control" }),
    col.accessor((a) => a.accountable?.display_name ?? "Nobody yet", { id: "accountable", header: "Accountable" }),
    col.display({
      id: "status",
      header: "Status",
      cell: () => <StatusBadge status="pending" label="Not evaluated yet" size="sm" />,
    }),
    col.display({
      id: "why",
      header: "Why",
      cell: ({ row }) => (
        // The row opens the control; "Why?" must not.
        <span onClick={(event) => event.stopPropagation()} onKeyDown={(event) => event.stopPropagation()}>
          <ExplainWhy
            reason={row.original.reason}
            sources={[{ label: `${row.original.control.code}, rule version ${row.original.rule_version}` }]}
          />
        </span>
      ),
    }),
  ]
})()

function AppliedList() {
  const [, open] = useDetailParam("control")
  const query = useInfiniteQuery({
    ...listAppliedControlsInfiniteOptions({ query: { limit: PAGE_SIZE } }),
    initialPageParam: {},
    getNextPageParam: (page) => page.meta.next_cursor ?? undefined,
  })

  const first = query.data?.pages[0]
  const rows = React.useMemo(() => query.data?.pages.flatMap((p) => p.data) ?? [], [query.data])

  if (query.isError && problemStatus(query.error) === 403) return <NoAccessState requirement="a role that can see controls" />

  return (
    <div className="flex flex-col gap-4 pr-4">
      {first && (
        <span className="mono text-sm text-muted-foreground tabular-nums" aria-live="polite">
          {first.meta.total ?? rows.length} applied {(first.meta.total ?? rows.length) === 1 ? "control" : "controls"}
        </span>
      )}
      <DataTable<AppliedControlRead>
        label="Applied controls"
        columns={appliedColumns}
        data={rows}
        getRowId={(a) => a.id}
        loading={query.isPending}
        error={query.isError ? { onRetry: () => void query.refetch(), retrying: query.isFetching } : undefined}
        empty={{
          title: "No applied controls yet",
          description: "A control applies to every asset, data store or application with the attributes it selects. They appear here as soon as one matches.",
        }}
        onRowOpen={(a) => open(a.control.id)}
      />
      {query.hasNextPage && (
        <Button variant="secondary" className="self-center" onClick={() => void query.fetchNextPage()} loading={query.isFetchingNextPage}>
          Load more
        </Button>
      )}
    </div>
  )
}
