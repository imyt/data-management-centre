import * as React from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { InboxIcon } from "lucide-react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import type { GalleryEntry } from "@/dev/specimen"
import { createDataTableColumns, DataTable } from "@/patterns/data-table"
import { Field, fieldA11y, ReadOnlyField } from "@/patterns/field"
import { FilterChips, type ActiveFilter } from "@/patterns/filter-chips"
import { StageStepper } from "@/patterns/stage-stepper"
import { EmptyState, ErrorState, NoAccessState } from "@/patterns/states"
import { StatusBadge, type Status } from "@/patterns/status-badge"
import { Button } from "@/ui/button"
import { Input } from "@/ui/input"
import { Skeleton } from "@/ui/skeleton"

interface Asset {
  id: string
  name: string
  owner: string | null
  status: { status: Status; label: string }
  rows: number
  updated: string
}

const assets: Asset[] = [
  { id: "AST-004821", name: "Customer master", owner: "David Vance", status: { status: "success", label: "Compliant" }, rows: 1284902, updated: "16 Oct 2026" },
  { id: "AST-004822", name: "Payment events", owner: "Elena Rostova", status: { status: "warning", label: "Due in 2h" }, rows: 48113067, updated: "15 Oct 2026" },
  { id: "AST-004830", name: "Marketing leads", owner: null, status: { status: "danger", label: "Breached" }, rows: 92410, updated: "2 Oct 2026" },
  { id: "AST-004851", name: "Supplier contracts", owner: "Sarah Chen", status: { status: "neutral", label: "Pending review" }, rows: 3120, updated: "28 Sep 2026" },
]

const manyAssets: Asset[] = Array.from({ length: 500 }, (_, i) => ({
  ...assets[i % assets.length],
  id: `AST-${String(100000 + i).padStart(6, "0")}`,
}))

const col = createDataTableColumns<Asset>()
const assetColumns = [
  col.accessor("id", { header: "ID", meta: { mono: true } }),
  col.accessor("name", { header: "Asset" }),
  col.accessor("owner", { header: "Owner" }),
  col.accessor("status", {
    header: "Status",
    enableSorting: false,
    cell: ({ getValue }) => <StatusBadge {...getValue()} />,
  }),
  col.accessor("rows", {
    header: "Rows",
    meta: { align: "right" },
    cell: ({ getValue }) => getValue().toLocaleString("en-GB"),
  }),
  col.accessor("updated", { header: "Updated", enableSorting: false }),
]

function AssetTable(props: Partial<React.ComponentProps<typeof DataTable<Asset>>>) {
  return (
    <DataTable<Asset>
      label="Assets"
      columns={assetColumns}
      data={assets}
      getRowId={(a) => a.id}
      className="w-full"
      scrollClassName="max-h-72"
      {...props}
    />
  )
}

const policySchema = z.object({
  name: z.string().trim().min(1, "Enter a policy name."),
  retention: z.coerce.number<string>().int("Enter whole days.").positive("Enter a number of days above zero."),
})

function RetentionForm({ initialErrors = false }: { initialErrors?: boolean }) {
  const form = useForm({
    resolver: zodResolver(policySchema),
    defaultValues: { name: initialErrors ? "" : "Customer data retention", retention: initialErrors ? "-30" : "365" },
    mode: "onTouched",
  })
  const { errors } = form.formState

  React.useEffect(() => {
    if (initialErrors) void form.trigger()
  }, [form, initialErrors])

  const nameId = initialErrors ? "policy-name-error" : "policy-name"
  const retentionId = initialErrors ? "retention-error" : "retention"

  return (
    <form className="flex w-full flex-col gap-4" onSubmit={form.handleSubmit(() => undefined)} noValidate>
      <Field label="Policy name" htmlFor={nameId} required error={errors.name?.message}>
        <Input {...form.register("name")} {...fieldA11y(nameId, { error: errors.name?.message })} />
      </Field>
      <Field label="Retention (days)" htmlFor={retentionId} required hint="Counted from the last update." error={errors.retention?.message}>
        <Input
          inputMode="numeric"
          className="tabular-nums"
          {...form.register("retention")}
          {...fieldA11y(retentionId, { hint: "Counted from the last update.", error: errors.retention?.message })}
        />
      </Field>
    </form>
  )
}

function ChipsDemo() {
  const [filters, setFilters] = React.useState<ActiveFilter[]>([
    { id: "domain", facet: "Domain", value: "Finance" },
    { id: "status", facet: "Status", value: "Breached" },
  ])
  if (filters.length === 0) {
    return (
      <Button variant="ghost" onClick={() => setFilters([{ id: "domain", facet: "Domain", value: "Finance" }])}>
        Restore filters
      </Button>
    )
  }
  return (
    <FilterChips
      filters={filters}
      onRemove={(id) => setFilters((f) => f.filter((x) => x.id !== id))}
      onClearAll={() => setFilters([])}
    />
  )
}

function RetryDemo() {
  const [retrying, setRetrying] = React.useState(false)
  return (
    <ErrorState
      retrying={retrying}
      onRetry={() => {
        setRetrying(true)
        window.setTimeout(() => setRetrying(false), 1200)
      }}
    />
  )
}

export const patternEntries: GalleryEntry[] = [
  {
    id: "status-badge",
    name: "StatusBadge",
    layer: "patterns",
    summary: "A record's state as tint, icon and label. Never colour alone, never the accent. SLA risk reads as text.",
    variants: (
      <div className="flex flex-wrap gap-2">
        <StatusBadge status="success" label="Compliant" />
        <StatusBadge status="warning" label="Due in 2h" />
        <StatusBadge status="danger" label="Breached" />
        <StatusBadge status="neutral" label="Pending review" />
      </div>
    ),
    states: {
      default: <StatusBadge status="success" label="Compliant" />,
      hover: { na: "not interactive." },
      focus: { na: "not interactive." },
      disabled: { na: "not interactive." },
      loading: <Skeleton className="h-5 w-24" />,
      error: <StatusBadge status="danger" label="Breached" />,
      empty: { na: "every record has a state; unknown shows an em dash in its cell." },
    },
  },
  {
    id: "field",
    name: "Field",
    layer: "patterns",
    summary:
      "Label above, control, hint, inline plain-language error. Built for react-hook-form + zod. ReadOnlyField renders locked values as text.",
    states: {
      default: <RetentionForm />,
      hover: (
        <Field label="Asset name" htmlFor="field-hover" required>
          <Input id="field-hover" defaultValue="Customer master" data-gallery-subject="" />
        </Field>
      ),
      focus: (
        <Field label="Asset name" htmlFor="field-focus" required>
          <Input id="field-focus" defaultValue="Customer master" data-gallery-subject="" />
        </Field>
      ),
      disabled: <ReadOnlyField label="Data owner" value="David Vance" controlledBy="Set by the Finance domain." />,
      loading: (
        <div className="flex w-full flex-col gap-1">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-(--control-height) w-full" />
        </div>
      ),
      error: <RetentionForm initialErrors />,
      empty: <ReadOnlyField label="Steward" value={null} />,
    },
  },
  {
    id: "filter-chips",
    name: "FilterChips",
    layer: "patterns",
    summary: "Active facets as removable chips with Clear all. The consumer syncs filter state to the URL.",
    states: {
      default: <ChipsDemo />,
      hover: (
        <FilterChips
          filters={[{ id: "domain", facet: "Domain", value: "Finance" }]}
          onRemove={() => undefined}
          onClearAll={() => undefined}
        />
      ),
      focus: (
        <FilterChips
          filters={[{ id: "domain", facet: "Domain", value: "Finance" }]}
          onRemove={() => undefined}
          onClearAll={() => undefined}
        />
      ),
      disabled: { na: "filters are always removable." },
      loading: <Skeleton className="h-8 w-40" />,
      error: { na: "an invalid URL filter is dropped with a toast." },
      empty: <p className="text-sm text-text-tertiary">No filters: the bar renders nothing.</p>,
    },
  },
  {
    id: "stage-stepper",
    name: "StageStepper",
    layer: "patterns",
    summary: "Where a record is in a linear workflow. Stages come from configuration; only valid next steps are offered.",
    states: {
      default: <StageStepper stages={["Submitted", "Steward review", "Owner approval", "Published"]} current={1} />,
      hover: { na: "not interactive." },
      focus: { na: "not interactive." },
      disabled: { na: "not interactive." },
      loading: <Skeleton className="h-5 w-64" />,
      error: { na: "a rejected record shows a StatusBadge next to the stepper." },
      empty: { na: "records without a linear process use StatusBadge only." },
    },
  },
  {
    id: "data-table",
    name: "DataTable",
    layer: "patterns",
    wide: true,
    summary:
      "TanStack Table on shadcn's Table: sticky header, hairline rows, sort, selection, mono IDs, right-aligned numbers, em dash for empty, row click opens detail. Virtualises past 100 rows.",
    variants: (
      <div className="flex flex-col gap-2">
        <p className="text-xs text-text-tertiary">500 rows, virtualised, selectable</p>
        <DataTable<Asset>
          label="All assets"
          columns={assetColumns}
          data={manyAssets}
          getRowId={(a) => a.id}
          selectable
          onRowOpen={() => undefined}
        />
      </div>
    ),
    states: {
      default: <AssetTable onRowOpen={() => undefined} />,
      hover: { na: "rows highlight in bg-subtle on hover (see default)." },
      focus: { na: "rows that open a detail panel are tabbable; Enter opens (see default)." },
      disabled: { na: "rows are never disabled; explain read-only in the detail panel." },
      loading: <AssetTable loading />,
      error: <AssetTable data={[]} error={{ onRetry: () => undefined }} />,
      empty: (
        <AssetTable
          data={[]}
          empty={{ title: "No assets in Finance yet", description: "Register a source to harvest its tables." }}
        />
      ),
    },
  },
  {
    id: "states",
    name: "EmptyState, ErrorState, NoAccessState",
    layer: "patterns",
    summary: "Required for every data view. Calm, short, one clear next step. No stock artwork.",
    states: {
      default: (
        <EmptyState
          icon={InboxIcon}
          title="No findings to review"
          description="New violations appear here after the next scan."
          action={<Button variant="secondary">Run a scan now</Button>}
        />
      ),
      hover: { na: "see the action's button states." },
      focus: { na: "see the action's button states." },
      disabled: <NoAccessState askWho="the domain owner, David Vance," />,
      loading: { na: "loading uses skeletons shaped like the content." },
      error: <RetryDemo />,
      empty: <EmptyState icon={InboxIcon} title="Nothing assigned to you" />,
    },
  },
]
