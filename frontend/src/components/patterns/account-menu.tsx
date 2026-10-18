import { ChevronDownIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Skeleton } from "@/components/ui/skeleton"

export interface AccountUser {
  name: string
  /** Plain-language roles, e.g. "Data Owner". */
  role?: string
}

export interface PersonaOption {
  id: string
  name: string
  role: string
}

interface AccountMenuProps {
  user?: AccountUser | null
  loading?: boolean
  /** Dev authentication only: the seeded personas to act as. Omit and the switcher is hidden. */
  personas?: PersonaOption[]
  persona?: string
  onPersonaChange?: (id: string) => void
}

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("")
}

/** Who you are acting as, in the header. In dev authentication it also switches persona. */
export function AccountMenu({ user, loading, personas, persona, onPersonaChange }: AccountMenuProps) {
  if (loading) {
    return (
      <span role="status" className="flex items-center gap-2">
        <span className="sr-only">Loading your account</span>
        <Skeleton className="size-7 rounded-full" />
        <Skeleton className="hidden h-4 w-24 xl:block" />
      </span>
    )
  }

  const switching = !!personas?.length && !!onPersonaChange
  const name = user?.name ?? "Not signed in"

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm">
          <span
            aria-hidden="true"
            className="flex size-7 items-center justify-center rounded-full bg-subtle text-xs font-medium text-foreground"
          >
            {user ? initials(user.name) : "?"}
          </span>
          {/* Always the button's name; shown from xl, read out at every width. */}
          <span className="sr-only max-w-36 truncate xl:not-sr-only">{name}</span>
          {switching && <span className="sr-only">, switch persona</span>}
          <ChevronDownIcon aria-hidden="true" className="size-3.5 text-muted-foreground" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        <DropdownMenuLabel className="flex flex-col gap-0.5">
          <span>{name}</span>
          {user?.role && <span className="text-xs font-normal text-muted-foreground">{user.role}</span>}
          {!user && (
            <span className="text-xs font-normal text-muted-foreground">DMC could not tell who you are.</span>
          )}
        </DropdownMenuLabel>
        {switching && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuLabel className="text-xs font-normal text-muted-foreground">
              Act as (development only)
            </DropdownMenuLabel>
            <DropdownMenuRadioGroup value={persona} onValueChange={onPersonaChange}>
              {personas.map((p) => (
                <DropdownMenuRadioItem key={p.id} value={p.id}>
                  <span className="flex flex-col">
                    <span>{p.name}</span>
                    <span className="text-xs text-muted-foreground">{p.role}</span>
                  </span>
                </DropdownMenuRadioItem>
              ))}
            </DropdownMenuRadioGroup>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
