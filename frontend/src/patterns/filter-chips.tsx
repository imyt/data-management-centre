import { XIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/ui/button"

export interface ActiveFilter {
  id: string
  /** Facet name, e.g. "Domain". */
  facet: string
  /** Display value, e.g. "Finance". */
  value: string
}

interface FilterChipsProps {
  filters: ActiveFilter[]
  onRemove: (id: string) => void
  onClearAll: () => void
  className?: string
}

/**
 * Faceted filters as removable chips (DESIGN.md: Finding). The consumer owns filter state
 * and syncs it to the URL; this only renders it.
 */
export function FilterChips({ filters, onRemove, onClearAll, className }: FilterChipsProps) {
  if (filters.length === 0) return null
  return (
    <div role="group" aria-label="Active filters" className={cn("flex flex-wrap items-center gap-2", className)}>
      {filters.map((filter) => (
        <span
          key={filter.id}
          data-slot="filter-chip"
          className="inline-flex h-8 items-center gap-1 rounded-sm border border-input bg-surface pr-1 pl-2 text-sm text-foreground"
        >
          <span className="text-muted-foreground">{filter.facet}:</span>
          {filter.value}
          <button
            type="button"
            onClick={() => onRemove(filter.id)}
            aria-label={`Remove ${filter.facet} filter`}
            className="inline-flex size-6 cursor-pointer items-center justify-center rounded-sm text-muted-foreground transition-colors duration-fast hover:bg-subtle hover:text-foreground"
          >
            <XIcon className="size-3.5" aria-hidden="true" />
          </button>
        </span>
      ))}
      <Button variant="ghost" onClick={onClearAll}>
        Clear all
      </Button>
    </div>
  )
}
