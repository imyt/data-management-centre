import * as React from "react"
import { useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query"

import { getMeOptions, listDevUsersOptions } from "@/api/@tanstack/react-query.gen"
import type { Role, UserRead } from "@/api/types.gen"
import type { AccountUser, PersonaOption } from "@/components/patterns"
import { getDevUser, setDevUser } from "@/lib/dev-user"

export const ROLE_LABELS: Record<Role, string> = {
  data_owner: "Data Owner",
  application_owner: "Application Owner",
  data_steward: "Data Steward",
  process_owner: "Process Owner",
  governance: "Governance team",
  leadership: "Leadership",
  auditor: "Auditor",
}

function rolesLabel(user: UserRead) {
  return user.roles.map((r) => ROLE_LABELS[r]).join(", ")
}

/**
 * Act as another persona: store it for the request header, then drop every cached response, since
 * each was fetched as the previous persona. Active queries refetch as the new one.
 */
export async function switchPersona(queryClient: QueryClient, username: string | null) {
  setDevUser(username)
  await queryClient.resetQueries()
}

/** The current user from /me and, when dev authentication is on, the personas to switch between. */
export function useIdentity() {
  const queryClient = useQueryClient()
  const me = useQuery(getMeOptions())
  // 404 unless the backend runs DMC_AUTH_MODE=dev; then there is nothing to switch.
  const devUsers = useQuery({ ...listDevUsersOptions(), retry: false, staleTime: Infinity })

  // A stored persona that no longer exists (a reseeded database) gets 401: fall back to the default.
  const meStatus = (me.error as { status?: number } | null)?.status
  React.useEffect(() => {
    if (meStatus === 401 && getDevUser()) void switchPersona(queryClient, null)
  }, [meStatus, queryClient])

  const user: AccountUser | null = me.data ? { name: me.data.data.display_name, role: rolesLabel(me.data.data) } : null
  const personas: PersonaOption[] | undefined = devUsers.data?.data.map((u) => ({
    id: u.username,
    name: u.display_name,
    role: rolesLabel(u),
  }))

  return {
    user,
    loading: me.isPending,
    personas,
    persona: me.data?.data.username,
    onPersonaChange: (username: string) => void switchPersona(queryClient, username),
  }
}
