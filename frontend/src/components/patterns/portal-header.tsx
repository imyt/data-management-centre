import * as React from "react"
import { ChevronDownIcon, Clock3Icon, SearchIcon } from "lucide-react"
import { Link, NavLink } from "react-router"

import { DmcMark } from "@/components/patterns/dmc-mark"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Skeleton } from "@/components/ui/skeleton"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { formatRelative, formatTimestamp } from "@/lib/format"
import { cn } from "@/lib/utils"

function useNow(intervalMs = 60_000) {
  const [now, setNow] = React.useState(() => Date.now())
  React.useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), intervalMs)
    return () => window.clearInterval(timer)
  }, [intervalMs])
  return now
}

/* ---------- global navigation ---------- */

export type Section = "inbox" | "assets" | "applications" | "controls" | "reports"

export const SECTIONS: { id: Section; label: string }[] = [
  { id: "inbox", label: "Inbox" },
  { id: "assets", label: "Assets" },
  { id: "applications", label: "Applications" },
  { id: "controls", label: "Controls" },
  { id: "reports", label: "Reports" },
]

interface GlobalNavProps {
  routes: Record<Section, string>
  /** Items waiting on the user. */
  inboxCount?: number
}

/** The five sections. The active one follows the route. */
export function GlobalNav({ routes, inboxCount = 0 }: GlobalNavProps) {
  return (
    <nav aria-label="Main" className="flex items-stretch">
      {SECTIONS.map((s) => {
        const showCount = s.id === "inbox" && inboxCount > 0
        return (
          <NavLink
            key={s.id}
            to={routes[s.id]}
            aria-label={showCount ? `Inbox, ${inboxCount} need you` : undefined}
            className={({ isActive }) =>
              cn(
                "relative flex items-center gap-1 px-3 text-sm transition-colors duration-fast",
                isActive ? "font-medium text-foreground" : "text-muted-foreground hover:text-foreground"
              )
            }
          >
            {({ isActive }) => (
              <>
                {s.label}
                {showCount && (
                  <span className="mono flex h-4.5 min-w-4.5 items-center justify-center rounded-full bg-primary px-1.5 text-xs text-primary-foreground tabular-nums">
                    {inboxCount > 99 ? "99+" : inboxCount}
                  </span>
                )}
                {isActive && <span aria-hidden="true" className="absolute inset-x-3 bottom-0 h-0.5 bg-primary" />}
              </>
            )}
          </NavLink>
        )
      })}
    </nav>
  )
}

/* ---------- posture readout ---------- */

export interface Posture {
  /** 0 to 100, share of applied controls passing in the current scope. */
  passingPercent: number
  evaluatedAt: Date | string
}

interface PostureReadoutProps {
  posture?: Posture | null
  loading?: boolean
  to: string
  /** Older than this and the readout says so (DESIGN.md: Freshness is visible). */
  staleAfterMinutes?: number
}

export function PostureReadout({ posture, loading, to, staleAfterMinutes = 60 }: PostureReadoutProps) {
  const now = useNow()

  if (loading) {
    return (
      <span role="status" className="flex items-center">
        <span className="sr-only">Loading posture</span>
        <Skeleton className="h-5 w-24" />
      </span>
    )
  }

  if (!posture) {
    return (
      <Link to={to} className="rounded-sm px-1 text-sm text-muted-foreground underline-offset-4 hover:underline">
        No posture yet
      </Link>
    )
  }

  const at = new Date(posture.evaluatedAt)
  const stale = now - at.getTime() > staleAfterMinutes * 60_000
  const pct = Math.round(posture.passingPercent)
  const when = formatRelative(at, now)

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Link
          to={to}
          aria-label={`Control posture: ${pct}% passing, evaluated ${when}${stale ? ", may be out of date" : ""}`}
          className="flex items-center gap-1 rounded-sm px-1 text-sm hover:text-foreground"
        >
          <span className="mono tabular-nums">{pct}%</span>
          <span className="hidden text-muted-foreground xl:inline">passing</span>
          {stale && (
            <span className="flex items-center gap-1 text-xs text-status-excepted">
              <Clock3Icon aria-hidden="true" className="size-3.5" />
              <span className="hidden 2xl:inline">Out of date</span>
            </span>
          )}
        </Link>
      </TooltipTrigger>
      <TooltipContent>
        Evaluated {when}
        <time dateTime={at.toISOString()} className="mono block tabular-nums">
          {formatTimestamp(at)}
        </time>
      </TooltipContent>
    </Tooltip>
  )
}

/* ---------- scope switcher ---------- */

export interface ScopeOption {
  id: string
  label: string
}

interface ScopeSwitcherProps {
  options: ScopeOption[]
  value: string
  onChange: (id: string) => void
}

/** Everything on screen is filtered to this scope; say so, and let people change it. */
export function ScopeSwitcher({ options, value, onChange }: ScopeSwitcherProps) {
  const current = options.find((o) => o.id === value) ?? options[0]
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" aria-label={`Scope: ${current?.label}. Change scope`}>
          <span className="max-w-36 truncate">{current?.label}</span>
          <ChevronDownIcon aria-hidden="true" className="size-3.5 text-muted-foreground" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>Show data for</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuRadioGroup value={value} onValueChange={onChange}>
          {options.map((o) => (
            <DropdownMenuRadioItem key={o.id} value={o.id}>
              {o.label}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

/* ---------- header ---------- */

interface PortalHeaderProps {
  homeTo?: string
  sectionRoutes: Record<Section, string>
  inboxCount: number
  /** Opens the command palette; also bound to ⌘K / Ctrl+K. */
  onOpenCommand?: () => void
  scopes: ScopeOption[]
  scope: string
  onScopeChange: (id: string) => void
  posture?: Posture | null
  postureLoading?: boolean
  postureTo: string
  /** Avatar and account menu. */
  userMenu?: React.ReactNode
}

/** Mark and full name, sections, search, scope, posture, account. The hairline accent rule sits under it. */
export function PortalHeader({
  homeTo = "/",
  sectionRoutes,
  inboxCount,
  onOpenCommand,
  scopes,
  scope,
  onScopeChange,
  posture,
  postureLoading,
  postureTo,
  userMenu,
}: PortalHeaderProps) {
  React.useEffect(() => {
    if (!onOpenCommand) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key.toLowerCase() === "k" && (event.metaKey || event.ctrlKey)) {
        event.preventDefault()
        onOpenCommand()
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [onOpenCommand])

  return (
    <header
      data-slot="portal-header"
      className="z-nav flex h-14 shrink-0 items-stretch gap-4 border-b border-primary bg-surface px-4 xl:gap-7"
    >
      <Link to={homeTo} className="flex items-center gap-2 rounded-sm">
        <DmcMark size={22} title="" />
        <span className="text-base font-semibold tracking-tight whitespace-nowrap">Data Management Centre</span>
      </Link>

      <GlobalNav routes={sectionRoutes} inboxCount={inboxCount} />

      <div className="flex flex-1 items-center justify-end">
        {onOpenCommand && (
          <>
            <button
              type="button"
              onClick={onOpenCommand}
              className="hidden h-(--control-height) w-full max-w-xs cursor-pointer items-center gap-2 rounded-sm border border-input bg-surface px-3 text-sm text-muted-foreground transition-colors duration-fast hover:bg-subtle 2xl:flex"
            >
              <SearchIcon aria-hidden="true" className="size-4" />
              <span className="flex-1 text-left">Search or jump to…</span>
              <kbd className="mono rounded-sm bg-subtle px-1.5 text-xs">⌘K</kbd>
            </button>
            <Button variant="ghost" size="icon" onClick={onOpenCommand} aria-label="Search (⌘K)" className="2xl:hidden">
              <SearchIcon aria-hidden="true" />
            </Button>
          </>
        )}
      </div>

      <div className="flex items-center gap-3">
        <ScopeSwitcher options={scopes} value={scope} onChange={onScopeChange} />
        <PostureReadout posture={posture} loading={postureLoading} to={postureTo} />
        {userMenu}
      </div>
    </header>
  )
}
