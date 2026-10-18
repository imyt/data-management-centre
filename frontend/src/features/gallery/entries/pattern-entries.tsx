import * as React from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { InboxIcon } from "lucide-react"
import { useForm } from "react-hook-form"
import { Link } from "react-router"
import { z } from "zod"

import {
  ConfirmWithReason,
  createDataTableColumns,
  DataTable,
  DetailLayout,
  DetailSplit,
  DmcMark,
  EmptyState,
  EntityHeader,
  ErrorState,
  ExplainWhy,
  Field,
  fieldA11y,
  FilterChips,
  LoadingState,
  NoAccessState,
  NotFoundState,
  PostureReadout,
  ReadOnlyField,
  ScopeSwitcher,
  STAGES,
  StageTracker,
  stageTabId,
  STATUSES,
  StatusBadge,
  useDetail,
  useDetailParam,
  type ActiveFilter,
  type Stage,
  type StageState,
  type Status,
} from "@/components/patterns"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { Textarea } from "@/components/ui/textarea"
import type { GalleryEntry } from "@/features/gallery/specimen"

/* ---------- sample data ---------- */

interface Asset {
  id: string
  name: string
  owner: string | null
  status: Status
  rows: number
  updated: string
}

const assets: Asset[] = [
  { id: "AST-10482", name: "Customer orders", owner: "Priya Nair", status: "failing", rows: 1284902, updated: "16 Oct 2026" },
  { id: "AST-10511", name: "Payroll ledger", owner: "Tom Becker", status: "excepted", rows: 48113067, updated: "15 Oct 2026" },
  { id: "AST-10533", name: "Product catalogue", owner: null, status: "passing", rows: 92410, updated: "2 Oct 2026" },
  { id: "AST-10560", name: "Marketing consent", owner: "Ana Costa", status: "pending", rows: 3120, updated: "28 Sep 2026" },
]

const manyAssets: Asset[] = Array.from({ length: 500 }, (_, i) => ({
  ...assets[i % assets.length],
  id: `AST-${String(100000 + i).padStart(6, "0")}`,
}))

/** Fixed, so screenshots don't drift. */
const EVALUATED_AT = "2026-10-17T07:42:00Z"

/* ---------- DataTable ---------- */

const col = createDataTableColumns<Asset>()
const assetColumns = [
  col.accessor("id", { header: "ID", meta: { mono: true } }),
  col.accessor("name", { header: "Asset" }),
  col.accessor("owner", { header: "Owner" }),
  col.accessor("status", {
    header: "Status",
    enableSorting: false,
    cell: ({ getValue }) => <StatusBadge status={getValue()} />,
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

/* ---------- Field ---------- */

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

/* ---------- FilterChips ---------- */

function ChipsDemo() {
  const [filters, setFilters] = React.useState<ActiveFilter[]>([
    { id: "domain", facet: "Domain", value: "Finance" },
    { id: "status", facet: "Status", value: "Failing" },
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

/* ---------- StageTracker ---------- */

const trackerStates: Record<string, Record<Stage, StageState>> = {
  default: {
    know: { summary: "Complete", tone: "complete" },
    assess: { summary: "3 controls failing", tone: "attention" },
    act: { summary: "2 actions open", tone: "progress" },
    assure: { summary: "1 fix awaiting verification", tone: "progress" },
  },
  complete: {
    know: { summary: "Complete", tone: "complete" },
    assess: { summary: "All controls passing", tone: "complete" },
    act: { summary: "No open actions", tone: "complete" },
    assure: { summary: "Verified 17 Oct", tone: "complete" },
  },
  attention: {
    know: { summary: "Harvest failed", tone: "attention" },
    assess: { summary: "Waiting on Know", tone: "progress" },
    act: { summary: "Waiting on Assess", tone: "progress" },
    assure: { summary: "Waiting on Act", tone: "progress" },
  },
  empty: {
    know: { summary: "Not started", tone: "progress" },
    assess: { summary: "Not started", tone: "progress" },
    act: { summary: "Not started", tone: "progress" },
    assure: { summary: "Not started", tone: "progress" },
  },
}

function StageTrackerDemo({ id, states, initial = "assess" }: { id: string; states: Record<Stage, StageState>; initial?: Stage }) {
  const [stage, setStage] = React.useState<Stage>(initial)
  const panelId = `${id}-panel`
  return (
    <div className="flex w-full flex-col gap-3">
      <StageTracker entityName="Customer orders" panelId={panelId} selected={stage} onSelect={setStage} states={states} />
      <div
        id={panelId}
        role="tabpanel"
        aria-labelledby={stageTabId(panelId, stage)}
        className="rounded-md bg-subtle p-4 text-sm text-muted-foreground"
      >
        {STAGES.find((s) => s.id === stage)?.label} panel: {states[stage].summary}
      </div>
    </div>
  )
}

/* ---------- ConfirmWithReason ---------- */

function ConfirmDemo({ trigger, fail = false, slow = false }: { trigger: string; fail?: boolean; slow?: boolean }) {
  const [open, setOpen] = React.useState(false)
  return (
    <>
      <Button variant="secondary" onClick={() => setOpen(true)}>
        {trigger}
      </Button>
      <ConfirmWithReason
        open={open}
        onOpenChange={setOpen}
        title="Accept risk on Customer orders?"
        description="The failing control stays open as an exception until it expires."
        impact="Affects 1 Confidential asset and 2 applications."
        confirmLabel="Accept risk"
        onConfirm={async () => {
          await new Promise((resolve) => window.setTimeout(resolve, slow ? 2400 : 600))
          if (fail) throw new Error("The exception wasn’t saved because the control changed. Reload and try again.")
        }}
      />
    </>
  )
}

/* ---------- DetailSplit ---------- */

function AssetList() {
  const [selected, open] = useDetailParam("asset")
  return (
    <ul className="divide-y bg-surface">
      {assets.map((a) => (
        <li key={a.id}>
          <Link
            to={`?asset=${a.id}`}
            onClick={(event) => {
              if (event.metaKey || event.ctrlKey || event.shiftKey) return // let ⌘-click open a new tab
              event.preventDefault()
              open(a.id)
            }}
            aria-current={selected === a.id ? "true" : undefined}
            className="flex items-center gap-3 px-4 py-3 text-sm transition-colors duration-fast hover:bg-subtle aria-[current=true]:bg-brand-bg"
          >
            <span className="mono w-24 text-muted-foreground">{a.id}</span>
            <span className="flex-1 truncate">{a.name}</span>
            <StatusBadge status={a.status} size="sm" />
          </Link>
        </li>
      ))}
      <li>
        <Link
          to="?asset=AST-99999"
          onClick={(event) => {
            if (event.metaKey || event.ctrlKey || event.shiftKey) return
            event.preventDefault()
            open("AST-99999")
          }}
          className="flex items-center gap-3 px-4 py-3 text-sm text-muted-foreground transition-colors duration-fast hover:bg-subtle"
        >
          <span className="mono w-24">AST-99999</span>
          <span className="flex-1 truncate">A deleted asset (shows not found)</span>
        </Link>
      </li>
    </ul>
  )
}

function AssetDetail({ id }: { id: string }) {
  const asset = assets.find((a) => a.id === id)
  const { setDirty } = useDetail()
  const [confirmOpen, setConfirmOpen] = React.useState(false)

  if (!asset) return <NotFoundState kind="asset" />

  return (
    <DetailLayout
      header={
        <EntityHeader
          kind="Asset"
          identifier={asset.id}
          title={asset.name}
          status={asset.status}
          explain={
            <ExplainWhy
              reason="Encryption at rest is failing on the production store, and this asset is classified Confidential."
              sources={[{ label: "Policy: Encryption at rest" }, { label: "Classification: Confidential" }]}
              evaluatedAt={EVALUATED_AT}
            />
          }
          meta={[
            { label: "Owner", value: asset.owner ?? "—" },
            { label: "Classification", value: "Confidential" },
            { label: "Applications", value: "Order service, Billing" },
          ]}
        />
      }
      footer={
        <>
          <Button variant="outline" onClick={() => setConfirmOpen(true)}>
            Accept risk
          </Button>
          <Button>Create action</Button>
        </>
      }
    >
      <div className="flex flex-col gap-1">
        <Label htmlFor="asset-notes">Notes</Label>
        <Textarea id="asset-notes" rows={4} onChange={() => setDirty(true)} />
        <p className="text-xs text-text-tertiary">Type here, then close the panel to see the unsaved-changes guard.</p>
      </div>
      <ConfirmWithReason
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={`Accept risk on ${asset.name}?`}
        description="The failing control stays open as an exception until it expires."
        impact="Affects 1 Confidential asset and 2 applications."
        confirmLabel="Accept risk"
        onConfirm={() => new Promise((resolve) => window.setTimeout(resolve, 600))}
      />
    </DetailLayout>
  )
}

/* ---------- small demos ---------- */

function ScopeDemo() {
  const [scope, setScope] = React.useState("finance")
  return (
    <ScopeSwitcher
      options={[
        { id: "all", label: "All domains" },
        { id: "finance", label: "Finance" },
        { id: "customer", label: "Customer" },
      ]}
      value={scope}
      onChange={setScope}
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

const minutesAgo = (m: number) => new Date(Date.now() - m * 60_000)

export const patternEntries: GalleryEntry[] = [
  {
    id: "dmc-mark",
    name: "DmcMark",
    layer: "patterns",
    summary:
      "Four corners framing a diamond: Know, Assess, Act, Assure clockwise from top left. As an indicator, lit corners use the accent and unlit corners --mark-idle.",
    variants: (
      <div className="flex flex-wrap items-end gap-8">
        <DmcMark size={64} />
        <DmcMark size={32} />
        <DmcMark size={16} />
        {STAGES.map((s) => (
          <div key={s.id} className="flex flex-col items-center gap-1">
            <DmcMark size={32} lit={[s.id]} title={`${s.label} lit`} />
            <span className="text-xs text-muted-foreground">{s.label}</span>
          </div>
        ))}
      </div>
    ),
    states: {
      default: <DmcMark size={32} />,
      hover: { na: "not interactive." },
      focus: { na: "not interactive." },
      disabled: { na: "not interactive." },
      loading: { na: "the mark is static; the tracker next to it shows loading." },
      error: <DmcMark size={32} lit={["know", "assess"]} title="2 of 4 stages complete" />,
      empty: <DmcMark size={32} lit={[]} title="No stages complete" />,
    },
  },
  {
    id: "status-badge",
    name: "StatusBadge",
    layer: "patterns",
    summary: "The one status language: passing, failing, excepted, pending, not applicable. Same colour, icon and word everywhere; never the accent.",
    variants: (
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap gap-2">
          {STATUSES.map((s) => (
            <StatusBadge key={s} status={s} />
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          {STATUSES.map((s) => (
            <StatusBadge key={s} status={s} size="sm" />
          ))}
        </div>
      </div>
    ),
    states: {
      default: <StatusBadge status="passing" />,
      hover: { na: "not interactive." },
      focus: { na: "not interactive." },
      disabled: <StatusBadge status="not_applicable" />,
      loading: <Skeleton className="h-6 w-20" />,
      error: <StatusBadge status="failing" />,
      empty: { na: "every result has a status; a missing one shows an em dash in its cell." },
    },
  },
  {
    id: "stage-tracker",
    name: "StageTracker",
    layer: "patterns",
    wide: true,
    summary:
      "Where one asset or application is in Know, Assess, Act, Assure, as tabs over the stage panels. Arrow keys move between stages; the mark lights completed stages.",
    states: {
      default: <StageTrackerDemo id="tracker-default" states={trackerStates.default} />,
      hover: <StageTrackerDemo id="tracker-hover" states={trackerStates.default} initial="know" />,
      focus: <StageTrackerDemo id="tracker-focus" states={trackerStates.default} />,
      disabled: { na: "every stage can be viewed; actions inside a panel carry their own reasons." },
      loading: <Skeleton className="h-16 w-full" />,
      error: <StageTrackerDemo id="tracker-error" states={trackerStates.attention} initial="know" />,
      empty: <StageTrackerDemo id="tracker-empty" states={trackerStates.empty} initial="know" />,
    },
    variants: <StageTrackerDemo id="tracker-complete" states={trackerStates.complete} initial="assure" />,
  },
  {
    id: "entity-header",
    name: "EntityHeader",
    layer: "patterns",
    wide: true,
    summary: "Same summary shape for every entity, in pages and in sheets: kind and mono ID, title, status with why, key facts, actions with the primary last.",
    states: {
      default: (
        <EntityHeader
          kind="Application"
          identifier="APP-0042"
          title="Order service"
          status="passing"
          meta={[
            { label: "App owner", value: "Marcus Lee" },
            { label: "Hosting", value: "Cloud" },
            { label: "Applied controls", value: <span className="mono tabular-nums">14</span> },
            { label: "Lifecycle", value: "Active" },
          ]}
          actions={<Button variant="outline">Edit</Button>}
          className="w-full"
        />
      ),
      hover: { na: "see the action's button states." },
      focus: { na: "see the action's button states." },
      disabled: (
        <EntityHeader
          kind="Application"
          identifier="APP-0042"
          title="Order service"
          status="passing"
          actions={
            <Button variant="outline" disabled disabledReason="Only the app owner can edit this application.">
              Edit
            </Button>
          }
          className="w-full"
        />
      ),
      loading: (
        <div role="status" className="flex w-full flex-col gap-2">
          <span className="sr-only">Loading application</span>
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-6 w-64" />
          <Skeleton className="h-8 w-full" />
        </div>
      ),
      error: (
        <EntityHeader
          kind="Asset"
          identifier="AST-10482"
          title="Customer orders"
          status="failing"
          explain={
            <ExplainWhy
              reason="Encryption at rest is failing on the production store, and this asset is classified Confidential."
              sources={[{ label: "Policy: Encryption at rest" }]}
              evaluatedAt={EVALUATED_AT}
            />
          }
          meta={[{ label: "Owner", value: "Priya Nair" }]}
          className="w-full"
        />
      ),
      empty: (
        <EntityHeader
          kind="Asset"
          identifier="AST-10601"
          title="Untitled export"
          meta={[
            { label: "Owner", value: <span className="text-text-tertiary">—</span> },
            { label: "Classification", value: <span className="text-text-tertiary">—</span> },
          ]}
          className="w-full"
        />
      ),
    },
  },
  {
    id: "explain-why",
    name: "ExplainWhy",
    layer: "patterns",
    summary: "Every derived decision says why, from what, and when it was evaluated. Sources link to the asset, policy or rule.",
    states: {
      default: (
        <span className="flex items-center gap-2 text-sm">
          Encryption at rest is required
          <ExplainWhy
            reason="Required because Customer orders is classified Confidential."
            sources={[{ label: "Customer orders (AST-10482)", to: "/gallery?asset=AST-10482" }, { label: "Policy: Encryption at rest" }]}
            evaluatedAt={EVALUATED_AT}
          />
        </span>
      ),
      hover: <ExplainWhy reason="Required because Customer orders is classified Confidential." />,
      focus: <ExplainWhy reason="Required because Customer orders is classified Confidential." />,
      disabled: { na: "the reason is always available." },
      loading: { na: "reasons arrive with the item they explain." },
      error: (
        <ExplainWhy
          label="Why failing?"
          reason="The last evaluation couldn’t reach the production store, so this result is from the previous run."
          evaluatedAt={EVALUATED_AT}
        />
      ),
      empty: <ExplainWhy reason="Set by hand by Priya Nair; no rule derived it." />,
    },
  },
  {
    id: "confirm-with-reason",
    name: "ConfirmWithReason",
    layer: "patterns",
    summary: "Risk decisions preview their impact and require a reason, recorded in the audit trail. The confirm button uses the action's verb.",
    states: {
      default: <ConfirmDemo trigger="Accept risk" />,
      hover: { na: "see the trigger's button states." },
      focus: { na: "focus moves to the reason and returns to the trigger on close." },
      disabled: <ConfirmDemo trigger="Open, then leave the reason short" />,
      loading: <ConfirmDemo trigger="Open, then confirm (slow)" slow />,
      error: <ConfirmDemo trigger="Open, then confirm (fails)" fail />,
      empty: { na: "always has a title, an impact and a reason field." },
    },
  },
  {
    id: "portal-header",
    name: "PortalHeader",
    layer: "patterns",
    summary:
      "Mark and full name, the five sections with the Inbox count, search (⌘K), scope, posture with freshness, account. Live at the top of this page; parts below.",
    states: {
      default: <PostureReadout posture={{ passingPercent: 92, evaluatedAt: minutesAgo(4) }} to="/reports" />,
      hover: <ScopeDemo />,
      focus: <ScopeDemo />,
      disabled: { na: "sections a user can never open are hidden, not disabled." },
      loading: <PostureReadout loading to="/reports" />,
      error: <PostureReadout posture={{ passingPercent: 71, evaluatedAt: minutesAgo(180) }} to="/reports" />,
      empty: <PostureReadout posture={null} to="/reports" />,
    },
  },
  {
    id: "app-shell",
    name: "AppShell",
    layer: "patterns",
    summary:
      "Header above, section sidebar, main. The sidebar collapses to icons below 1280px and remembers the user's choice. This page is the live example.",
    states: {
      default: { na: "this page is framed by AppShell." },
      hover: { na: "sidebar links tint on hover (see the sidebar)." },
      focus: { na: "Tab once from the top: Skip to content appears." },
      disabled: { na: "pages a user can never open are hidden." },
      loading: { na: "the frame renders at once; content loads inside main." },
      error: { na: "errors show inside main, never in the frame." },
      empty: { na: "a section with one page still shows its sidebar." },
    },
  },
  {
    id: "detail-split",
    name: "DetailSplit, DetailLayout",
    layer: "patterns",
    wide: true,
    summary:
      "List plus detail with the selection in the URL. Docked and resizable at 1536px and wider, a sheet below. Unsaved changes ask before closing.",
    states: {
      default: (
        <div className="h-96 w-full overflow-hidden rounded-md border">
          <DetailSplit param="asset" label="Asset details" list={<AssetList />}>
            {(id) => <AssetDetail id={id} />}
          </DetailSplit>
        </div>
      ),
      hover: { na: "rows tint on hover (see default)." },
      focus: { na: "rows are links; Enter opens, Esc closes the panel (see default)." },
      disabled: { na: "rows always open; the detail explains what can't be changed." },
      loading: <LoadingState label="Loading asset" className="w-full" />,
      error: <NotFoundState kind="asset" />,
      empty: { na: "with nothing selected the list takes the full width (see default)." },
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
          <Input id="field-hover" defaultValue="Customer orders" data-gallery-subject="" />
        </Field>
      ),
      focus: (
        <Field label="Asset name" htmlFor="field-focus" required>
          <Input id="field-focus" defaultValue="Customer orders" data-gallery-subject="" />
        </Field>
      ),
      disabled: <ReadOnlyField label="Data owner" value="Priya Nair" controlledBy="Set by the Finance domain." />,
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
    name: "EmptyState, ErrorState, NoAccessState, NotFoundState, LoadingState",
    layer: "patterns",
    wide: true,
    summary: "Every data view handles loading, empty, error, no access and not found. Calm, short, one clear next step. No artwork.",
    variants: (
      <div className="grid grid-cols-5 gap-4">
        <EmptyState
          title="No applied controls yet"
          description="Link this application to its data assets and DMC will derive the controls it needs."
          action={<Button>Link assets</Button>}
        />
        <ErrorState onRetry={() => undefined} />
        <NoAccessState requirement="the Data Owner role for this asset" />
        <NotFoundState kind="asset" />
        <LoadingState />
      </div>
    ),
    states: {
      default: (
        <EmptyState
          icon={InboxIcon}
          title="Nothing needs you"
          description="New approvals and failing controls appear here."
          action={<Button variant="secondary">Open assets</Button>}
        />
      ),
      hover: { na: "see the action's button states." },
      focus: { na: "see the action's button states." },
      disabled: <NoAccessState requirement="the Data Owner role for this asset" askWho="the domain owner, Priya Nair," />,
      loading: <LoadingState label="Loading applied controls" className="w-full" />,
      error: <RetryDemo />,
      empty: <EmptyState icon={InboxIcon} title="Nothing assigned to you" />,
    },
  },
]
