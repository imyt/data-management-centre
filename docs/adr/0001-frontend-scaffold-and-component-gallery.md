# ADR 0001: Frontend scaffold, shadcn adaptation and the component gallery

- Status: accepted
- Date: 2026-10-16

## Context

`frontend/` held only `DESIGN.md` and `src/tokens/tokens.css`. The frontend instructions require shadcn/ui components adapted to DESIGN.md, and a gallery at `/dev/components` that shows every `ui` and `pattern` component in all states (default, hover, focus, disabled, loading, error, empty), in light and dark, covered by Playwright screenshots and an axe check.

## Decisions

1. **Stack.** Vite, React 19, TypeScript, React Router (per DMC_ARCHITECTURE.md §15), Tailwind v4, shadcn/ui on `radix-ui`, TanStack Table v9 + TanStack Virtual, react-hook-form + zod, lucide-react, self-hosted Inter and Geist Mono (`@fontsource-variable`), sonner, cmdk. Tests: Vitest (unit), Playwright + `@axe-core/playwright` (gallery).
2. **shadcn components are added with the CLI and adapted with minimal diffs.** `npm run ui:adapt` (`scripts/adapt-shadcn.mjs`) swaps whole class tokens only: global focus outline instead of rings, `shadow-sm`/`shadow-lg` only and never with a border, token z-index (`z-popover`, `z-modal`), 4/6/10 radius, `control-height`, token durations, no `dark:` classes (dark mode lives in tokens.css). Code shape, exports and variant names stay as the CLI wrote them, so upstream updates merge cleanly.
3. **Targeted hand edits on top of the CLI output** (re-apply after any `--overwrite`):
   - `button.tsx`: variants restyled (default = filled accent, destructive = danger text, not a red fill); added `loading` and `disabledReason` (tooltip plus screen-reader text).
   - `badge.tsx`: added `success` and `warning`; `destructive` is a danger tint.
   - `sonner.tsx`: uses our `ThemeProvider` instead of `next-themes`.
   - `table.tsx`: sticky header, `row-height`, header in `text-muted-foreground`, selected row in `accent-bg`.
   - `tabs.tsx`: inactive tabs in `text-muted-foreground` (the CLI's `foreground/60` is 4.22:1 on the list background); accent active line.
   - `command.tsx`: `CommandEmpty` wraps its message in a disabled `role="option"`, because cmdk otherwise leaves an empty listbox (an axe violation on every "no results").
4. **Theme and density** are classes on `<html>` (`.dark`, `data-density="compact"`), as tokens.css expects. A small script in `index.html` applies the saved choice before first paint, so there is no flash or colour transition on load.
5. **Gallery hover/focus states** are live in the browser. For screenshots, Playwright forces `:hover` and `:focus-visible` through the Chrome DevTools protocol (`CSS.forcePseudoState`) on each cell's `[data-gallery-subject]`. A state that cannot apply to a component says why instead of being left out.
6. **Screenshots** run at the three DESIGN.md sizes (first screen) and per section at 1920×1080, in both themes. Baselines are platform-specific (`*-win32.png`); CI on Linux needs its own baselines (`npm run e2e:update`).

## Token changes made while building this

- `--warning` (light) `#8a6a00` → `#866700`, in DESIGN.md and tokens.css. The original was 4.41:1 on `warning-bg`, below AA; axe flagged it in the gallery. The new value is 4.62:1 on `warning-bg` and 5.27:1 on `bg-surface`.
- Font stacks in tokens.css now name `"Inter Variable"` and `"Geist Mono Variable"` first: those are the families `@fontsource-variable` registers. Without them the UI silently fell back to system fonts.

## Not done yet

- URL-synced filters and sort, column resize/reorder/hide, and saved views are the consuming feature's job; `DataTable` takes controlled `sorting` for that.
- The custom entity glyph set in DESIGN.md "Signature" does not exist yet; lucide covers everything for now.
- `eslint-plugin-boundaries` (architecture §15) is not set up; oxlint is.
