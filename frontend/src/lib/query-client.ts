import { QueryClient } from "@tanstack/react-query"

// Server state goes through TanStack Query, using the options generated in src/api/@tanstack.
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Governance data changes on evaluation runs, not by the second; refetch after 30s, not on every mount.
      staleTime: 30_000,
      // One retry for a transient failure; 4xx answers are final.
      retry: (failureCount, error) => failureCount < 1 && !isClientError(error),
      refetchOnWindowFocus: true,
    },
    mutations: { retry: false },
  },
})

// Generated query functions throw the parsed error body; RFC 9457 problem details carry `status`.
function isClientError(error: unknown): boolean {
  const status = (error as { status?: unknown } | null)?.status
  return typeof status === "number" && status >= 400 && status < 500
}
