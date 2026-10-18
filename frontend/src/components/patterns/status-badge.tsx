import { CircleCheckIcon, CircleMinusIcon, CircleXIcon, Clock3Icon, ShieldAlertIcon, type LucideIcon } from "lucide-react"

import { cn } from "@/lib/utils"

const STATUS = {
  passing: { label: "Passing", icon: CircleCheckIcon, className: "bg-status-passing-bg text-status-passing" },
  failing: { label: "Failing", icon: CircleXIcon, className: "bg-status-failing-bg text-status-failing" },
  excepted: { label: "Excepted", icon: ShieldAlertIcon, className: "bg-status-excepted-bg text-status-excepted" },
  pending: { label: "Pending", icon: Clock3Icon, className: "bg-status-pending-bg text-status-pending" },
  not_applicable: {
    label: "Not applicable",
    icon: CircleMinusIcon,
    className: "bg-status-not-applicable-bg text-status-not-applicable",
  },
} as const satisfies Record<string, { label: string; icon: LucideIcon; className: string }>

export type Status = keyof typeof STATUS
export const STATUSES = Object.keys(STATUS) as Status[]

interface StatusBadgeProps {
  status: Status
  /** Override the default word only when the context truly needs it. */
  label?: string
  size?: "sm" | "default"
  className?: string
}

/** The one status language: same colour, icon and word everywhere. Never colour alone, never the accent. */
export function StatusBadge({ status, label, size = "default", className }: StatusBadgeProps) {
  const { label: defaultLabel, icon: Icon, className: tone } = STATUS[status]
  return (
    <span
      data-slot="status-badge"
      data-status={status}
      className={cn(
        "inline-flex w-fit shrink-0 items-center gap-1 rounded-full text-xs font-medium whitespace-nowrap",
        size === "sm" ? "h-5 px-1.5" : "h-6 px-2",
        tone,
        className
      )}
    >
      <Icon aria-hidden="true" className={size === "sm" ? "size-3" : "size-3.5"} />
      {label ?? defaultLabel}
    </span>
  )
}
