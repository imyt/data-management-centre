import type { AssetType, OwnershipRole, OwnershipStatus } from "@/api"
import type { Status } from "@/components/patterns"

// Words for the API's value sets, in sentence case (DESIGN.md: Content).

export const ASSET_TYPE: Record<AssetType, string> = {
  dataset: "Dataset",
  report: "Report",
  model: "Model",
  file: "File",
}

export const OWNERSHIP_ROLE: Record<OwnershipRole, string> = {
  owner: "Data Owner",
  steward: "Data Steward",
}

export const OWNERSHIP_STATUS: Record<OwnershipStatus, { status: Status; label: string }> = {
  pending: { status: "pending", label: "Awaiting confirmation" },
  confirmed: { status: "passing", label: "Confirmed" },
  disputed: { status: "failing", label: "Disputed" },
}

export const YES_NO = [
  { value: "no", label: "No" },
  { value: "yes", label: "Yes" },
]
