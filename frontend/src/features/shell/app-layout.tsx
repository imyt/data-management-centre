import * as React from "react"
import {
  AppWindowIcon,
  DatabaseIcon,
  InboxIcon,
  LayoutDashboardIcon,
  ShieldCheckIcon,
  type LucideIcon,
} from "lucide-react"
import { Outlet, useLocation } from "react-router"

import {
  AppShell,
  PortalHeader,
  UpdateBanner,
  type NavGroup,
  type ScopeOption,
  type Section,
} from "@/components/patterns"

import { usePairing } from "./use-pairing"

const SECTION_ROUTES: Record<Section, string> = {
  inbox: "/",
  assets: "/assets",
  applications: "/applications",
  controls: "/controls",
  reports: "/reports",
}

// Pages within each section. One per section until the slices that add the rest (PRD.md §5).
const SECTION_PAGES: Record<Section, { label: string; icon: LucideIcon }> = {
  inbox: { label: "Waiting on me", icon: InboxIcon },
  assets: { label: "All assets", icon: DatabaseIcon },
  applications: { label: "All applications", icon: AppWindowIcon },
  controls: { label: "Applied controls", icon: ShieldCheckIcon },
  reports: { label: "Posture", icon: LayoutDashboardIcon },
}

// Domains come with the identity module (roadmap 0.7); until then the only scope is everything.
const SCOPES: ScopeOption[] = [{ id: "all", label: "All domains" }]

function sectionFor(pathname: string): Section {
  const first = pathname.split("/")[1]
  const match = (Object.keys(SECTION_ROUTES) as Section[]).find((s) => s !== "inbox" && s === first)
  return match ?? "inbox"
}

/** The portal frame for every section screen: header with the five sections, the section's sidebar, the screen. */
export function AppLayout() {
  const { pathname } = useLocation()
  const section = sectionFor(pathname)
  const [scope, setScope] = React.useState(SCOPES[0].id)
  const pairing = usePairing()

  const page = SECTION_PAGES[section]
  const nav: NavGroup[] = [{ items: [{ label: page.label, to: SECTION_ROUTES[section], icon: page.icon }] }]

  return (
    <AppShell
      header={
        <>
          {pairing.outdated && <UpdateBanner />}
          <PortalHeader
            sectionRoutes={SECTION_ROUTES}
            inboxCount={0}
            scopes={SCOPES}
            scope={scope}
            onScopeChange={setScope}
            posture={null}
            postureTo={SECTION_ROUTES.reports}
            environment={pairing.environmentBadge}
          />
        </>
      }
      nav={nav}
    >
      <Outlet />
    </AppShell>
  )
}
