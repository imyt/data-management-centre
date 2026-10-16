#!/usr/bin/env node
// Adapt shadcn CLI output in src/ui to DESIGN.md by swapping whole class tokens only.
// Code shape, exports and variant names stay exactly as the CLI wrote them, so later
// `npx shadcn@latest add <name> --overwrite` runs can be re-adapted with `npm run ui:adapt`.
// Hand edits on top (Button loading/disabledReason, Badge status variants, Sonner theme,
// Table/Tabs colours, CommandEmpty option) must be re-applied after an overwrite; see
// docs/adr/0001-frontend-scaffold-and-component-gallery.md.
import { readdirSync, readFileSync, writeFileSync } from "node:fs"
import { join } from "node:path"

const UI = process.argv[2] ?? "src/ui"

const DROP = new Set([
  // Focus: tokens.css draws one global 2px accent outline with 2px offset on :focus-visible.
  "outline-none", "focus-visible:border-ring", "focus-visible:ring-[3px]", "focus-visible:ring-ring/50",
  "focus-visible:outline-1", "focus-visible:outline-ring", "focus:ring-2", "focus:ring-ring",
  "focus:ring-offset-2", "focus:outline-hidden", "ring-offset-background",
  "focus-visible:ring-destructive/20", "aria-invalid:ring-destructive/20",
  // Elevation: only shadow-sm (menus) and shadow-lg (modals) exist.
  "shadow-xs", "shadow-2xs",
  "group-data-[variant=default]/tabs-list:data-[state=active]:shadow-sm",
  "group-data-[variant=line]/tabs-list:data-[state=active]:shadow-none",
  // Selection colour is set once in tokens.css (::selection uses accent-bg).
  "selection:bg-primary", "selection:text-primary-foreground",
  // One size from the scale, no responsive bumps.
  "md:text-sm",
  // Durations come from tokens.
  "data-[state=closed]:duration-300",
])

const REPLACE = new Map([
  ["shadow-md", "shadow-sm"],
  ["bg-black/50", "bg-canvas/80"],
  ["rounded-xs", "rounded-sm"],
  ["rounded-[4px]", "rounded-sm"],
  ["rounded-[2px]", "rounded-sm"],
  ["h-9", "h-(--control-height)"],
  ["size-9", "size-(--control-height)"],
  ["duration-200", "duration-base"],
  ["data-[state=open]:duration-500", "duration-base"],
  ["text-white", "text-primary-foreground"],
  ["transition-all", "transition-colors"],
])

const MODAL_FILES = new Set(["dialog.tsx", "sheet.tsx"])
const FIELD_FILES = new Set(["input.tsx", "textarea.tsx", "select.tsx"])
const BORDERS = new Set(["border", "border-l", "border-r", "border-t", "border-b"])

function adaptClasses(text, file) {
  const tokens = text.split(" ")
  if (!tokens.some((t) => t.includes("-") || t.includes(":"))) return text // not a class string
  let out = []
  for (let t of tokens) {
    if (t.startsWith("dark:") || DROP.has(t)) continue // dark mode lives in tokens.css
    t = REPLACE.get(t) ?? t
    if (t === "z-50") t = MODAL_FILES.has(file) ? "z-modal" : "z-popover"
    if (FIELD_FILES.has(file) && t === "bg-transparent" && tokens.includes("border-input")) t = "bg-surface"
    if (FIELD_FILES.has(file) && t === "text-base") t = "text-sm"
    out.push(t)
  }
  // Never a border and a shadow on the same element.
  if (out.includes("shadow-sm") || out.includes("shadow-lg")) {
    out = out.filter((t) => !BORDERS.has(t)).map((t) => (t === "bg-background" ? "bg-surface" : t))
  }
  return out.filter(Boolean).join(" ")
}

for (const name of readdirSync(UI).sort()) {
  if (!name.endsWith(".tsx")) continue
  const path = join(UI, name)
  const src = readFileSync(path, "utf8")
  const next = src
    .replace('import { cn } from "cn"', 'import { cn } from "@/lib/utils"')
    .replace(/"([^"\n]*)"/g, (_, classes) => `"${adaptClasses(classes, name)}"`)
  if (next !== src) {
    writeFileSync(path, next)
    console.log(`adapted ${name}`)
  }
}
