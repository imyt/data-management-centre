import { InboxIcon } from "lucide-react"

import { EmptyState } from "@/components/patterns"
import { Screen } from "@/features/shell/screen"

export function InboxPage() {
  return (
    <Screen title="Inbox">
      <EmptyState icon={InboxIcon} title="Nothing is waiting on you" description="Reviews, approvals and exceptions that need you will appear here." />
    </Screen>
  )
}
