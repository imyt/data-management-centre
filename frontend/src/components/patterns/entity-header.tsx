import * as React from "react"

import { StatusBadge, type Status } from "@/components/patterns/status-badge"
import { cn } from "@/lib/utils"

export interface EntityMeta {
  label: string
  value: React.ReactNode
}

interface EntityHeaderProps {
  /** What this is: "Asset", "Application", "Applied control". */
  kind: string
  title: string
  /** Stable ID shown in mono, e.g. "AST-10482". */
  identifier?: string
  status?: Status
  /** Usually an <ExplainWhy /> for the status. */
  explain?: React.ReactNode
  meta?: EntityMeta[]
  /** Primary action last, so it sits rightmost. */
  actions?: React.ReactNode
  className?: string
}

/** Same summary shape for every entity, in pages and in sheets. */
export function EntityHeader({ kind, title, identifier, status, explain, meta = [], actions, className }: EntityHeaderProps) {
  return (
    <header data-slot="entity-header" className={cn("flex flex-col gap-4", className)}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 flex-col gap-1">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>{kind}</span>
            {identifier && <span className="mono tabular-nums">{identifier}</span>}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="truncate text-lg font-semibold tracking-tight">{title}</h2>
            {status && <StatusBadge status={status} />}
            {explain}
          </div>
        </div>
        {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
      </div>

      {meta.length > 0 && (
        <dl className="flex flex-wrap gap-x-6 gap-y-3">
          {meta.map((m) => (
            <div key={m.label} className="w-36 min-w-0">
              <dt className="text-xs text-muted-foreground">{m.label}</dt>
              <dd className="truncate text-sm">{m.value}</dd>
            </div>
          ))}
        </dl>
      )}
    </header>
  )
}
