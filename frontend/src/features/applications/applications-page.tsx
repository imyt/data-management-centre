import { AppWindowIcon } from "lucide-react"

import { EmptyState } from "@/components/patterns"
import { Screen } from "@/features/shell/screen"

export function ApplicationsPage() {
  return (
    <Screen title="Applications">
      <EmptyState icon={AppWindowIcon} title="No applications yet" description="Applications appear here once they are registered." />
    </Screen>
  )
}
