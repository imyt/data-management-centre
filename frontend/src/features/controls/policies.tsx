import * as React from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { PlusIcon } from "lucide-react"
import { Link } from "react-router"

import type { PolicyRead } from "@/api"
import {
  createPolicyMutation,
  getPolicyOptions,
  listControlsOptions,
  listPoliciesOptions,
  listUsersOptions,
  updatePolicyMutation,
} from "@/api/@tanstack/react-query.gen"
import {
  Button,
  createDataTableColumns,
  DataTable,
  DetailLayout,
  EmptyState,
  EntityHeader,
  ErrorState,
  Field,
  fieldA11y,
  LoadingState,
  NoAccessState,
  NotFoundState,
  ReadOnlyField,
  SelectInput,
  TextArea,
  TextInput,
  useDetail,
  useDetailParam,
} from "@/components/patterns"
import { problemFieldErrors, problemMessage, problemStatus } from "@/features/applications/problem"
import { invalidateControls } from "@/features/controls/queries"

/** `?policy=new` opens the add form in the detail panel. */
export const NEW_POLICY = "new"
const NONE = "none"

const col = createDataTableColumns<PolicyRead>()
const columns = [
  col.accessor("code", { header: "Code", meta: { mono: true } }),
  col.accessor("name", { header: "Policy" }),
  col.accessor((p) => p.owner?.display_name ?? "Nobody yet", { id: "owner", header: "Owner" }),
  col.accessor("control_count", { header: "Controls", meta: { align: "right", mono: true } }),
]

/** The policies, each a statement of intent that its controls make enforceable (FR-P1). */
export function PolicyList() {
  const [, open] = useDetailParam("policy")
  const query = useQuery(listPoliciesOptions())
  const rows = query.data?.data ?? []
  const canCreate = query.data?.allowed_actions.includes("create_policy") ?? false

  if (query.isError && problemStatus(query.error) === 403) return <NoAccessState requirement="a role that can see policies" />

  return (
    <div className="flex flex-col gap-4 pr-4">
      <div className="flex flex-wrap items-center gap-3">
        {query.data && (
          <span className="mono text-sm text-muted-foreground tabular-nums" aria-live="polite">
            {rows.length} {rows.length === 1 ? "policy" : "policies"}
          </span>
        )}
        {canCreate && (
          <Button className="ml-auto" onClick={() => open(NEW_POLICY)}>
            <PlusIcon aria-hidden="true" />
            Add policy
          </Button>
        )}
      </div>
      <DataTable<PolicyRead>
        label="Policies"
        columns={columns}
        data={rows}
        getRowId={(p) => p.id}
        loading={query.isPending}
        error={query.isError ? { onRetry: () => void query.refetch(), retrying: query.isFetching } : undefined}
        empty={{
          title: "No policies yet",
          description: "A policy states what the organisation commits to. Controls under it make that checkable.",
          action: canCreate ? <Button onClick={() => open(NEW_POLICY)}>Add policy</Button> : undefined,
        }}
        onRowOpen={(p) => open(p.id)}
      />
    </div>
  )
}

export function PolicyDetailView({ id }: { id: string }) {
  const query = useQuery(getPolicyOptions({ path: { policy_id: id } }))
  const [editing, setEditing] = React.useState(false)

  if (query.isPending) return <LoadingState label="Loading policy" />
  if (query.isError) {
    const status = problemStatus(query.error)
    if (status === 404 || status === 422) return <NotFoundState kind="policy" />
    if (status === 403) return <NoAccessState requirement="a role that can see policies" />
    return <ErrorState onRetry={() => void query.refetch()} retrying={query.isFetching} />
  }

  const policy = query.data.data
  const canEdit = query.data.allowed_actions.includes("edit_policy")

  if (editing) {
    return (
      <DetailLayout header={<EntityHeader kind="Edit policy" title={policy.name} identifier={policy.code} />}>
        <PolicyForm policy={policy} onSaved={() => setEditing(false)} onCancel={() => setEditing(false)} />
      </DetailLayout>
    )
  }

  return (
    <DetailLayout
      header={
        <EntityHeader
          kind="Policy"
          title={policy.name}
          identifier={policy.code}
          meta={[
            { label: "Owner", value: policy.owner?.display_name ?? "Nobody yet" },
            { label: "Controls", value: <span className="mono tabular-nums">{policy.control_count}</span> },
          ]}
          actions={
            canEdit && (
              <Button variant="secondary" onClick={() => setEditing(true)}>
                Edit
              </Button>
            )
          }
        />
      }
    >
      <div className="flex flex-col gap-6">
        <ReadOnlyField label="Statement" value={policy.statement} />
        <PolicyControls policyId={policy.id} />
      </div>
    </DetailLayout>
  )
}

function PolicyControls({ policyId }: { policyId: string }) {
  const query = useQuery(listControlsOptions({ query: { policy_id: policyId, limit: 100 } }))
  const rows = query.data?.data ?? []
  return (
    <section aria-labelledby="policy-controls-heading" className="flex flex-col gap-3">
      <h3 id="policy-controls-heading" className="text-base font-semibold">
        Controls
      </h3>
      {query.isPending ? (
        <LoadingState label="Loading controls" />
      ) : query.isError ? (
        <ErrorState onRetry={() => void query.refetch()} retrying={query.isFetching} />
      ) : rows.length === 0 ? (
        <EmptyState title="No controls under this policy" description="Add one from the control library." />
      ) : (
        <ul className="flex flex-col divide-y rounded-md border">
          {rows.map((control) => (
            <li key={control.id} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 text-sm">
              <Link to={`/controls?view=library&control=${control.id}`} className="text-brand underline-offset-4 hover:underline">
                <span className="mono tabular-nums">{control.code}</span> · {control.name}
              </Link>
              <span className="text-xs text-muted-foreground">
                Applied to <span className="mono tabular-nums">{control.applied_count}</span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

/** The add-policy form in the detail panel, at ?policy=new. */
export function NewPolicyView() {
  const { open, close } = useDetail()
  return (
    <DetailLayout header={<EntityHeader kind="Policy" title="Add a policy" />}>
      <PolicyForm onSaved={(policy) => open(policy.id)} onCancel={close} />
    </DetailLayout>
  )
}

function PolicyForm({ policy, onSaved, onCancel }: { policy?: PolicyRead; onSaved: (policy: PolicyRead) => void; onCancel: () => void }) {
  const queryClient = useQueryClient()
  const { setDirty } = useDetail()
  const users = useQuery(listUsersOptions({ query: { role: "governance" } }))
  const create = useMutation(createPolicyMutation())
  const update = useMutation(updatePolicyMutation())
  const editing = policy !== undefined
  const [code, setCode] = React.useState(policy?.code ?? "")
  const [name, setName] = React.useState(policy?.name ?? "")
  const [statement, setStatement] = React.useState(policy?.statement ?? "")
  const [ownerId, setOwnerId] = React.useState(policy?.owner?.id ?? NONE)
  const [errors, setErrors] = React.useState<Record<string, string>>({})
  const [formError, setFormError] = React.useState<string | null>(null)

  const dirty = name !== (policy?.name ?? "") || statement !== (policy?.statement ?? "") || code !== (policy?.code ?? "")
  React.useEffect(() => setDirty(dirty), [dirty, setDirty])
  React.useEffect(() => () => setDirty(false), [setDirty])

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault()
    const next: Record<string, string> = {}
    if (!editing && !/^[A-Za-z0-9][A-Za-z0-9_.-]{1,39}$/.test(code.trim())) next.code = "Use 2 to 40 letters, digits, dots, dashes or underscores, e.g. RET."
    if (!name.trim()) next.name = "Enter a name."
    if (!statement.trim()) next.statement = "Say what the organisation commits to."
    setErrors(next)
    setFormError(null)
    if (Object.keys(next).length > 0) return
    const owner_id = ownerId === NONE ? null : ownerId
    try {
      const saved = editing
        ? await update.mutateAsync({ path: { policy_id: policy.id }, body: { name: name.trim(), statement: statement.trim(), owner_id } })
        : await create.mutateAsync({ body: { code: code.trim(), name: name.trim(), statement: statement.trim(), owner_id } })
      await invalidateControls(queryClient)
      setDirty(false)
      onSaved(saved.data)
    } catch (error) {
      const fields = problemFieldErrors(error)
      if (Object.keys(fields).length > 0) setErrors(fields)
      else setFormError(problemMessage(error))
    }
  }

  return (
    <form aria-label={editing ? `Edit ${policy.name}` : "Add a policy"} className="flex flex-col gap-4" onSubmit={(event) => void onSubmit(event)} noValidate>
      {!editing && (
        <Field label="Code" htmlFor="policy-code" required error={errors.code} hint="Unique and short, e.g. RET.">
          <TextInput
            {...fieldA11y("policy-code", { error: errors.code, hint: "Unique and short, e.g. RET." })}
            className="mono w-48"
            value={code}
            onChange={(event) => setCode(event.target.value)}
          />
        </Field>
      )}
      <Field label="Name" htmlFor="policy-name" required error={errors.name}>
        <TextInput {...fieldA11y("policy-name", { error: errors.name })} value={name} onChange={(event) => setName(event.target.value)} />
      </Field>
      <Field label="Statement" htmlFor="policy-statement" required error={errors.statement} hint="What the organisation commits to.">
        <TextArea
          {...fieldA11y("policy-statement", { error: errors.statement, hint: "What the organisation commits to." })}
          value={statement}
          onChange={(event) => setStatement(event.target.value)}
        />
      </Field>
      <Field label="Owner" htmlFor="policy-owner">
        <SelectInput
          {...fieldA11y("policy-owner", {})}
          options={[{ value: NONE, label: "Nobody yet" }, ...(users.data?.data ?? []).map((u) => ({ value: u.id, label: u.display_name }))]}
          value={ownerId}
          onValueChange={setOwnerId}
        />
      </Field>
      {formError && (
        <p role="alert" className="text-sm text-danger">
          {formError}
        </p>
      )}
      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" loading={create.isPending || update.isPending}>
          {editing ? "Save changes" : "Add policy"}
        </Button>
      </div>
    </form>
  )
}
