import { useOutletContext } from "react-router"

/** What AppLayout passes to every section screen through its <Outlet>. */
export interface ShellContext {
  /** The domain picked in the header's scope switcher; null means all domains. */
  domainId: string | null
}

export const ALL_DOMAINS = "all"

/** The scope switcher's domain, for server-side filtering. Null when the scope is all domains. */
export function useScopeDomain(): string | null {
  return useOutletContext<ShellContext | undefined>()?.domainId ?? null
}
