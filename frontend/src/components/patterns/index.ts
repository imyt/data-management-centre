// The only import surface for screens in src/features (enforced in .oxlintrc.json).
export { AppShell, type NavGroup, type NavItem } from "./app-shell"
export { ConfirmWithReason } from "./confirm-with-reason"
export {
  createDataTableColumns,
  DataTable,
  dataTableFeatures,
  type DataTableColumn,
  type DataTableColumnMeta,
  type DataTableFeatures,
} from "./data-table"
export { DetailLayout, DetailSplit, useDetail, useDetailParam } from "./detail-split"
export { DmcMark, STAGES, type Stage } from "./dmc-mark"
export { EntityHeader, type EntityMeta } from "./entity-header"
export { ExplainWhy, type ExplainSource } from "./explain-why"
export { Field, fieldA11y, ReadOnlyField } from "./field"
export { FilterChips, type ActiveFilter } from "./filter-chips"
export {
  GlobalNav,
  PortalHeader,
  PostureReadout,
  ScopeSwitcher,
  SECTIONS,
  type Posture,
  type ScopeOption,
  type Section,
} from "./portal-header"
export { StageTracker, stageTabId, type StageState, type StageTone } from "./stage-tracker"
export { EmptyState, ErrorState, LoadingState, NoAccessState, NotFoundState } from "./states"
export { StatusBadge, STATUSES, type Status } from "./status-badge"
