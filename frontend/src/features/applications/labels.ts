import type {
  Criticality,
  DataStoreType,
  EnvironmentType,
  HarvestStatus,
  Hosting,
  LifecycleStatus,
} from "@/api"
import type { SelectOption, Status } from "@/components/patterns"

// Words for the API's value sets, in sentence case (DESIGN.md: Content).

export const LIFECYCLE: Record<LifecycleStatus, string> = {
  planned: "Planned",
  active: "Active",
  retiring: "Retiring",
  decommissioned: "Decommissioned",
}

export const CRITICALITY: Record<Criticality, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
}

export const HOSTING: Record<Hosting, string> = {
  on_premises: "On premises",
  private_cloud: "Private cloud",
  public_cloud: "Public cloud",
  saas: "SaaS",
}

export const ENVIRONMENT_TYPE: Record<EnvironmentType, string> = {
  production: "Production",
  non_production: "Non-production",
}

export const DATA_STORE_TYPE: Record<DataStoreType, string> = {
  relational: "Relational database",
  document: "Document database",
  object_storage: "Object storage",
  warehouse: "Data warehouse",
  file_share: "File share",
}

export const HARVEST: Record<HarvestStatus, { status: Status; label: string }> = {
  never: { status: "pending", label: "Not harvested" },
  succeeded: { status: "passing", label: "Harvested" },
  failed: { status: "failing", label: "Harvest failed" },
}

export function optionsOf<T extends string>(labels: Record<T, string>): SelectOption[] {
  return (Object.entries(labels) as [T, string][]).map(([value, label]) => ({ value, label }))
}
