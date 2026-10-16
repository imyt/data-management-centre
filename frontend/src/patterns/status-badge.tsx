import { CircleCheckIcon, CircleDashedIcon, CircleXIcon, TriangleAlertIcon, type LucideIcon } from "lucide-react"

import { Badge } from "@/ui/badge"

export type Status = "success" | "warning" | "danger" | "neutral"

const statusIcon: Record<Status, LucideIcon> = {
  success: CircleCheckIcon,
  warning: TriangleAlertIcon,
  danger: CircleXIcon,
  neutral: CircleDashedIcon,
}

const statusVariant = {
  success: "success",
  warning: "warning",
  danger: "destructive",
  neutral: "secondary",
} as const

interface StatusBadgeProps {
  status: Status
  /** Sentence-case label. Required: status is never colour alone. */
  label: string
  className?: string
}

/** A record state as a subtle tint plus icon plus label (DESIGN.md: never colour alone, never the accent). */
export function StatusBadge({ status, label, className }: StatusBadgeProps) {
  const Icon = statusIcon[status]
  return (
    <Badge variant={statusVariant[status]} className={className} data-status={status}>
      <Icon aria-hidden="true" />
      {label}
    </Badge>
  )
}
