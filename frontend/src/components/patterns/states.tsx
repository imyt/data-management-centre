import * as React from "react"
import { CircleXIcon, FileQuestionIcon, InboxIcon, LockIcon, type LucideIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  /** One short sentence: what happened and what to do next. */
  description?: React.ReactNode
  /** The one clear next step. */
  action?: React.ReactNode
  className?: string
}

/** Calm, centred, one next step. No artwork (DESIGN.md: every state designed). */
export function EmptyState({ icon: Icon = InboxIcon, title, description, action, className }: EmptyStateProps) {
  return (
    <div data-slot="empty-state" className={cn("flex flex-col items-center gap-2 px-6 py-12 text-center", className)}>
      <Icon className="size-5 text-text-tertiary" aria-hidden="true" />
      <p className="text-lg leading-tight font-semibold tracking-tight text-foreground">{title}</p>
      {description && <p className="max-w-sm text-sm text-muted-foreground">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}

interface ErrorStateProps {
  title?: string
  description?: React.ReactNode
  onRetry?: () => void
  retrying?: boolean
  className?: string
}

/** Says what happened and what to do next. No blame, no raw error text. */
export function ErrorState({
  title = "This didn’t load",
  description = "Check your connection, then try again. If it keeps failing, the service may be down.",
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
          onRetry && (
            <Button variant="secondary" onClick={onRetry} loading={retrying}>
              Try again
            </Button>
          )
        }
      />
    </div>
  )
}

interface NoAccessStateProps {
  /** What access is needed, e.g. "the Data Owner role for this asset". */
  requirement?: string
  /** Who can grant it, e.g. "the domain owner, David Vance,". */
  askWho?: string
  action?: React.ReactNode
  className?: string
}

/** A calm "You don’t have access" with what is needed and who to ask, never a blank page. */
export function NoAccessState({ requirement, askWho = "the owner or a DMC admin", action, className }: NoAccessStateProps) {
  const ask = `Ask ${askWho} for access.`
  return (
    <EmptyState
      icon={LockIcon}
      title="You don’t have access"
      description={requirement ? `This needs ${requirement}. ${ask}` : ask}
      action={action}
      className={className}
    />
  )
}

interface NotFoundStateProps {
  /** What was looked for, e.g. "asset". */
  kind?: string
  action?: React.ReactNode
  className?: string
}

export function NotFoundState({ kind = "item", action, className }: NotFoundStateProps) {
  return (
    <EmptyState
      icon={FileQuestionIcon}
      title={`This ${kind} doesn’t exist`}
      description="It may have been deleted, or the link is wrong."
      action={action}
      className={className}
    />
  )
}

interface LoadingStateProps {
  rows?: number
  /** Announced to screen readers. */
  label?: string
  className?: string
}

/** Skeleton shaped like what is coming, not a spinner. */
export function LoadingState({ rows = 4, label = "Loading", className }: LoadingStateProps) {
  return (
    <div role="status" data-slot="loading-state" className={cn("flex flex-col gap-3 p-6", className)}>
      <span className="sr-only">{label}</span>
      <Skeleton className="h-5 w-1/3" />
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} className={cn("h-4", i % 3 === 2 ? "w-2/3" : "w-full")} />
      ))}
    </div>
  )
}
