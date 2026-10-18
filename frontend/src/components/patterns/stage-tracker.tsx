import * as React from "react"
import { CircleCheckIcon, CircleXIcon, Clock3Icon } from "lucide-react"

import { DmcMark, STAGES, type Stage } from "@/components/patterns/dmc-mark"
import { cn } from "@/lib/utils"

export type StageTone = "complete" | "attention" | "progress"

export interface StageState {
  /** Short status, e.g. "3 controls failing". */
  summary: string
  tone: StageTone
}

const TONE = {
  complete: { icon: CircleCheckIcon, className: "text-status-passing" },
  attention: { icon: CircleXIcon, className: "text-status-failing" },
  progress: { icon: Clock3Icon, className: "text-status-pending" },
} as const

interface StageTrackerProps {
  /** Name of the entity, for the accessible label. */
  entityName: string
  states: Record<Stage, StageState>
  selected: Stage
  onSelect: (stage: Stage) => void
  /** id of the panel element the tabs control. */
  panelId: string
  className?: string
}

/** Where one asset or application is in Know, Assess, Act, Assure. Tabs over the stage panels. */
export function StageTracker({ entityName, states, selected, onSelect, panelId, className }: StageTrackerProps) {
  const refs = React.useRef<(HTMLButtonElement | null)[]>([])
  const complete = STAGES.filter((s) => states[s.id].tone === "complete").map((s) => s.id)

  function onKeyDown(event: React.KeyboardEvent, index: number) {
    const last = STAGES.length - 1
    const next =
      event.key === "ArrowRight"
        ? index === last ? 0 : index + 1
        : event.key === "ArrowLeft"
          ? index === 0 ? last : index - 1
          : event.key === "Home"
            ? 0
            : event.key === "End"
              ? last
              : null
    if (next === null) return
    event.preventDefault()
    onSelect(STAGES[next].id)
    refs.current[next]?.focus()
  }

  return (
    <div data-slot="stage-tracker" className={cn("flex items-stretch gap-4", className)}>
      <div className="flex items-center px-2">
        <DmcMark size={40} lit={complete} title={`${entityName}: ${complete.length} of 4 stages complete`} />
      </div>

      <div role="tablist" aria-label={`Stages for ${entityName}`} className="grid flex-1 grid-cols-4 gap-2">
        {STAGES.map((stage, i) => {
          const state = states[stage.id]
          const { icon: Icon, className: tone } = TONE[state.tone]
          const isSelected = stage.id === selected
          return (
            <button
              key={stage.id}
              ref={(el) => {
                refs.current[i] = el
              }}
              type="button"
              role="tab"
              id={`${panelId}-tab-${stage.id}`}
              aria-selected={isSelected}
              aria-controls={panelId}
              tabIndex={isSelected ? 0 : -1}
              onClick={() => onSelect(stage.id)}
              onKeyDown={(event) => onKeyDown(event, i)}
              className={cn(
                "flex cursor-pointer flex-col gap-1 rounded-b-md border-t-2 px-4 py-3 text-left transition-colors duration-fast",
                isSelected ? "border-primary bg-surface" : "border-transparent bg-subtle hover:bg-surface"
              )}
            >
              <span className="text-sm font-semibold text-foreground">{stage.label}</span>
              <span className={cn("flex items-center gap-1 text-sm", tone)}>
                <Icon aria-hidden="true" className="size-3.5 shrink-0" />
                <span className="truncate">{state.summary}</span>
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

/** id of a StageTracker tab, for the panel's aria-labelledby. */
export function stageTabId(panelId: string, stage: Stage) {
  return `${panelId}-tab-${stage}`
}
