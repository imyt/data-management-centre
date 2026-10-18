import * as React from "react"
import { InfoIcon } from "lucide-react"
import { Link } from "react-router"

import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { formatTimestamp } from "@/lib/format"

export interface ExplainSource {
  label: string
  /** In-app route to the source: the asset, policy or rule. */
  to?: string
}

interface ExplainWhyProps {
  /** Plain-language reason, e.g. "Required because Customer orders is classified Confidential." */
  reason: React.ReactNode
  /** The facts the decision was derived from: assets, policies, rules. */
  sources?: ExplainSource[]
  evaluatedAt?: Date | string
  /** Custom trigger; defaults to a small "Why?" button. */
  children?: React.ReactNode
  label?: string
}

/** Every derived decision can say why and from what (DESIGN.md: Show why). */
export function ExplainWhy({ reason, sources = [], evaluatedAt, children, label = "Why?" }: ExplainWhyProps) {
  const at = evaluatedAt ? new Date(evaluatedAt) : null

  return (
    <Popover>
      <PopoverTrigger asChild>
        {children ?? (
          <button
            type="button"
            data-slot="explain-why"
            className="inline-flex cursor-pointer items-center gap-1 rounded-sm text-xs text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
          >
            <InfoIcon aria-hidden="true" className="size-3.5" />
            {label}
          </button>
        )}
      </PopoverTrigger>
      <PopoverContent align="start" className="w-80 text-sm">
        <p className="leading-relaxed">{reason}</p>

        {sources.length > 0 && (
          <div className="mt-3 border-t pt-3">
            <p className="text-xs font-medium text-muted-foreground">Based on</p>
            <ul className="mt-1 flex flex-col gap-1">
              {sources.map((s) => (
                <li key={s.label}>
                  {s.to ? (
                    <Link to={s.to} className="text-brand underline-offset-4 hover:underline">
                      {s.label}
                    </Link>
                  ) : (
                    s.label
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        {at && (
          <p className="mt-3 text-xs text-muted-foreground">
            Evaluated{" "}
            <time dateTime={at.toISOString()} title={at.toISOString()} className="mono tabular-nums">
              {formatTimestamp(at)}
            </time>
          </p>
        )}
      </PopoverContent>
    </Popover>
  )
}
