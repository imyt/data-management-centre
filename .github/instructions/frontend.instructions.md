---
applyTo: "frontend/**"
---

# Frontend instructions

Read `DESIGN.md` and `frontend/src/tokens/tokens.css` before writing any UI. If a request conflicts with them, follow them and flag the conflict.

## Stack
React, TypeScript, Tailwind v4, shadcn/ui (Radix), TanStack Table, react-hook-form + zod, lucide-react plus our custom glyphs. Desktop only (1280 to 3440px wide).

## Structure and imports
```
src/tokens/     tokens.css
src/ui/         shadcn-based primitives
src/patterns/   composed: data table, filters, forms, empty/error states
src/features/   app-specific; workflow screens
src/api/        generated client (do not hand-edit)
src/dev/        component gallery at /dev/components
```
- `ui` imports tokens only. `patterns` import `ui`. `features` import `patterns`, `ui`, `api`.
- `ui` never imports from `patterns` or `features`.
- Features never import Radix or shadcn internals directly; go through `ui` and `patterns`.

## Styling rules
- Use only design tokens through Tailwind utilities: `bg-background`, `bg-card`, `bg-subtle`, `text-foreground`, `text-muted-foreground`, `text-text-tertiary`, `border-border`, `border-input`, `bg-primary`, `text-primary-foreground`, `bg-brand-bg`, `text-success` / `bg-success-bg`, `text-warning` / `bg-warning-bg`, `text-danger` / `bg-danger-bg`.
- **Never:** inline styles, raw hex or rgb, arbitrary Tailwind values (`w-[13px]`, `text-[#...]`), raw `z-index` (use `z-sticky`, `z-pane`, `z-popover`, `z-modal`, `z-toast`), font weights above 600, ALL CAPS.
- Type sizes come from the scale only (12, 13, 15, 17, 22, 28, 34px). Spacing is 4px steps.
- One accent (teal, `primary`) for interaction only. Status colors always pair with an icon and label.
- Record IDs and timestamps use `.mono`; numbers in tables use `.tabular` and are right-aligned.
- Empty values render as `—`.

## Components
- Add missing shadcn components with `npx shadcn@latest add <name>`, then adapt them to DESIGN.md (our palette, 4/6/10 radius, no extra shadows or borders) before using them.
- Restyle through variants (cva) in `/ui`, never with one-off class overrides at call sites.
- Check `/dev/components` before creating anything new. Reuse over invent.
- Every new `ui` or `pattern` component is added to the gallery with default, hover, focus, disabled, loading, error, and empty states, in light and dark.

## Behavior
- One primary action per view.
- Every data view has loading (skeleton), empty, and error-with-retry states.
- Tables: TanStack Table, virtualized past 100 rows, sticky header, URL-synced filters and sort, no hover-only actions.
- Forms: react-hook-form + zod, label above input, inline validation in plain language.
- Hide actions the user can never perform; disable with a reason when temporarily blocked.
- Workflows render from schema (fields, rules, transitions); never fork a component per workflow.
- Everything is keyboard reachable with a visible focus ring. Respect reduced motion.

## Tests
- Unit tests for logic and hooks; Playwright for flows.
- Gallery route gets Playwright screenshot tests and an axe check (no violations).
- Check layouts at 1280x800, 1920x1080, and 3440x1440.

## Self-check before finishing
- Any raw color, size, or z-index left? Remove it.
- More than one primary action, or an extra border, shadow, or color that can go? Remove it.
- Keyboard reachable? Contrast passes? States covered? Light and dark verified?
