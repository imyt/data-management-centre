import * as React from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import type { AssetDetail, OwnershipRead, OwnershipRole } from "@/api"
import {
  assignOwnershipMutation,
  confirmOwnershipMutation,
  disputeOwnershipMutation,
  listUsersOptions,
} from "@/api/@tanstack/react-query.gen"
import { Button, ConfirmWithReason, Field, fieldA11y, SelectInput, StatusBadge, TextArea } from "@/components/patterns"
import { problemMessage } from "@/features/applications/problem"
import { OWNERSHIP_ROLE, OWNERSHIP_STATUS } from "@/features/assets/labels"
import { invalidateAssets } from "@/features/assets/queries"

const ROLES: OwnershipRole[] = ["owner", "steward"]
/** Who can hold each accountability (FR-K10). */
const HOLDER_ROLE = { owner: "data_owner", steward: "data_steward" } as const
const ASSIGN_ACTION = { owner: "assign_owner", steward: "assign_steward" } as const

function formatDate(value: string) {
  return new Date(value).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })
}

/** Data Owner and Data Steward: assign, confirm, reassign or dispute (FR-K10). */
export function OwnershipSection({ asset, actions }: { asset: AssetDetail; actions: string[] }) {
  return (
    <section aria-labelledby="ownership-heading" className="flex flex-col gap-3">
      <h3 id="ownership-heading" className="text-base font-semibold">
        Ownership
      </h3>
      <ul className="flex flex-col gap-3">
        {ROLES.map((role) => (
          <li key={role} className="rounded-md border p-4">
            <RoleRow asset={asset} role={role} ownership={role === "owner" ? asset.owner : asset.steward} actions={actions} />
          </li>
        ))}
      </ul>
    </section>
  )
}

interface RoleRowProps {
  asset: AssetDetail
  role: OwnershipRole
  ownership: OwnershipRead | null
  actions: string[]
}

function RoleRow({ asset, role, ownership, actions }: RoleRowProps) {
  const queryClient = useQueryClient()
  const [assigning, setAssigning] = React.useState(false)
  const [disputing, setDisputing] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const confirm = useMutation(confirmOwnershipMutation())
  const dispute = useMutation(disputeOwnershipMutation())
  const label = OWNERSHIP_ROLE[role]
  const state = ownership ? OWNERSHIP_STATUS[ownership.status] : null

  const canAssign = actions.includes(ASSIGN_ACTION[role])
  const canConfirm = actions.includes(`confirm_${role}`)
  const canDispute = actions.includes(`dispute_${role}`)

  async function onConfirm() {
    setError(null)
    try {
      await confirm.mutateAsync({ path: { asset_id: asset.id, role } })
      await invalidateAssets(queryClient)
    } catch (e) {
      setError(problemMessage(e))
    }
  }

  async function onDispute(reason: string) {
    try {
      await dispute.mutateAsync({ path: { asset_id: asset.id, role }, body: { reason } })
    } catch (e) {
      throw new Error(problemMessage(e))
    }
    await invalidateAssets(queryClient)
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="flex flex-col gap-0.5">
          <h4 className="text-sm font-semibold">{label}</h4>
          {ownership ? (
            <p className="text-sm">{ownership.user.display_name}</p>
          ) : (
            <p className="text-sm text-text-tertiary">Nobody is assigned yet.</p>
          )}
        </div>
        {state && <StatusBadge status={state.status} label={state.label} size="sm" />}
      </div>

      {ownership && (
        <p className="text-xs text-muted-foreground">
          Assigned {ownership.assigned_by ? `by ${ownership.assigned_by.display_name} ` : ""}on{" "}
          <span className="mono tabular-nums">{formatDate(ownership.assigned_at)}</span>
          {ownership.reason && <> · {ownership.status === "disputed" ? "Disputed" : "Reassigned"}: {ownership.reason}</>}
        </p>
      )}

      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}

      {!assigning && (canConfirm || canDispute || canAssign) && (
        <div className="flex flex-wrap gap-2">
          {canConfirm && (
            <Button size="sm" onClick={() => void onConfirm()} loading={confirm.isPending}>
              Confirm {label}
            </Button>
          )}
          {canDispute && (
            <Button size="sm" variant="secondary" onClick={() => setDisputing(true)}>
              Dispute
            </Button>
          )}
          {canAssign && (
            <Button size="sm" variant="ghost" onClick={() => setAssigning(true)}>
              {ownership ? "Reassign" : `Assign ${label}`}
            </Button>
          )}
        </div>
      )}

      {assigning && <AssignForm asset={asset} role={role} existing={ownership} onDone={() => setAssigning(false)} />}

      <ConfirmWithReason
        open={disputing}
        onOpenChange={setDisputing}
        title={`Dispute being ${label} of ${asset.name}`}
        description="Say why this assignment is wrong, so Governance can reassign it."
        confirmLabel="Dispute"
        onConfirm={onDispute}
      />
    </div>
  )
}

function AssignForm({
  asset,
  role,
  existing,
  onDone,
}: {
  asset: AssetDetail
  role: OwnershipRole
  existing: OwnershipRead | null
  onDone: () => void
}) {
  const queryClient = useQueryClient()
  const users = useQuery(listUsersOptions({ query: { role: HOLDER_ROLE[role] } }))
  const assign = useMutation(assignOwnershipMutation())
  const [userId, setUserId] = React.useState("")
  const [reason, setReason] = React.useState("")
  const [error, setError] = React.useState<string | null>(null)
  const id = `assign-${role}`
  const needsReason = existing !== null
  const options = (users.data?.data ?? [])
    .filter((u) => u.id !== existing?.user.id)
    .map((u) => ({ value: u.id, label: u.display_name }))
  const ready = userId !== "" && (!needsReason || reason.trim().length > 0)

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (!ready) return
    setError(null)
    try {
      await assign.mutateAsync({
        path: { asset_id: asset.id, role },
        body: { user_id: userId, reason: reason.trim() || null },
      })
      await invalidateAssets(queryClient)
      onDone()
    } catch (e) {
      setError(problemMessage(e))
    }
  }

  return (
    <form
      aria-label={`${existing ? "Reassign" : "Assign"} ${OWNERSHIP_ROLE[role]}`}
      className="flex flex-col gap-4 rounded-md border bg-surface p-4"
      onSubmit={(event) => void onSubmit(event)}
      noValidate
    >
      <Field label={OWNERSHIP_ROLE[role]} htmlFor={`${id}-user`} required>
        <SelectInput
          {...fieldA11y(`${id}-user`, {})}
          options={options}
          value={userId}
          onValueChange={setUserId}
          placeholder={`Choose a ${OWNERSHIP_ROLE[role]}`}
        />
      </Field>
      {needsReason && (
        <Field label="Reason" htmlFor={`${id}-reason`} required hint="Recorded in the audit trail.">
          <TextArea
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            {...fieldA11y(`${id}-reason`, { hint: "Recorded in the audit trail." })}
          />
        </Field>
      )}
      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onDone}>
          Cancel
        </Button>
        <Button
          type="submit"
          loading={assign.isPending}
          disabled={!ready}
          disabledReason={userId === "" ? `Choose a ${OWNERSHIP_ROLE[role]}.` : "Enter a reason."}
        >
          {existing ? "Reassign" : "Assign"}
        </Button>
      </div>
    </form>
  )
}
