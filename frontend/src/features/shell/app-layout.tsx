import * as React from "react"
import { useQuery } from "@tanstack/react-query"
import {
  AppWindowIcon,
  DatabaseIcon,
  InboxIcon,
  LayoutDashboardIcon,
  ShieldCheckIcon,
  type LucideIcon,
} from "lucide-react"
import { Outlet, useLocation } from "react-router"

import { listDomainsOptions, listInboxOptions } from "@/api/@tanstack/react-query.gen"
import {
  AccountMenu,
  AppShell,
  PortalHeader,
  UpdateBanner,
  type NavGroup,
  type ScopeOption,
  type Section,
} from "@/components/patterns"
import { ALL_DOMAINS, type ShellContext } from "@/features/shell/scope"

import { useIdentity } from "./use-identity"
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

const ALL_SCOPE: ScopeOption = { id: ALL_DOMAINS, label: "All domains" }

function sectionFor(pathname: string): Section {
  const first = pathname.split("/")[1]
  const match = (Object.keys(SECTION_ROUTES) as Section[]).find((s) => s !== "inbox" && s === first)
  return match ?? "inbox"
}

/** The portal frame for every section screen: header with the five sections, the section's sidebar, the screen. */
export function AppLayout() {
  const { pathname } = useLocation()
  const section = sectionFor(pathname)
  const [scope, setScope] = React.useState(ALL_DOMAINS)
  const pairing = usePairing()
  const identity = useIdentity()
  // Scope options are the domains from reference data (FR-D2). Until they load, only "All domains".
  const domains = useQuery(listDomainsOptions())
  const scopes = React.useMemo<ScopeOption[]>(
    () => [ALL_SCOPE, ...(domains.data?.data ?? []).map((d) => ({ id: d.id, label: d.name }))],
    [domains.data]
  )
  const inbox = useQuery(listInboxOptions())
  const context: ShellContext = { domainId: scope === ALL_DOMAINS ? null : scope }

  const page = SECTION_PAGES[section]
  const nav: NavGroup[] = [{ items: [{ label: page.label, to: SECTION_ROUTES[section], icon: page.icon }] }]

  return (
    <AppShell
      header={
        <>
          {pairing.outdated && <UpdateBanner />}
          <PortalHeader
            sectionRoutes={SECTION_ROUTES}
            inboxCount={inbox.data?.meta.total ?? 0}
            scopes={scopes}
            scope={scope}
            onScopeChange={setScope}
            posture={null}
            postureTo={SECTION_ROUTES.reports}
            environment={pairing.environmentBadge}
            userMenu={<AccountMenu {...identity} />}
          />
        </>
      }
      nav={nav}
    >
      <Outlet context={context} />
    </AppShell>
  )
}
