import { CheckIcon } from "lucide-react"

import { cn } from "@/lib/utils"

interface StageStepperProps {
  /** Ordered stage labels, from workflow configuration (never hard-coded per workflow). */
  stages: string[]
  /** Index of the current stage. */
  current: number
  className?: string
}

/** Stage indicator for linear workflow records (DESIGN.md: Workflow patterns, State and stage). */
export function StageStepper({ stages, current, className }: StageStepperProps) {
  return (
    <ol aria-label="Stage" className={cn("flex items-center gap-2 text-sm", className)}>
      {stages.map((stage, index) => {
        const state = index < current ? "done" : index === current ? "current" : "upcoming"
        return (
          <li key={stage} className="flex items-center gap-2" aria-current={state === "current" ? "step" : undefined}>
            {index > 0 && <span aria-hidden="true" className="h-px w-6 bg-border" />}
            <span
              aria-hidden="true"
              className={cn(
                "inline-flex size-5 items-center justify-center rounded-full border text-xs tabular-nums",
                state === "done" && "border-subtle bg-subtle text-foreground",
                state === "current" && "border-primary bg-primary text-primary-foreground",
                state === "upcoming" && "border-input text-muted-foreground"
              )}
            >
              {state === "done" ? <CheckIcon className="size-3" /> : index + 1}
            </span>
            <span
              className={cn(
                state === "current" ? "font-medium text-foreground" : "text-muted-foreground",
                state === "done" && "text-foreground"
              )}
            >
              {stage}
              {state === "done" && <span className="sr-only"> (completed)</span>}
            </span>
          </li>
        )
      })}
    </ol>
  )
}
