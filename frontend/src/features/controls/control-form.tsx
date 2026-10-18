import * as React from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import type { ControlDetail } from "@/api"
import {
  createControlMutation,
  getPolicyVocabularyOptions,
  listPoliciesOptions,
  listUsersOptions,
  updateControlMutation,
} from "@/api/@tanstack/react-query.gen"
import {
  Button,
  ErrorState,
  Field,
  fieldA11y,
  LoadingState,
  SelectInput,
  TextArea,
  TextInput,
  useDetail,
} from "@/components/patterns"
import { problemFieldErrors, problemMessage } from "@/features/applications/problem"
import { draftProblem, emptyDraft, selectorOf, type RuleDraft } from "@/features/controls/rule-draft"
import { RuleEditor } from "@/features/controls/rule-editor"
import { invalidateControlsSoon } from "@/features/controls/queries"

const NONE = "none"

function useGovernanceUsers() {
  const users = useQuery(listUsersOptions({ query: { role: "governance" } }))
  return [{ value: NONE, label: "Nobody yet" }, ...(users.data?.data ?? []).map((u) => ({ value: u.id, label: u.display_name }))]
}

/** Add a control to the library: its policy, details and first rule version (FR-P1). */
export function ControlForm({ onSaved, onCancel }: { onSaved: (control: ControlDetail) => void; onCancel: () => void }) {
  const queryClient = useQueryClient()
  const { setDirty } = useDetail()
  const vocabulary = useQuery(getPolicyVocabularyOptions())
  const policies = useQuery(listPoliciesOptions())
  const owners = useGovernanceUsers()
  const create = useMutation(createControlMutation())

  const [policyId, setPolicyId] = React.useState("")
  const [code, setCode] = React.useState("")
  const [name, setName] = React.useState("")
  const [description, setDescription] = React.useState("")
  const [evidence, setEvidence] = React.useState("")
  const [ownerId, setOwnerId] = React.useState(NONE)
  const [draft, setDraft] = React.useState<RuleDraft | null>(null)
  const [errors, setErrors] = React.useState<Record<string, string>>({})
  const [formError, setFormError] = React.useState<string | null>(null)

  const vocab = vocabulary.data?.data
  const active = draft ?? (vocab?.rule_types[0] ? emptyDraft(vocab.rule_types[0]) : null)

  React.useEffect(() => setDirty(Boolean(code || name || description || evidence)), [code, name, description, evidence, setDirty])
  React.useEffect(() => () => setDirty(false), [setDirty])

  if (vocabulary.isPending || policies.isPending) return <LoadingState label="Loading the control form" />
  if (vocabulary.isError || policies.isError || !vocab || !active) {
    return <ErrorState onRetry={() => void vocabulary.refetch()} retrying={vocabulary.isFetching} />
  }

  const rule = vocab.rule_types.find((r) => r.key === active.ruleType)

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (!vocab || !active) return
    const next: Record<string, string> = {}
    if (!policyId) next.policy_id = "Choose a policy."
    if (!/^[A-Za-z0-9][A-Za-z0-9_.-]{1,39}$/.test(code.trim())) next.code = "Use 2 to 40 letters, digits, dots, dashes or underscores, e.g. RET-02."
    if (!name.trim()) next.name = "Enter a name."
    const problem = draftProblem(active, rule)
    setErrors(next)
    setFormError(problem)
    if (Object.keys(next).length > 0 || problem) return
    try {
      const saved = await create.mutateAsync({
        body: {
          policy_id: policyId,
          code: code.trim(),
          name: name.trim(),
          description: description.trim() || null,
          evidence_requirement: evidence.trim() || null,
          control_owner_id: ownerId === NONE ? null : ownerId,
          rule_type: active.ruleType,
          params: active.params,
          selector: selectorOf(active, vocab),
        },
      })
      await invalidateControlsSoon(queryClient)
      setDirty(false)
      onSaved(saved.data)
    } catch (error) {
      const fields = problemFieldErrors(error)
      if (Object.keys(fields).length > 0) setErrors(fields)
      else setFormError(problemMessage(error))
    }
  }

  return (
    <form aria-label="Add a control" className="flex flex-col gap-4" onSubmit={(event) => void onSubmit(event)} noValidate>
      <Field label="Policy" htmlFor="control-policy" required error={errors.policy_id}>
        <SelectInput
          {...fieldA11y("control-policy", { error: errors.policy_id })}
          options={(policies.data?.data ?? []).map((p) => ({ value: p.id, label: `${p.code} · ${p.name}` }))}
          value={policyId}
          onValueChange={setPolicyId}
          placeholder="Choose a policy"
        />
      </Field>
      <Field label="Code" htmlFor="control-code" required error={errors.code} hint="Unique and short, e.g. RET-02.">
        <TextInput
          {...fieldA11y("control-code", { error: errors.code, hint: "Unique and short, e.g. RET-02." })}
          className="mono w-48"
          value={code}
          onChange={(event) => setCode(event.target.value)}
        />
      </Field>
      <Field label="Name" htmlFor="control-name" required error={errors.name}>
        <TextInput {...fieldA11y("control-name", { error: errors.name })} value={name} onChange={(event) => setName(event.target.value)} />
      </Field>
      <Field label="Description" htmlFor="control-description" error={errors.description}>
        <TextArea {...fieldA11y("control-description", { error: errors.description })} value={description} onChange={(event) => setDescription(event.target.value)} />
      </Field>
      <Field label="Evidence requirement" htmlFor="control-evidence" hint="What shows the control is met.">
        <TextArea
          {...fieldA11y("control-evidence", { hint: "What shows the control is met." })}
          value={evidence}
          onChange={(event) => setEvidence(event.target.value)}
        />
      </Field>
      <Field label="Control owner" htmlFor="control-owner">
        <SelectInput {...fieldA11y("control-owner", {})} options={owners} value={ownerId} onValueChange={setOwnerId} />
      </Field>

      <h3 className="pt-2 text-base font-semibold">Rule</h3>
      <RuleEditor draft={active} onChange={setDraft} vocabulary={vocab} />

      {formError && (
        <p role="alert" className="text-sm text-danger">
          {formError}
        </p>
      )}
      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" loading={create.isPending}>
          Add control
        </Button>
      </div>
    </form>
  )
}

/** Name, description, owner and evidence requirement. The rule changes through a new version. */
export function ControlMetaForm({ control, onSaved, onCancel }: { control: ControlDetail; onSaved: () => void; onCancel: () => void }) {
  const queryClient = useQueryClient()
  const { setDirty } = useDetail()
  const owners = useGovernanceUsers()
  const update = useMutation(updateControlMutation())
  const [name, setName] = React.useState(control.name)
  const [description, setDescription] = React.useState(control.description ?? "")
  const [evidence, setEvidence] = React.useState(control.evidence_requirement ?? "")
  const [ownerId, setOwnerId] = React.useState(control.control_owner?.id ?? NONE)
  const [error, setError] = React.useState<string | null>(null)

  const dirty = name !== control.name || description !== (control.description ?? "") || evidence !== (control.evidence_requirement ?? "")
  React.useEffect(() => setDirty(dirty), [dirty, setDirty])
  React.useEffect(() => () => setDirty(false), [setDirty])

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (!name.trim()) {
      setError("Enter a name.")
      return
    }
    try {
      await update.mutateAsync({
        path: { control_id: control.id },
        body: {
          name: name.trim(),
          description: description.trim() || null,
          evidence_requirement: evidence.trim() || null,
          control_owner_id: ownerId === NONE ? null : ownerId,
        },
      })
      await invalidateControlsSoon(queryClient)
      setDirty(false)
      onSaved()
    } catch (e) {
      setError(problemMessage(e))
    }
  }

  return (
    <form aria-label={`Edit ${control.code}`} className="flex flex-col gap-4" onSubmit={(event) => void onSubmit(event)} noValidate>
      <Field label="Name" htmlFor="meta-name" required>
        <TextInput {...fieldA11y("meta-name", {})} value={name} onChange={(event) => setName(event.target.value)} />
      </Field>
      <Field label="Description" htmlFor="meta-description">
        <TextArea {...fieldA11y("meta-description", {})} value={description} onChange={(event) => setDescription(event.target.value)} />
      </Field>
      <Field label="Evidence requirement" htmlFor="meta-evidence">
        <TextArea {...fieldA11y("meta-evidence", {})} value={evidence} onChange={(event) => setEvidence(event.target.value)} />
      </Field>
      <Field label="Control owner" htmlFor="meta-owner">
        <SelectInput {...fieldA11y("meta-owner", {})} options={owners} value={ownerId} onValueChange={setOwnerId} />
      </Field>
      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}
      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" loading={update.isPending}>
          Save changes
        </Button>
      </div>
    </form>
  )
}
