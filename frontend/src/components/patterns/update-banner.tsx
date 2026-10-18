import { RefreshCwIcon } from "lucide-react"

import { Button } from "@/components/ui/button"

interface UpdateBannerProps {
  /** Defaults to a full page reload, which fetches the bundle that matches the API. */
  onReload?: () => void
}

/**
 * The API serves a newer contract than this bundle was built with (ADR 0004 §5). It can't be
 * dismissed: until the page reloads, requests may not match what the API expects.
 */
export function UpdateBanner({ onReload = () => window.location.reload() }: UpdateBannerProps) {
  return (
    <div
      role="alert"
      data-slot="update-banner"
      className="flex shrink-0 items-center justify-center gap-3 border-b border-warning bg-warning-bg px-4 py-1.5 text-sm text-foreground"
    >
      <RefreshCwIcon aria-hidden="true" className="size-4 text-warning" />
      <p>DMC has been updated. Reload to continue.</p>
      <Button variant="outline" size="sm" onClick={onReload}>
        Reload
      </Button>
    </div>
  )
}
