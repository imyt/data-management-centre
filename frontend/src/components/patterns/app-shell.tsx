import * as React from "react"
import { PanelLeftCloseIcon, PanelLeftOpenIcon, type LucideIcon } from "lucide-react"
import { NavLink } from "react-router"

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { useMediaQuery } from "@/hooks/use-media-query"
import { cn } from "@/lib/utils"

export interface NavItem {
  label: string
  to: string
  icon: LucideIcon
  /** Count of items needing the user. */
  badge?: number
}

export interface NavGroup {
  label?: string
  items: NavItem[]
}

interface AppShellProps {
  /** Usually <PortalHeader />; spans the full width above the sidebar. */
  header: React.ReactNode
  /** Pages within the current section. The section itself lives in the header. */
  nav: NavGroup[]
  children: React.ReactNode
}

const STORAGE_KEY = "dmc-sidebar-collapsed"

function readCollapsed(): boolean | null {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    return value === null ? null : value === "1"
  } catch {
    return null
  }
}

/** Header, section sidebar and main. The sidebar collapses to icons below 1280px and remembers the user's choice. */
export function AppShell({ header, nav, children }: AppShellProps) {
  const roomy = useMediaQuery("(min-width: 1280px)")
  const [userChoice, setUserChoice] = React.useState<boolean | null>(readCollapsed)
  const collapsed = userChoice ?? !roomy

  function toggle() {
    const next = !collapsed
    setUserChoice(next)
    try {
      localStorage.setItem(STORAGE_KEY, next ? "1" : "0")
    } catch {
      // Storage can be unavailable (private mode); the choice then lasts for the session only.
    }
  }

  const ToggleIcon = collapsed ? PanelLeftOpenIcon : PanelLeftCloseIcon

  return (
    <div data-slot="app-shell" className="flex h-dvh flex-col overflow-hidden bg-background text-foreground">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:top-3 focus:left-3 focus:z-toast focus:rounded-sm focus:bg-surface focus:px-3 focus:py-2"
      >
        Skip to content
      </a>

      {header}

      <div className="flex min-h-0 flex-1">
        <aside
          className={cn(
            "flex shrink-0 flex-col border-r bg-subtle",
            collapsed ? "w-14" : "w-60"
          )}
        >
          <nav aria-label="Section" className="flex flex-1 flex-col gap-5 overflow-y-auto px-2 py-4">
            {nav.map((group, gi) => (
              <div key={group.label ?? gi} className="flex flex-col gap-0.5">
                {group.label && !collapsed && (
                  <p className="px-2 pb-1 text-xs font-medium text-muted-foreground">{group.label}</p>
                )}
                {group.items.map((item) => {
                  const Icon = item.icon
                  const link = (
                    <NavLink
                      to={item.to}
                      end
                      className={({ isActive }) =>
                        cn(
                          "group flex h-8 items-center gap-2 rounded-sm px-2 text-sm text-muted-foreground transition-colors duration-fast hover:bg-surface hover:text-foreground",
                          isActive && "bg-surface font-medium text-foreground",
                          collapsed && "justify-center px-0"
                        )
                      }
                    >
                      <Icon aria-hidden="true" className="size-4 shrink-0 group-aria-[current=page]:text-brand" />
                      {collapsed ? (
                        <span className="sr-only">{item.label}</span>
                      ) : (
                        <>
                          <span className="truncate">{item.label}</span>
                          {!!item.badge && <span className="mono ml-auto tabular-nums">{item.badge}</span>}
                        </>
                      )}
                    </NavLink>
                  )
                  return collapsed ? (
                    <Tooltip key={item.to}>
                      <TooltipTrigger asChild>{link}</TooltipTrigger>
                      <TooltipContent side="right">
                        {item.label}
                        {!!item.badge && ` (${item.badge})`}
                      </TooltipContent>
                    </Tooltip>
                  ) : (
                    <React.Fragment key={item.to}>{link}</React.Fragment>
                  )
                })}
              </div>
            ))}
          </nav>

          <div className={cn("border-t p-2", collapsed && "flex justify-center")}>
            <button
              type="button"
              onClick={toggle}
              aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
              aria-expanded={!collapsed}
              className="flex h-8 cursor-pointer items-center gap-2 rounded-sm px-2 text-sm text-muted-foreground transition-colors duration-fast hover:bg-surface hover:text-foreground"
            >
              <ToggleIcon aria-hidden="true" className="size-4" />
              {!collapsed && <span>Collapse</span>}
            </button>
          </div>
        </aside>

        <main id="main" tabIndex={-1} className="min-h-0 flex-1 overflow-auto focus-visible:outline-none">
          {children}
        </main>
      </div>
    </div>
  )
}
