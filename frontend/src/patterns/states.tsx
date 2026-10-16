import * as React from "react"
import { CircleXIcon, LockIcon, type LucideIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/ui/button"

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  /** One short sentence: what happened and what to do next. */
  description?: string
  /** The one clear next step. */
  action?: React.ReactNode
  className?: string
}

/** Calm, centred, one next step. No artwork (DESIGN.md: empty, loading, error states). */
export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      data-slot="empty-state"
      className={cn("flex flex-col items-center gap-2 px-6 py-12 text-center", className)}
    >
      <Icon className="size-5 text-text-tertiary" aria-hidden="true" />
      <p className="text-lg leading-tight font-semibold tracking-tight text-foreground">{title}</p>
      {description && <p className="max-w-sm text-sm text-muted-foreground">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}

interface ErrorStateProps {
  title?: string
  description?: string
  onRetry: () => void
  retrying?: boolean
  className?: string
}

/** Error with retry. Plain language, no blame, no raw error text. */
export function ErrorState({
  title = "Couldn't load this",
  description = "Check your connection and try again.",
  onRetry,
  retrying = false,
  className,
}: ErrorStateProps) {
  return (
    <div role="alert" className={className}>
      <EmptyState
        icon={CircleXIcon}
        title={title}
        description={description}
        action={
          <Button variant="secondary" onClick={onRetry} loading={retrying}>
            Try again
          </Button>
        }
      />
    </div>
  )
}

interface NoAccessStateProps {
  /** Who can grant access, e.g. "the domain owner, David Vance". */
  askWho: string
  className?: string
}

/** DESIGN.md: a calm "You don't have access" state with who to ask, never a blank page. */
export function NoAccessState({ askWho, className }: NoAccessStateProps) {
  return (
    <EmptyState
      icon={LockIcon}
      title="You don't have access"
      description={`Ask ${askWho} to give you access.`}
      className={className}
    />
  )
}
