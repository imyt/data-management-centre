import * as React from "react"
import { MoonIcon, SunIcon } from "lucide-react"

import { patternEntries } from "@/dev/entries/pattern-entries"
import { uiEntries } from "@/dev/entries/ui-entries"
import { Specimen, type GalleryEntry } from "@/dev/specimen"
import { useTheme } from "@/lib/theme"
import { Button } from "@/ui/button"
import { Label } from "@/ui/label"
import { Switch } from "@/ui/switch"

export const galleryEntries: GalleryEntry[] = [...uiEntries, ...patternEntries]

function NavGroup({ title, entries }: { title: string; entries: GalleryEntry[] }) {
  return (
    <div className="flex flex-col gap-1">
      <p className="mono px-2 text-text-tertiary">{title}</p>
      <ul className="flex flex-col">
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

/** /dev/components: every ui and pattern component with all states, in light and dark. */
export function ComponentsPage() {
  const { theme, setTheme, density, setDensity } = useTheme()
  const mainRef = React.useRef<HTMLElement>(null)

  // cmdk scrolls its first item into view on mount, which drags the gallery down. Start at the
  // top, or at the linked section when the URL has a hash.
  React.useEffect(() => {
    const frame = requestAnimationFrame(() => {
      const target = window.location.hash ? document.getElementById(window.location.hash.slice(1)) : null
      if (target) target.scrollIntoView()
      else if (mainRef.current) mainRef.current.scrollTop = 0
    })
    return () => cancelAnimationFrame(frame)
  }, [])

  return (
    <div className="flex h-screen flex-col">
      <header className="z-nav flex h-12 shrink-0 items-center justify-between gap-4 bg-surface px-6">
        <div className="flex items-baseline gap-3">
          <h1 className="text-lg leading-tight font-semibold tracking-tight">Component gallery</h1>
          <span className="text-sm text-text-tertiary">
            {uiEntries.length} ui, {patternEntries.length} patterns
          </span>
        </div>
        <div className="flex items-center gap-4">
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
      </header>
      <div className="flex min-h-0 flex-1">
        <nav aria-label="Components" className="flex w-60 shrink-0 flex-col gap-6 overflow-y-auto p-4">
          <NavGroup title="src/ui" entries={uiEntries} />
          <NavGroup title="src/patterns" entries={patternEntries} />
        </nav>
        <main ref={mainRef} className="min-w-0 flex-1 overflow-y-auto px-8 py-8">
          <div className="flex flex-col gap-16 pb-16">
            {galleryEntries.map((entry) => (
              <Specimen key={entry.id} entry={entry} />
            ))}
          </div>
        </main>
      </div>
    </div>
  )
}
