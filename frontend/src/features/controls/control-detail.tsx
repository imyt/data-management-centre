import * as React from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Link } from "react-router"

import type { AppliedControlRead, ControlDetail, RuleVersionRead, SelectorPreview, SubjectType } from "@/api"
import {
  getControlOptions,
  getPolicyVocabularyOptions,
  listAppliedControlsOptions,
  publishRuleVersionMutation,
  retireControlMutation,
} from "@/api/@tanstack/react-query.gen"
import {
  Button,
  ConfirmWithReason,
  DetailLayout,
  EmptyState,
  EntityHeader,
  ErrorState,
  ExplainWhy,
  LoadingState,
  NoAccessState,
  NotFoundState,
  ReadOnlyField,
  StatusBadge,
  useDetail,
} from "@/components/patterns"
import { problemMessage, problemStatus } from "@/features/applications/problem"
import { ControlForm, ControlMetaForm } from "@/features/controls/control-form"
import { subjectLabel, subjectPath, SUBJECT_TYPE_PLURAL } from "@/features/controls/labels"
import { invalidateControlsSoon } from "@/features/controls/queries"
import { draftFromVersion, draftProblem, selectorOf, type RuleDraft } from "@/features/controls/rule-draft"
import { RuleEditor } from "@/features/controls/rule-editor"
import { formatTimestamp } from "@/lib/format"

type Mode = "view" | "meta" | "rule"

function when(value: string) {
  const date = new Date(value)
  return (
    <time dateTime={date.toISOString()} title={date.toISOString()} className="mono tabular-nums">
      {formatTimestamp(date)}
    </time>
  )
}

/** One control in the detail panel: its rule, what it applies to, and the versions behind it. */
export function ControlDetailView({ id }: { id: string }) {
  const query = useQuery(getControlOptions({ path: { control_id: id } }))
  const [mode, setMode] = React.useState<Mode>("view")

  if (query.isPending) return <LoadingState label="Loading control" />
  if (query.isError) {
    const status = problemStatus(query.error)
    if (status === 404 || status === 422) return <NotFoundState kind="control" />
    if (status === 403) return <NoAccessState requirement="a role that can see controls" />
    return <ErrorState onRetry={() => void query.refetch()} retrying={query.isFetching} />
  }

  const control = query.data.data
  const actions = query.data.allowed_actions

  if (mode === "meta") {
    return (
      <DetailLayout header={<EntityHeader kind="Edit control" title={control.name} identifier={control.code} />}>
        <ControlMetaForm control={control} onSaved={() => setMode("view")} onCancel={() => setMode("view")} />
      </DetailLayout>
    )
  }

  if (mode === "rule") {
    return (
      <DetailLayout header={<EntityHeader kind="New rule version" title={control.name} identifier={control.code} />}>
        <NewVersionForm control={control} onDone={() => setMode("view")} />
      </DetailLayout>
    )
  }

  return (
    <DetailLayout
      header={
        <ControlHeader control={control} actions={actions} onEdit={() => setMode("meta")} onNewVersion={() => setMode("rule")} />
      }
    >
      <div className="flex flex-col gap-6">
        {control.status === "retired" && (
          <p role="status" className="rounded-md bg-subtle px-3 py-2 text-sm">
            Retired: {control.retired_reason}
          </p>
        )}
        <RuleSection control={control} />
        <AppliedSection control={control} />
        <VersionsSection control={control} />
      </div>
    </DetailLayout>
  )
}

function ControlHeader({
  control,
  actions,
  onEdit,
  onNewVersion,
}: {
  control: ControlDetail
  actions: string[]
  onEdit: () => void
  onNewVersion: () => void
}) {
  const [retiring, setRetiring] = React.useState(false)
  const queryClient = useQueryClient()
  const retire = useMutation(retireControlMutation())

  async function onRetire(reason: string) {
    try {
      await retire.mutateAsync({ path: { control_id: control.id }, body: { reason } })
    } catch (e) {
      throw new Error(problemMessage(e))
    }
    await invalidateControlsSoon(queryClient)
  }

  return (
    <>
      <EntityHeader
        kind="Control"
        title={control.name}
        identifier={control.code}
        status={control.status === "retired" ? "not_applicable" : undefined}
        meta={[
          { label: "Policy", value: `${control.policy.code} · ${control.policy.name}` },
          { label: "Rule type", value: control.rule_type_label },
          { label: "Owner", value: control.control_owner?.display_name ?? "Nobody yet" },
          { label: "Applied to", value: <span className="mono tabular-nums">{control.applied_count}</span> },
        ]}
        actions={
          <>
            {actions.includes("retire") && (
              <Button variant="ghost" onClick={() => setRetiring(true)}>
                Retire
              </Button>
            )}
            {actions.includes("edit") && (
              <Button variant="secondary" onClick={onEdit}>
                Edit
              </Button>
            )}
            {actions.includes("publish_rule_version") && <Button onClick={onNewVersion}>New rule version</Button>}
          </>
        }
      />
      <ConfirmWithReason
        open={retiring}
        onOpenChange={setRetiring}
        title={`Retire ${control.code}`}
        description="A retired control stops applying. Its applied controls are kept as history."
        impact={
          <>
            <span className="mono tabular-nums">{control.applied_count}</span> applied controls will be retired.
          </>
        }
        confirmLabel="Retire control"
        destructive
        onConfirm={onRetire}
      />
    </>
  )
}

function RuleSection({ control }: { control: ControlDetail }) {
  const version = control.current_version
  const params = Object.entries(version.params)
  return (
    <section aria-labelledby="rule-heading" className="flex flex-col gap-3">
      <h3 id="rule-heading" className="text-base font-semibold">
        Rule <span className="mono text-sm font-normal text-muted-foreground tabular-nums">version {version.version}</span>
      </h3>
      {control.description && <p className="text-sm">{control.description}</p>}
      <div>
        <p className="text-xs text-muted-foreground">Applies to every {subjectLabel(control.subject_type).toLowerCase()} where</p>
        {version.conditions.length === 0 ? (
          <p className="text-sm">There are no conditions: all {SUBJECT_TYPE_PLURAL[control.subject_type as SubjectType] ?? "subjects"}.</p>
        ) : (
          <ul className="mt-1 flex flex-col gap-1">
            {version.conditions.map((condition) => (
              <li key={condition.attribute} className="text-sm">
                {condition.text}
              </li>
            ))}
          </ul>
        )}
      </div>
      {params.length > 0 && (
        <dl className="flex flex-wrap gap-x-6 gap-y-2">
          {params.map(([name, value]) => (
            <div key={name}>
              <dt className="text-xs text-muted-foreground">{name.replaceAll("_", " ")}</dt>
              <dd className="mono text-sm tabular-nums">{Array.isArray(value) ? value.join(", ") : String(value)}</dd>
            </div>
          ))}
        </dl>
      )}
      <ReadOnlyField label="Evidence requirement" value={control.evidence_requirement ?? "Not set"} />
    </section>
  )
}

function AppliedSection({ control }: { control: ControlDetail }) {
  const query = useQuery(listAppliedControlsOptions({ query: { control_id: control.id, limit: 100 } }))
  const rows = query.data?.data ?? []
  return (
    <section aria-labelledby="applied-heading" className="flex flex-col gap-3">
      <h3 id="applied-heading" className="text-base font-semibold">
        Applied controls
      </h3>
      {query.isPending ? (
        <LoadingState label="Loading applied controls" />
      ) : query.isError ? (
        <ErrorState onRetry={() => void query.refetch()} retrying={query.isFetching} />
      ) : rows.length === 0 ? (
        <EmptyState
          title="Nothing is selected yet"
          description={
            control.status === "retired"
              ? "A retired control applies to nothing."
              : "No subject has these attributes. A matching one gets this control as soon as it appears."
          }
        />
      ) : (
        <>
          <ul className="flex flex-col divide-y rounded-md border">
            {rows.map((applied) => (
              <li key={applied.id} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
                <AppliedRow applied={applied} />
              </li>
            ))}
          </ul>
          {(query.data?.meta.total ?? 0) > rows.length && (
            <p className="text-xs text-muted-foreground">
              Showing <span className="mono tabular-nums">{rows.length}</span> of <span className="mono tabular-nums">{query.data?.meta.total}</span>.
            </p>
          )}
        </>
      )}
    </section>
  )
}

/** A subject with the control: where it is, who is accountable, and why it applies. */
export function AppliedRow({ applied, showControl = false }: { applied: AppliedControlRead; showControl?: boolean }) {
  const path = subjectPath(applied.subject.type, applied.subject.id)
  return (
    <>
      <div className="flex min-w-0 flex-col gap-0.5">
        <span className="flex flex-wrap items-center gap-2 text-sm">
          {path ? (
            <Link to={path} className="font-medium text-brand underline-offset-4 hover:underline">
              {applied.subject.name}
            </Link>
          ) : (
            <span className="font-medium">{applied.subject.name}</span>
          )}
          <span className="text-xs text-muted-foreground">{subjectLabel(applied.subject.type)}</span>
        </span>
        <span className="text-xs text-muted-foreground">
          {showControl && (
            <>
              <span className="mono tabular-nums">{applied.control.code}</span> · {applied.control.name} ·{" "}
            </>
          )}
          Accountable: {applied.accountable?.display_name ?? "nobody yet"}
        </span>
      </div>
      <span className="flex items-center gap-3">
        <StatusBadge status="pending" label="Not evaluated yet" size="sm" />
        <ExplainWhy
          reason={applied.reason}
          sources={[{ label: `${applied.control.code}, rule version ${applied.rule_version}` }]}
        />
      </span>
    </>
  )
}

function VersionsSection({ control }: { control: ControlDetail }) {
  return (
    <section aria-labelledby="versions-heading" className="flex flex-col gap-3">
      <h3 id="versions-heading" className="text-base font-semibold">
        Version history
      </h3>
      <ol className="flex flex-col gap-3">
        {control.versions.map((version) => (
          <VersionRow key={version.id} version={version} current={version.version === control.current_version.version} />
        ))}
      </ol>
    </section>
  )
}

function VersionRow({ version, current }: { version: RuleVersionRead; current: boolean }) {
  return (
    <li className="rounded-md border p-3">
      <p className="flex flex-wrap items-center gap-2 text-sm">
        <span className="mono font-medium tabular-nums">Version {version.version}</span>
        {current && <span className="text-xs text-muted-foreground">current</span>}
        <span className="text-xs text-muted-foreground">
          {when(version.created_at)}
          {version.created_by && <> · {version.created_by.display_name}</>}
        </span>
      </p>
      <p className="mt-1 text-sm text-muted-foreground">
        {version.conditions.length === 0 ? "No conditions" : version.conditions.map((c) => c.text).join("; ")}
      </p>
      {version.change_reason && <p className="mt-1 text-sm">Reason: {version.change_reason}</p>}
    </li>
  )
}

/** Edit the current rule; publishing needs a reason, because a looser rule is a risk decision. */
function NewVersionForm({ control, onDone }: { control: ControlDetail; onDone: () => void }) {
  const queryClient = useQueryClient()
  const { setDirty } = useDetail()
  const vocabulary = useQuery(getPolicyVocabularyOptions())
  const publish = useMutation(publishRuleVersionMutation())
  const initial = React.useMemo(() => draftFromVersion(control.rule_type, control.current_version), [control])
  const [draft, setDraft] = React.useState<RuleDraft>(initial)
  const [preview, setPreview] = React.useState<SelectorPreview | null>(null)
  const [confirming, setConfirming] = React.useState(false)

  const vocab = vocabulary.data?.data
  const changed = vocab !== undefined && JSON.stringify([selectorOf(draft, vocab), draft.params]) !== JSON.stringify([selectorOf(initial, vocab), initial.params])
  React.useEffect(() => setDirty(changed), [changed, setDirty])
  React.useEffect(() => () => setDirty(false), [setDirty])

  if (vocabulary.isPending) return <LoadingState label="Loading the rule editor" />
  if (vocabulary.isError || !vocab) return <ErrorState onRetry={() => void vocabulary.refetch()} retrying={vocabulary.isFetching} />

  const problem = draftProblem(draft, vocab.rule_types.find((r) => r.key === draft.ruleType))

  async function onPublish(reason: string) {
    if (!vocab) return
    try {
      await publish.mutateAsync({
        path: { control_id: control.id },
        body: { params: draft.params, selector: selectorOf(draft, vocab), reason },
      })
    } catch (e) {
      throw new Error(problemMessage(e))
    }
    await invalidateControlsSoon(queryClient)
    setDirty(false)
    onDone()
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted-foreground">
        Version <span className="mono tabular-nums">{control.current_version.version + 1}</span> replaces version{" "}
        <span className="mono tabular-nums">{control.current_version.version}</span> for every subject. Earlier results stay explained by the
        version that produced them.
      </p>
      <RuleEditor draft={draft} onChange={setDraft} vocabulary={vocab} lockRuleType onPreview={setPreview} />
      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="ghost" onClick={onDone}>
          Cancel
        </Button>
        <Button
          onClick={() => setConfirming(true)}
          disabled={!changed || problem !== null}
          disabledReason={problem ?? (changed ? undefined : "Change the rule first.")}
        >
          Publish version {control.current_version.version + 1}
        </Button>
      </div>
      <ConfirmWithReason
        open={confirming}
        onOpenChange={setConfirming}
        title={`Publish version ${control.current_version.version + 1} of ${control.code}`}
        description="Say why the rule changes. The reason is recorded in the audit trail."
        impact={
          preview ? (
            <>
              Applies to <span className="mono tabular-nums">{preview.count}</span> of <span className="mono tabular-nums">{preview.total}</span>{" "}
              {SUBJECT_TYPE_PLURAL[draft.subject as SubjectType] ?? "subjects"} (now{" "}
              <span className="mono tabular-nums">{control.applied_count}</span>). Applied controls are recomputed.
            </>
          ) : (
            "Applied controls are recomputed."
          )
        }
        confirmLabel="Publish version"
        onConfirm={onPublish}
      />
    </div>
  )
}

/** The add-control form in the detail panel, at ?control=new. */
export function NewControlView() {
  const { open, close } = useDetail()
  return (
    <DetailLayout header={<EntityHeader kind="Control" title="Add a control" />}>
      <ControlForm onSaved={(control) => open(control.id)} onCancel={close} />
    </DetailLayout>
  )
}
