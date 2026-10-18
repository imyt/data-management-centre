# DMC design system

How Data Management Centre looks and behaves. Build screens from `frontend/src/components/patterns`; review them at the `/gallery` route.

## When principles conflict

Clarity, then accountability, then efficiency, then consistency, then calm. A screen that is unclear or hides who decided what is wrong, however tidy it looks.

## Experience principles

1. **Action first.** Every screen answers "what needs me?" before "what exists?". Home is the Inbox.
2. **Calm by default.** Paper neutrals, one accent used only for primary actions and identity, generous whitespace, few borders, no decorative charts.
3. **Show why.** Every derived decision (applied controls, classifications, auto-approvals) shows its reason and source.
4. **Context stays put.** Detail opens beside the list (docked at 1536px and wider) or in a sheet, never a new page by default.
5. **One status language.** Passing, failing, excepted, pending, not applicable: same colour, icon and word everywhere. Never colour alone.
6. **Built for power users.** Command palette (⌘K), shortcuts, bulk actions, saved views, density modes.
7. **Safe, accountable actions.** Preview impact, undo where possible, a reason on every risk decision.
8. **Fluid from 12" to 34".** Desktop only. Split views on wide screens, stacked on small ones.
9. **Accessible by design.** WCAG 2.2 AA, visible focus, full keyboard reach.
10. **Many things, one context.** Deep links, recents and pins, and compare instead of in-app tabs.

## Enterprise principles

11. **Permission-aware.** Hide what a user can never do; disable with a reason what they cannot do yet.
12. **Freshness is visible.** Every result shows when it was evaluated and from what source.
13. **Built for scale.** Server-side search, filter and paging; virtualised lists.
14. **Every state designed.** Empty, loading, partial, error, no access, not found.
15. **Long tasks in the background.** Scans, bulk changes and exports run as jobs with progress.
16. **Notifications with discipline.** Only actionable items notify; digests by default.
17. **Sensitive data masked by default.** Revealing is permissioned and logged.
18. **Predictable over clever.** Same action, same place, same words on every screen.
19. **Fast by budget.** Interactive in under 1 s, actions respond in under 100 ms, checked in CI.
20. **Help in context.** Inline explanations linked to the governing policy.
21. **Export and integrate.** Any view can be exported or reached through the API.
22. **Time and locale correct.** Local time with UTC on hover; locale formats.

The design system grows by harvesting patterns from real screens, not by designing components upfront.

## Identity

**Name.** Always "Data Management Centre" in the product header. "DMC" only where space forces it.

**Mark.** Four square corners framing a diamond: the four stages governing a data asset.

- 100 × 100 viewBox. Corners: `M 8 34 V 8 H 34`, `M 66 8 H 92 V 34`, `M 92 66 V 92 H 66`, `M 34 92 H 8 V 66`, stroke 12, miter joins.
- Diamond: `M 50 33 L 67 50 L 50 67 L 33 50 Z`; at 16 px and below use `M 50 37 L 63 50 L 50 63 L 37 50 Z`.
- Corners map clockwise from top left to Know, Assess, Act, Assure. As an indicator, lit corners use the accent and unlit corners use `--mark-idle`.
- Component: `DmcMark`.

**Colour.** Paper warm neutrals from the theme. Accent aubergine `#5B3A57` (dark mode `#C39BBD`), used for primary actions, focus, selection and identity only. Status colours are separate and never use the accent:

| Status | Light text / fill | Dark text / fill |
|---|---|---|
| Passing | `#2E6A47` / `#E5EFE8` | `#8FCAA6` / `#1F3329` |
| Failing | `#A23B2F` / `#F6E4E0` | `#EEA397` / `#3D221E` |
| Excepted | `#85580F` / `#F5EBD8` | `#E3BD7A` / `#3A2D17` |
| Pending | `#4F5B69` / `#EAEDF0` | `#B3BDC9` / `#272C32` |
| Not applicable | `#6E6A64` / `#EFEDEA` | `#B5B0A9` / `#2C2A27` |

Tokens live in `frontend/src/styles/patterns.css`.

**Type.** Inter for UI. Geist Mono for IDs, numbers, counts and timestamps, with tabular figures.

**Shape.** shadcn/ui with balanced radius. Hairline aubergine rule under the header is the one place the accent appears at rest.

## Layout

**Header** (`PortalHeader`): mark and full name (with the environment badge outside production), global navigation (Inbox with count, Assets, Applications, Controls, Reports), search (⌘K), scope switcher, posture readout with freshness, account menu.

**Sidebar** (`AppShell`): pages within the current section. Collapses to icons below 1280px; remembers the user's choice.

**Entity detail**: breadcrumb, `EntityHeader`, `StageTracker`, then the selected stage's panel with sub-sections. Failing counts show on sub-section tabs.

## Patterns

Built: `AppShell`, `PortalHeader` (with `EnvironmentBadge` outside production), `UpdateBanner`, `DmcMark`, `StageTracker`, `DetailSplit` and `DetailLayout`, `EntityHeader`, `StatusBadge`, `ExplainWhy`, `ConfirmWithReason`, state set (empty, error, no access, not found, loading). DataTable is maintained separately.

Next as screens need them: command palette, inbox and approval card, filter builder, compare view, lineage graph, audit timeline, evidence viewer, wizard, background job progress, notification centre.

## Content

- Sentence case everywhere. Buttons use the action's verb ("Accept risk", not "Confirm").
- Typographic apostrophes and quotes in UI text.
- IDs, counts and numbers in Geist Mono.
- Errors say what happened and what to do next.

## Enforcement

- Screens import from `components/patterns`, never `components/ui` (oxlint `no-restricted-imports`; the gallery is exempt).
- No raw hex or arbitrary Tailwind values outside the token file.
- axe and Playwright visual tests on the gallery; Lighthouse performance budgets.
- Every API response carries `allowed_actions`, `reason` for derived items, `evaluated_at`, and paging.
