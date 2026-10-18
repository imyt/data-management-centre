import { DatabaseIcon } from "lucide-react"

import { EmptyState } from "@/components/patterns"
import { Screen } from "@/features/shell/screen"

export function AssetsPage() {
  return (
    <Screen title="Assets">
      <EmptyState icon={DatabaseIcon} title="No assets yet" description="Assets appear here once data stores are harvested." />
    </Screen>
  )
}
