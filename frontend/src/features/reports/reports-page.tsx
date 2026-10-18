import { LayoutDashboardIcon } from "lucide-react"

import { EmptyState } from "@/components/patterns"
import { Screen } from "@/features/shell/screen"

export function ReportsPage() {
  return (
    <Screen title="Reports">
      <EmptyState icon={LayoutDashboardIcon} title="No reports yet" description="Posture, coverage and remediation reports appear after the first evaluation." />
    </Screen>
  )
}
