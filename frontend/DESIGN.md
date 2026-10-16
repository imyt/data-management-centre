# DESIGN.md

The product should feel calm, precise, and quiet. The interface recedes; the user's content leads. When in doubt, remove something.

## Principles

1. **Content first.** Chrome (borders, fills, icons, labels) exists only to serve content. If removing it loses no meaning, remove it.
2. **One primary action per view.** Exactly one filled primary button on screen. Everything else is secondary or tertiary.
3. **Hierarchy through type and space, not decoration.** Use size, weight, and whitespace before color, borders, or shadows.
4. **Restraint with color.** Neutral surfaces. One accent color, used only for interaction (links, primary action, focus, selection). Semantic colors (success, warning, danger) appear only when meaning requires them.
5. **Consistency over novelty.** Reuse an existing component before creating one. A new pattern needs a reason.
6. **Motion explains, never entertains.** Animate only to show cause and effect (open, close, reorder). Short, eased, interruptible.
7. **Accessible by default.** Keyboard, focus, contrast, and screen readers are part of "done."

## Tokens (the only allowed values)

Never use raw hex, px, or arbitrary values outside the token files.

**Color (semantic roles, light and dark both required)**
- `bg-canvas`, `bg-surface`, `bg-subtle`
- `text-primary`, `text-secondary`, `text-tertiary`
- `border-subtle` (hairline, used sparingly)
- `accent`, `accent-hover`, `on-accent`
- `success`, `warning`, `danger` (text and tinted background only)

**Typography**
- Default font: **Inter** (variable, self-hosted). Fallback stack: `"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`
- Enable `font-feature-settings: "cv11", "ss01"` and `tabular-nums` for numeric columns
- Scale: 12, 13, 15 (body), 17, 22, 28, 34. No other sizes.
- Weights: 400 regular, 500 medium, 600 semibold. Never bold (700+).
- Line height: 1.4 to 1.5 body, 1.2 to 1.3 headings. Slight negative tracking on large headings.
- Sentence case everywhere. No ALL CAPS, no underlines except links.

**Spacing:** 4px base. Allowed: 4, 8, 12, 16, 24, 32, 48, 64. Prefer larger gaps over dividers.

**Radius:** 4 (controls), 6 (inputs, cards), 10 (modals, sheets). Consistent per component type.

**Elevation:** Prefer none. Allowed: `shadow-sm` (menus, popovers) and `shadow-lg` (modals). Shadows are soft and low-opacity. No colored shadows, no glows.

**Motion:** 150ms (hover, press), 250ms (open, close). Ease-out. Respect `prefers-reduced-motion`.

## Layout

- Generous whitespace. Density is "comfortable" by default; offer "compact" only for data-heavy tables.
- Max content width for reading: 720px. Align to a 12-column grid; keep consistent page margins.
- Left-align text. Center only empty states and auth screens.
- One column of focus per screen where possible. Progressive disclosure for secondary detail.

## Screen sizes (desktop only)

No mobile or tablet layouts. Supported range: 12" laptop (1280 x 800) to 34" ultrawide (3440 x 1440). Below 1280px wide, show a "best viewed on a larger screen" notice; do not build a mobile layout.

| Tier | Width | Behavior |
|---|---|---|
| Compact | 1280 to 1535 | Nav collapses to a 56px icon rail. Detail opens as an overlay sheet, not a side-by-side pane. Default to compact density. |
| Standard | 1536 to 1919 | Expanded nav (240px). List and detail side by side. |
| Wide | 1920 to 2559 | Optional third pane (activity, related records) beside the form. |
| Ultrawide | 2560+ | Never stretch content. Extra width goes to panes (list, detail, context), not wider lines. |

**Rules**
- Tables may use the full width; forms, text, and activity streams cap at 720px, panes at their own max.
- Panes are resizable and remember their width per user.
- Vertical space is scarcer than horizontal on laptops: header 48px, no more than 96px of stacked sticky elements, tables scroll inside their container.
- Use `rem` and tokens so browser zoom (100 to 150%) and OS scaling work without breaking layout.
- Test every screen at 1280 x 800, 1920 x 1080, and 3440 x 1440.

## Component foundation: shadcn/ui

All UI is built on **shadcn/ui** (Radix primitives + Tailwind). Components are copied into `/ui` and owned by us.

- Add components with the CLI (`npx shadcn@latest add <name>`); never hand-roll what shadcn provides (Button, Input, Select, Dialog, Sheet, Popover, Dropdown Menu, Command, Tabs, Table, Tooltip, Toast/Sonner, Form, Checkbox, Switch, Badge, Skeleton, Breadcrumb)
- Map shadcn CSS variables (`--background`, `--foreground`, `--primary`, `--muted`, `--border`, `--ring`, `--radius`) to our semantic tokens in `tokens/`; light and dark both defined
- shadcn's `--accent` means a subtle hover surface, not our brand color; our teal is `--primary`
- Set `--primary` to our teal accent; set `--radius` to 6px
- Restyle by editing the component in `/ui` or its variants (cva), never with one-off class overrides at call sites
- Replace shadcn's default palette, radius, and focus ring with ours before shipping any component
- Strip default decoration that violates this file (extra shadows, heavy borders, bold weights) when adding a component
- Data tables use **TanStack Table** with shadcn's Table; the Command component powers the ⌘K palette
- Forms use shadcn Form with react-hook-form and zod
- Icons: **lucide-react** for generic UI, plus our custom entity glyph set (see Signature); 16 or 20px, consistent stroke
- Compose, don't fork: patterns (`/patterns`) wrap shadcn components; features never import Radix or shadcn internals directly

## Signature (what makes this not a default shadcn app)

Restraint stays. Identity comes from a few deliberate choices applied everywhere, not extra decoration. Decisions below are made; change them here first, then in tokens.

**Color**
- **Paper**: warm neutral ramp (never stock zinc or slate). Canvas is warm off-white, text is warm near-black.
- One accent: **teal**. Interaction only (links, primary action, focus, selection). Never used for status.
- Layers separate by tonal background steps (`bg-canvas` < `bg-surface` < `bg-subtle`), not borders or shadows.

**Palette (starting values, light / dark; verify contrast before locking)**

| Token | Light | Dark |
|---|---|---|
| `bg-canvas` | `#FAF8F5` | `#171513` |
| `bg-surface` | `#FFFEFC` | `#1F1C19` |
| `bg-subtle` | `#F1EDE7` | `#28241F` |
| `border-subtle` | `#E7E2DA` | `#34302A` |
| `border-strong` (controls) | `#8F8A81` | `#77726A` |
| `accent-bg` (selection) | `#E3F1F0` | `#12302F` |
| `text-primary` | `#1F1D1A` | `#F2EFEA` |
| `text-secondary` | `#5E5A53` | `#B5B0A7` |
| `text-tertiary` | `#76716A` | `#8F8A81` |
| `accent` | `#0E7C7B` | `#3FB8B5` |
| `accent-hover` | `#0A6564` | `#5CCBC8` |
| `on-accent` | `#FFFFFF` | `#171513` |
| `success` | `#2F6B3F` | `#6FBF86` |
| `warning` | `#866700` | `#D9B23F` |
| `danger` | `#B42318` | `#F0867A` |

**Status color:** success (green), warning (ochre), and danger (red) are distinct from the teal accent. Status always appears with an icon and label, never color alone. The accent is never used on error states or validation.

**Font loading:** Inter and Geist Mono self-hosted, variable, `font-display: swap`.

**Type**
- Inter for UI text; **Inter Display** with tight tracking for page titles and large numbers.
- Record IDs, timestamps, and metadata use the mono face (**Geist Mono**), 12 or 13px. This is a signature; use it consistently.
- Page titles get more size and whitespace than typical SaaS.

**Shape**
- **Balanced** radius: 4px (controls), 6px (inputs, cards), 10px (modals, sheets). Replaces the earlier 6/10/14 values. Same family everywhere.
- Custom focus ring and selection style, defined once in tokens.

**Layout**
- Record-centric, not dashboard-centric: list-to-detail split panes, ⌘K as primary navigation.
- No default "sidebar + KPI cards + table" template. No stat-card grids.
- Navigation is quiet: text-first, minimal icons, no colored badges unless actionable.

**Domain identity**
- Custom glyph set for core entities and statuses (domain, asset, term, policy, workflow state). lucide covers generic UI only.
- Signature views (lineage, quality scores, ownership, workflow stage) are designed by hand, not assembled from generic chart blocks.

**Motion**
- One signature transition: list rows expand into the detail panel. Everything else stays minimal.

**Reject on review**
- Unmodified shadcn blocks or examples pasted in
- Gradient pills, glows, or decorative illustration
- Generic empty states with stock artwork
- Default shadcn zinc palette or default radius left in place

## Components

- **Buttons:** Primary (filled accent), Secondary (subtle fill), Tertiary (text only). Destructive actions use danger text, confirmed in a dialog, never a red filled button by default.
- **Inputs:** Label above, subtle border, accent focus ring. Inline validation with plain language. No placeholder-as-label.
- **Tables:** No zebra stripes, no vertical borders. Hairline row separators or none. Sticky header, right-align numbers.
- **Cards:** Use sparingly. Prefer plain sections with spacing. No nested cards.
- **Modals:** Only for focused, interruptive tasks. One title, one primary action, escape to close.
- **Icons:** One set, one stroke weight, 16 or 20px. Icons support text, they rarely replace it.
- **Empty, loading, error states:** Required for every data view. Calm, short, with one clear next step. Skeletons over spinners.

## Voice

Plain, short, human. Say what happened and what to do next. No exclamation marks, no jargon, no blame.

## Do not

- Gradients, glassmorphism, or decorative illustration in product UI
- More than one accent color
- Borders and shadows on the same element
- Custom one-off spacing, colors, or font sizes
- Placeholder text as the only label
- Disabled buttons without explanation
- Emoji as icons

## Data-dense patterns

Density comes from tight spacing and small type (13px), never from extra borders or color. Hairlines and whitespace rhythm stay.

**Density modes:** comfortable (default) and compact (tables, lists). Persist per user.

**Data table (required behaviors)**
- Sticky header and first column; right-align numbers; truncate with tooltip
- Resize, reorder, hide columns; saved per user
- Virtualized rows beyond 100; skeleton rows while loading
- Multi-column sort and group; server-side for large sets
- Cursor pagination with total count; selection persists across pages
- Row click opens detail panel; no hover-only actions (keyboard parity)

**Finding**
- Global search and command palette (⌘K) for navigation and actions
- Faceted filters as removable chips; state synced to the URL
- Saved views (filters, columns, sort), shareable by link

**Detail and hierarchy**
- Side panel or split view keeps list context
- Tree views lazy-load, expand with arrow keys
- Lineage/graph views: zoom, pan, collapse, focus on node; color only for status

**Acting on data**
- Bulk action bar appears on selection; destructive bulk actions confirm with count
- Inline edit: click to edit, validate, Esc cancels, undo toast after save
- Import/export: CSV with preview, validation report, downloadable error file
- Optimistic updates with rollback and clear failure message

**Trust**
- Stale-data indicator with last refreshed time
- Every record has history: who, what, when, with diff view
- Read-only and no-permission states are explained, not just disabled

**Keyboard:** arrow navigation in tables and trees, `/` focuses search, `?` shows shortcuts. Focus is always visible and never lost after an action.

## Workflow patterns (ServiceNow-style)

Records move through states under rules. The UI makes the current state, owner, and next step obvious.

**Record form**
- Header: record ID, title, status badge, priority, assignee, and primary action
- Two-column field layout in sections; activity stream on the side or below
- Fields can be conditionally shown, required, or read-only by state and role (UI policies); explain why when locked
- Dirty state is visible; unsaved changes warn before leaving

**State and stage**
- Stage indicator at the top (stepper) for linear processes; status badge for the rest
- Only valid next transitions are offered as actions; invalid ones are hidden, not disabled
- Transitions that need input (reason, resolution notes) open a short dialog
- Status uses text plus a subtle tint; never color alone

**Queues and lists**
- Work queues: "Assigned to me", "My team", "Unassigned", with counts
- Priority and SLA columns; breach risk shown as text ("Due in 2h"), color only when breached
- Quick assign and claim actions inline; bulk reassign

**Approvals**
- Approval card shows what is requested, by whom, impact, and linked record
- Approve and Reject with required comment on reject; one primary action
- Approver list with state per person (pending, approved, rejected), in order

**Activity stream**
- Single chronological feed: comments, work notes (internal), state changes, field changes
- Toggle between public comments and internal notes; internal notes are labeled
- @mentions notify; system events are quieter than human comments

**Related records**
- Related lists under the form (tasks, linked items, attachments) using the same data table
- Create linked record from context; parent/child relationships visible

**Request/catalog forms**
- Short, sectioned, progressive disclosure; conditional questions
- Review step before submit; confirmation shows record ID and what happens next

**Notifications:** in-app inbox plus email; each item links to the record and states the action needed.

**Admin-configurable (design for it)**
- Workflow states, transitions, SLAs, and form layouts come from configuration, not hardcoded in components
- Components render from schema (fields, rules, actions); never fork a component per workflow

## Accessibility

- **Contrast:** WCAG AA minimum. 4.5:1 for text, 3:1 for large text, icons, and control borders. `text-tertiary` is for non-essential metadata only.
- **Focus:** visible on every interactive element. 2px teal ring with 2px offset, same style everywhere. Never remove an outline without replacing it.
- **Hit targets:** 32px minimum height in compact density, 36px in comfortable. Icon-only buttons need an accessible name and a tooltip.
- **Keyboard:** every action reachable without a mouse. Logical tab order, focus returns to the trigger when a dialog or sheet closes, Esc closes overlays.
- **Color:** never the only carrier of meaning. Status uses icon plus label.
- **Motion:** respect `prefers-reduced-motion` (swap transitions for instant changes).
- **Screen readers:** semantic landmarks, table headers and `aria-sort`, live regions for toasts and async results, labels on every input.
- **Zoom:** layouts work at 150% browser zoom without horizontal scrolling of the page.

## Permissions in the UI

- **Hide** actions the user can never perform with their role, and transitions that are invalid for the current state.
- **Disable with a reason** (tooltip or inline text) when the action is normally available but blocked right now: missing required field, record locked by another user, pending approval.
- **Read-only fields** look like plain text, not greyed-out inputs. Show who or what controls the field if it is not obvious.
- **No access to a page or record:** a calm "You don't have access" state with who to ask, never a blank page or raw error.
- Never rely on the UI for security; the backend enforces every permission.

## Layering scale

Use tokens, never raw `z-index` values.

| Token | Value | Use |
|---|---|---|
| `z-base` | 0 | Page content |
| `z-sticky` | 10 | Table headers, sticky columns |
| `z-nav` | 20 | App header, nav rail |
| `z-pane` | 30 | Side panes, sheets |
| `z-popover` | 40 | Dropdowns, popovers, tooltips, command palette |
| `z-modal` | 50 | Dialogs and their backdrop |
| `z-toast` | 60 | Toasts, always on top |

## Formatting conventions

- **Dates:** `16 Oct 2026` in tables and detail. Relative time ("2h ago") for activity under 7 days, with the exact timestamp in a tooltip. Use the user's locale and time zone; store UTC.
- **Timestamps in records:** mono face, `2026-10-16 14:32`.
- **Numbers:** locale-aware separators, tabular figures, right-aligned. Abbreviate (1.2k, 3.4M) only in tight spaces, with the full value in a tooltip.
- **Percentages and scores:** consistent precision per column (for example, one decimal).
- **Empty and null values:** show `—` (em dash) in tables and read-only fields, never "null", "N/A", or blank. Empty collections get the empty state, not an empty table.
- **Truncation:** single-line ellipsis with full text in a tooltip. Record IDs are never truncated.
- **Names and IDs:** record IDs in mono, copyable on click or hover.
- **Units and currency:** always explicit, in the column header when constant.

## Rules for AI agents

1. Read this file and the token files before writing any UI.
2. Use only shadcn-based components from `/ui` and tokens. If a needed component is missing, add it via the shadcn CLI, then adapt it to this file. Check the component gallery (`/dev/components`) before creating anything new.
3. No inline styles, no raw hex, no arbitrary Tailwind values (`w-[13px]`).
4. Every new component is added to the gallery route (`/dev/components`) showing default, hover, focus, disabled, loading, error, and empty states, in light and dark.
5. Before finishing, self-check: one primary action? Extra borders or colors that can go? Keyboard reachable? Contrast passes?
6. If a request conflicts with this file, follow this file and flag the conflict.

## Definition of done (UI)

- Uses tokens and existing components only
- Light and dark verified
- Checked at 1280 x 800, 1920 x 1080, and 3440 x 1440
- Keyboard and screen reader pass (axe clean), focus ring and contrast meet the Accessibility rules
- All states shown in the component gallery (`/dev/components`)
- Visual regression snapshot updated
