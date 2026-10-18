import { ShieldCheckIcon } from "lucide-react"

import { EmptyState } from "@/components/patterns"
import { Screen } from "@/features/shell/screen"

export function ControlsPage() {
  return (
    <Screen title="Controls">
      <EmptyState icon={ShieldCheckIcon} title="No applied controls yet" description="Applied controls and their evaluations will appear here." />
    </Screen>
  )
}
