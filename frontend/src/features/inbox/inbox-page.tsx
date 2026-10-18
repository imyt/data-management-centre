import { useQuery } from "@tanstack/react-query"
import { InboxIcon } from "lucide-react"
import { Link } from "react-router"

import type { InboxItem } from "@/api"
import { listInboxOptions } from "@/api/@tanstack/react-query.gen"
import { Button, EmptyState, ErrorState, LoadingState, StatusBadge } from "@/components/patterns"
import { Screen } from "@/features/shell/screen"

function formatDate(value: string) {
  return new Date(value).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })
}

/** Inbox: everything waiting on the current user. v1 lists ownership confirmations due. */
export function InboxPage() {
  const query = useQuery(listInboxOptions())

  return (
    <Screen title="Inbox">
      {query.isPending && <LoadingState label="Loading your Inbox" />}
      {query.isError && <ErrorState onRetry={() => void query.refetch()} retrying={query.isFetching} />}
      {query.isSuccess && query.data.data.length === 0 && (
        <EmptyState
          icon={InboxIcon}
          title="Nothing is waiting on you"
          description="Ownership confirmations, reviews and approvals that need you will appear here."
        />
      )}
      {query.isSuccess && query.data.data.length > 0 && (
        <ul aria-label="Waiting on you" className="flex max-w-3xl flex-col divide-y rounded-md border">
          {query.data.data.map((item) => (
            <InboxRow key={item.id} item={item} />
          ))}
        </ul>
      )}
    </Screen>
  )
}

function InboxRow({ item }: { item: InboxItem }) {
  return (
    <li className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
      <div className="flex min-w-0 flex-col gap-1">
        <span className="text-sm font-medium">{item.title}</span>
        <span className="text-xs text-muted-foreground">
          {item.requested_by ? `Assigned by ${item.requested_by} · ` : ""}Due{" "}
          <span className="mono tabular-nums">{formatDate(item.due_at)}</span>
        </span>
      </div>
      <div className="flex items-center gap-3">
        {item.overdue && <StatusBadge status="failing" label="Overdue" size="sm" />}
        <Button asChild variant="secondary" size="sm">
          <Link to={`/assets?asset=${item.subject_id}`}>Review</Link>
        </Button>
      </div>
    </li>
  )
}
