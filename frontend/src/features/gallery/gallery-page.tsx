import * as React from "react"
import { LayoutGridIcon, MoonIcon, SunIcon } from "lucide-react"

import { AppShell, PortalHeader, type NavGroup } from "@/components/patterns"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { accountMenuEntry, patternEntries } from "@/features/gallery/entries/pattern-entries"
import { uiEntries } from "@/features/gallery/entries/ui-entries"
import { Specimen, type GalleryEntry } from "@/features/gallery/specimen"
import { useTheme } from "@/lib/theme"

// Sections are fractional pixels tall (text line heights), so inserting one, or a contents link that
// wraps, moves every later section to a new sub-pixel offset and churns its screenshot. Until the
// line heights are whole pixels, new entries go last and stay out of the contents row.
export const galleryEntries: GalleryEntry[] = [...patternEntries, ...uiEntries, accountMenuEntry]

const NAV: NavGroup[] = [{ label: "Design system", items: [{ label: "Gallery", to: "/gallery", icon: LayoutGridIcon }] }]

const SECTION_ROUTES = {
  inbox: "/",
  assets: "/assets",
  applications: "/applications",
  controls: "/controls",
  reports: "/reports",
} as const

const SCOPES = [
  { id: "all", label: "All domains" },
  { id: "finance", label: "Finance" },
  { id: "customer", label: "Customer" },
]

function GalleryHeader() {
  const [scope, setScope] = React.useState("all")
  const [evaluatedAt] = React.useState(() => new Date(Date.now() - 4 * 60_000))
  return (
    <PortalHeader
      homeTo="/gallery"
      sectionRoutes={SECTION_ROUTES}
      inboxCount={7}
      onOpenCommand={() => undefined}
      scopes={SCOPES}
      scope={scope}
      onScopeChange={setScope}
      posture={{ passingPercent: 92, evaluatedAt }}
      postureTo="/reports"
    />
  )
}

function Contents({ title, entries }: { title: string; entries: GalleryEntry[] }) {
  return (
    <div className="flex flex-col gap-1">
      <p className="mono text-text-tertiary">{title}</p>
      <ul className="flex flex-wrap gap-x-1">
        {entries.map((entry) => (
          <li key={entry.id}>
            <a
              href={`#${entry.id}`}
              className="block rounded-sm px-2 py-1 text-sm text-muted-foreground transition-colors duration-fast hover:bg-subtle hover:text-foreground"
            >
              {entry.name}
            </a>
          </li>
        ))}
      </ul>
    </div>
  )
}

/** /gallery: every pattern and ui primitive in every state, in light and dark. The visual test target. */
export function GalleryPage() {
  const { theme, setTheme, density, setDensity } = useTheme()

  // cmdk scrolls its first item into view on mount, which drags the gallery down. Start at the
  // top, or at the linked section when the URL has a hash.
  React.useEffect(() => {
    const frame = requestAnimationFrame(() => {
      const target = window.location.hash ? document.getElementById(window.location.hash.slice(1)) : null
      const main = document.getElementById("main")
      if (target) target.scrollIntoView()
      else if (main) main.scrollTop = 0
    })
    return () => cancelAnimationFrame(frame)
  }, [])

  return (
    <AppShell header={<GalleryHeader />} nav={NAV}>
      <div className="flex flex-col gap-8 px-8 py-8">
        <div className="flex items-start justify-between gap-4">
          <div className="flex flex-col gap-1">
            <h1 className="text-xl leading-tight font-semibold tracking-tight">Gallery</h1>
            <p className="text-sm text-muted-foreground">
              Every pattern in every state. Screens build from <span className="mono">@/components/patterns</span>.{" "}
              <span className="mono tabular-nums">{patternEntries.length + 1}</span> patterns,{" "}
              <span className="mono tabular-nums">{uiEntries.length}</span> ui primitives.
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-4">
            <Label>
              <Switch
                checked={density === "compact"}
                onCheckedChange={(compact) => setDensity(compact ? "compact" : "comfortable")}
              />
              Compact density
            </Label>
            <Button
              variant="ghost"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
            >
              {theme === "dark" ? <SunIcon /> : <MoonIcon />}
              {theme === "dark" ? "Light" : "Dark"}
            </Button>
          </div>
        </div>
        <nav aria-label="Gallery contents" className="flex flex-col gap-3">
          <Contents title="src/components/patterns" entries={patternEntries} />
          <Contents title="src/components/ui" entries={uiEntries} />
        </nav>
        <div className="flex flex-col gap-16 pb-16">
          {galleryEntries.map((entry) => (
            <Specimen key={entry.id} entry={entry} />
          ))}
        </div>
      </div>
    </AppShell>
  )
}
