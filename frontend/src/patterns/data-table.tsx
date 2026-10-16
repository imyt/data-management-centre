import * as React from "react"
import {
  createColumnHelper,
  createSortedRowModel,
  rowSelectionFeature,
  rowSortingFeature,
  sortFn_alphanumeric,
  sortFn_basic,
  sortFn_text,
  tableFeatures,
  useTable,
  type ColumnDef,
  type RowData,
  type RowSelectionState,
  type SortingState,
} from "@tanstack/react-table"
import { useVirtualizer } from "@tanstack/react-virtual"
import { ArrowDownIcon, ArrowUpDownIcon, ArrowUpIcon, InboxIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import { EmptyState, ErrorState } from "@/patterns/states"
import { Checkbox } from "@/ui/checkbox"
import { Skeleton } from "@/ui/skeleton"
import { TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/ui/table"

export interface DataTableColumnMeta {
  /** Numbers are right-aligned with tabular figures. */
  align?: "left" | "right"
  /** Record IDs and timestamps use the mono face. */
  mono?: boolean
}

export const dataTableFeatures = tableFeatures({
  rowSortingFeature,
  rowSelectionFeature,
  sortedRowModel: createSortedRowModel(),
  sortFns: { alphanumeric: sortFn_alphanumeric, text: sortFn_text, basic: sortFn_basic },
  columnMeta: {} as DataTableColumnMeta,
})

export type DataTableFeatures = typeof dataTableFeatures
export type DataTableColumn<TData extends RowData> = ColumnDef<DataTableFeatures, TData, any>
export const createDataTableColumns = <TData extends RowData>() => createColumnHelper<DataTableFeatures, TData>()

/** DESIGN.md: virtualise rows beyond 100. */
const VIRTUALIZE_AFTER = 100
const SKELETON_ROWS = 5

interface DataTableProps<TData extends RowData> {
  columns: DataTableColumn<TData>[]
  data: TData[]
  getRowId: (row: TData) => string
  /** Accessible name for the table, e.g. "Assets". */
  label: string
  loading?: boolean
  error?: { onRetry: () => void; retrying?: boolean }
  /** What an empty result means and the one next step. */
  empty?: { title: string; description?: string; action?: React.ReactNode }
  /** Row click opens the detail panel. Enter does the same, for keyboard parity. */
  onRowOpen?: (row: TData) => void
  /** Controlled sort, so the consumer can sync it to the URL. */
  sorting?: SortingState
  onSortingChange?: (sorting: SortingState) => void
  selectable?: boolean
  rowSelection?: RowSelectionState
  onRowSelectionChange?: (selection: RowSelectionState) => void
  /** Height cap for the scroll container (a Tailwind max-h-* class); the header sticks inside it. */
  scrollClassName?: string
  className?: string
}

export function DataTable<TData extends RowData>({
  columns,
  data,
  getRowId,
  label,
  loading = false,
  error,
  empty = { title: "Nothing here yet" },
  onRowOpen,
  sorting: sortingProp,
  onSortingChange,
  selectable = false,
  rowSelection: rowSelectionProp,
  onRowSelectionChange,
  scrollClassName = "max-h-128",
  className,
}: DataTableProps<TData>) {
  const [sortingState, setSortingState] = React.useState<SortingState>([])
  const [selectionState, setSelectionState] = React.useState<RowSelectionState>({})
  const sorting = sortingProp ?? sortingState
  const rowSelection = rowSelectionProp ?? selectionState

  const allColumns = React.useMemo<DataTableColumn<TData>[]>(
    () => (selectable ? [selectionColumn<TData>(), ...columns] : columns),
    [columns, selectable]
  )

  const table = useTable({
    features: dataTableFeatures,
    columns: allColumns,
    data,
    getRowId: (row) => getRowId(row),
    state: { sorting, rowSelection },
    onSortingChange: (updater) => {
      const next = typeof updater === "function" ? updater(sorting) : updater
      setSortingState(next)
      onSortingChange?.(next)
    },
    onRowSelectionChange: (updater) => {
      const next = typeof updater === "function" ? updater(rowSelection) : updater
      setSelectionState(next)
      onRowSelectionChange?.(next)
    },
    enableRowSelection: selectable,
  })

  const rows = table.getRowModel().rows
  const scrollRef = React.useRef<HTMLDivElement>(null)
  const virtualize = rows.length > VIRTUALIZE_AFTER
  const virtualizer = useVirtualizer({
    count: virtualize ? rows.length : 0,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => 40,
    overscan: 10,
  })
  const virtualRows = virtualize ? virtualizer.getVirtualItems() : []
  const visibleRows = virtualize ? virtualRows.map((item) => rows[item.index]) : rows
  const padTop = virtualize && virtualRows.length ? virtualRows[0].start : 0
  const padBottom =
    virtualize && virtualRows.length ? virtualizer.getTotalSize() - virtualRows[virtualRows.length - 1].end : 0
  const colCount = allColumns.length

  const showError = !loading && error
  const showEmpty = !loading && !error && rows.length === 0

  return (
    <div data-slot="data-table" className={cn("rounded-md bg-surface", className)}>
      {showError ? (
        <ErrorState onRetry={error.onRetry} retrying={error.retrying} />
      ) : showEmpty ? (
        <EmptyState icon={InboxIcon} title={empty.title} description={empty.description} action={empty.action} />
      ) : (
        <div ref={scrollRef} className={cn("relative w-full overflow-auto", scrollClassName)}>
          <table data-slot="table" aria-label={label} aria-busy={loading || undefined} className="w-full caption-bottom text-sm">
            <TableHeader>
              {table.getHeaderGroups().map((headerGroup) => (
                <TableRow key={headerGroup.id} className="hover:bg-transparent">
                  {headerGroup.headers.map((header) => {
                    const meta = header.column.columnDef.meta
                    const sorted = header.column.getIsSorted()
                    return (
                      <TableHead
                        key={header.id}
                        className={cn(meta?.align === "right" && "text-right")}
                        aria-sort={sorted === "asc" ? "ascending" : sorted === "desc" ? "descending" : header.column.getCanSort() ? "none" : undefined}
                      >
                        {header.isPlaceholder ? null : header.column.getCanSort() ? (
                          <button
                            type="button"
                            onClick={header.column.getToggleSortingHandler()}
                            className={cn(
                              "inline-flex cursor-pointer items-center gap-1 rounded-sm hover:text-foreground",
                              meta?.align === "right" && "flex-row-reverse"
                            )}
                          >
                            <table.FlexRender header={header} />
                            {sorted === "asc" ? (
                              <ArrowUpIcon className="size-3.5" aria-hidden="true" />
                            ) : sorted === "desc" ? (
                              <ArrowDownIcon className="size-3.5" aria-hidden="true" />
                            ) : (
                              <ArrowUpDownIcon className="size-3.5 text-text-tertiary" aria-hidden="true" />
                            )}
                          </button>
                        ) : (
                          <table.FlexRender header={header} />
                        )}
                      </TableHead>
                    )
                  })}
                </TableRow>
              ))}
            </TableHeader>
            <TableBody>
              {loading ? (
                Array.from({ length: SKELETON_ROWS }, (_, i) => (
                  <TableRow key={`skeleton-${i}`} className="hover:bg-transparent">
                    {Array.from({ length: colCount }, (_, j) => (
                      <TableCell key={j}>
                        <Skeleton className="h-4 w-full max-w-32" />
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              ) : (
                <>
                  {padTop > 0 && (
                    // Spacer heights are measured at runtime by the virtualiser, so they stay inline.
                    <tr aria-hidden="true">
                      <td colSpan={colCount} style={{ height: padTop }} />
                    </tr>
                  )}
                  {visibleRows.map((row) => (
                    <TableRow
                      key={row.id}
                      data-state={row.getIsSelected() ? "selected" : undefined}
                      tabIndex={onRowOpen ? 0 : undefined}
                      onClick={onRowOpen ? () => onRowOpen(row.original) : undefined}
                      onKeyDown={
                        onRowOpen
                          ? (event) => {
                              if (event.key === "Enter" && event.target === event.currentTarget) onRowOpen(row.original)
                            }
                          : undefined
                      }
                      className={cn(onRowOpen && "cursor-pointer")}
                    >
                      {row.getAllCells().map((cell) => {
                        const meta = cell.column.columnDef.meta
                        const value = cell.getValue()
                        // DESIGN.md: empty and null values show an em dash, never "null" or a blank cell.
                        const isEmpty = cell.column.accessorFn !== undefined && (value === null || value === undefined || value === "")
                        return (
                          <TableCell
                            key={cell.id}
                            className={cn(
                              meta?.align === "right" && "text-right tabular-nums",
                              meta?.mono && "mono",
                              isEmpty && "text-text-tertiary"
                            )}
                          >
                            {isEmpty ? "—" : <table.FlexRender cell={cell} />}
                          </TableCell>
                        )
                      })}
                    </TableRow>
                  ))}
                  {padBottom > 0 && (
                    <tr aria-hidden="true">
                      <td colSpan={colCount} style={{ height: padBottom }} />
                    </tr>
                  )}
                </>
              )}
            </TableBody>
          </table>
        </div>
      )}
    </div>
  )
}

function selectionColumn<TData extends RowData>(): DataTableColumn<TData> {
  return {
    id: "select",
    enableSorting: false,
    header: ({ table }) => (
      <Checkbox
        aria-label="Select all rows"
        checked={table.getIsAllRowsSelected() ? true : table.getIsSomeRowsSelected() ? "indeterminate" : false}
        onCheckedChange={(checked) => table.toggleAllRowsSelected(checked === true)}
      />
    ),
    cell: ({ row }) => (
      <Checkbox
        aria-label="Select row"
        checked={row.getIsSelected()}
        onCheckedChange={(checked) => row.toggleSelected(checked === true)}
        onClick={(event) => event.stopPropagation()}
      />
    ),
  }
}
