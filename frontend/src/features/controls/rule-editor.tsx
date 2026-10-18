import * as React from "react"
import { useMutation } from "@tanstack/react-query"
import { PlusIcon, XIcon } from "lucide-react"

import type { AttributeRead, RuleTypeRead, SelectorBody, SelectorPreview, SubjectType, Vocabulary } from "@/api"
import { previewSelectorMutation } from "@/api/@tanstack/react-query.gen"
import { Button, Field, fieldA11y, SelectInput, TextInput } from "@/components/patterns"
import { OPERATOR, SUBJECT_TYPE, SUBJECT_TYPE_PLURAL, type Operator } from "@/features/controls/labels"
import { emptyDraft, selectorOf, type ConditionDraft, type ParamValue, type RuleDraft } from "@/features/controls/rule-draft"

interface RuleEditorProps {
  draft: RuleDraft
  onChange: (draft: RuleDraft) => void
  vocabulary: Vocabulary
  /** The rule type is fixed once a control exists. */
  lockRuleType?: boolean
  /** Reports what the selector matches now, for the caller to show in a confirmation. */
  onPreview?: (preview: SelectorPreview | null) => void
}

/** The rule of a control: what it checks, its parameters, and the attributes it applies to (FR-P2). */
export function RuleEditor({ draft, onChange, vocabulary, lockRuleType = false, onPreview }: RuleEditorProps) {
  const rule = vocabulary.rule_types.find((r) => r.key === draft.ruleType)
  const subject = vocabulary.subject_types.find((s) => s.type === draft.subject)
  const attributes = subject?.attributes ?? []
  const used = new Set(draft.conditions.map((c) => c.attribute))
  const free = attributes.filter((a) => !used.has(a.name))

  function setRuleType(key: string) {
    const next = vocabulary.rule_types.find((r) => r.key === key)
    if (next) onChange(emptyDraft(next))
  }

  function setCondition(index: number, next: ConditionDraft) {
    onChange({ ...draft, conditions: draft.conditions.map((c, i) => (i === index ? next : c)) })
  }

  function addCondition() {
    const attribute = free[0]
    if (!attribute) return
    const operator: Operator = attribute.kind === "boolean" ? "equals" : "in"
    onChange({ ...draft, conditions: [...draft.conditions, { attribute: attribute.name, operator, values: attribute.kind === "boolean" ? ["yes"] : [] }] })
  }

  return (
    <div className="flex flex-col gap-4">
      <Field label="Rule type" htmlFor="rule-type" required hint={rule?.description}>
        <SelectInput
          {...fieldA11y("rule-type", { hint: rule?.description })}
          options={vocabulary.rule_types.map((r) => ({ value: r.key, label: r.label }))}
          value={draft.ruleType}
          onValueChange={setRuleType}
          disabled={lockRuleType}
        />
      </Field>

      {rule?.params.map((spec) => (
        <ParamField
          key={spec.name}
          spec={spec}
          value={draft.params[spec.name]}
          onChange={(value) => onChange({ ...draft, params: { ...draft.params, [spec.name]: value } })}
        />
      ))}

      <fieldset className="flex flex-col gap-3">
        <legend className="text-sm font-medium">Applies to</legend>
        <p className="text-xs text-text-tertiary">
          Controls apply by attribute, never by name: every {SUBJECT_TYPE[draft.subject as SubjectType]?.toLowerCase() ?? "subject"} with these
          attributes gets the control, now and when new ones appear.
        </p>
        {rule && rule.subjects.length > 1 && (
          <Field label="Kind of subject" htmlFor="rule-subject" required>
            <SelectInput
              {...fieldA11y("rule-subject", {})}
              options={rule.subjects.map((s) => ({ value: s, label: SUBJECT_TYPE[s as SubjectType] ?? s }))}
              value={draft.subject}
              onValueChange={(value) => onChange({ ...draft, subject: value, conditions: [] })}
            />
          </Field>
        )}
        <ul className="flex flex-col gap-2">
          {draft.conditions.map((condition, index) => (
            <li key={condition.attribute} className="rounded-md border bg-surface p-3">
              <ConditionRow
                condition={condition}
                index={index}
                attributes={attributes}
                available={free}
                onChange={(next) => setCondition(index, next)}
                onRemove={() => onChange({ ...draft, conditions: draft.conditions.filter((_, i) => i !== index) })}
              />
            </li>
          ))}
        </ul>
        {draft.conditions.length === 0 && (
          <p className="text-sm text-text-tertiary">No conditions: the control applies to every {SUBJECT_TYPE[draft.subject as SubjectType]?.toLowerCase() ?? "subject"}.</p>
        )}
        <Button type="button" variant="secondary" size="sm" className="self-start" onClick={addCondition} disabled={free.length === 0}>
          <PlusIcon aria-hidden="true" />
          Add condition
        </Button>
      </fieldset>

      <SelectorPreviewLine draft={draft} vocabulary={vocabulary} onPreview={onPreview} />
    </div>
  )
}

function ParamField({
  spec,
  value,
  onChange,
}: {
  spec: RuleTypeRead["params"][number]
  value: ParamValue | undefined
  onChange: (value: ParamValue) => void
}) {
  const id = `param-${spec.name}`
  if (spec.kind === "integer") {
    return (
      <Field label={spec.label} htmlFor={id} required>
        <TextInput
          {...fieldA11y(id, {})}
          type="number"
          min={spec.minimum}
          className="w-32 tabular-nums"
          value={typeof value === "number" ? value : ""}
          onChange={(event) => onChange(event.target.value === "" ? Number.NaN : Number(event.target.value))}
        />
      </Field>
    )
  }
  const chosen = Array.isArray(value) ? value : []
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="text-sm font-medium">{spec.label}</legend>
      <div className="flex flex-wrap gap-x-4 gap-y-2">
        {spec.choices.map((choice) => (
          <CheckOption
            key={choice}
            label={choice.replaceAll("_", " ")}
            checked={chosen.includes(choice)}
            onChange={(on) => onChange(on ? [...chosen, choice] : chosen.filter((c) => c !== choice))}
          />
        ))}
      </div>
    </fieldset>
  )
}

function CheckOption({ label, checked, onChange }: { label: string; checked: boolean; onChange: (checked: boolean) => void }) {
  return (
    <label className="flex cursor-pointer items-center gap-2 text-sm">
      <input type="checkbox" className="size-4 accent-brand" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      <span className="first-letter:uppercase">{label}</span>
    </label>
  )
}

function ConditionRow({
  condition,
  index,
  attributes,
  available,
  onChange,
  onRemove,
}: {
  condition: ConditionDraft
  index: number
  attributes: AttributeRead[]
  available: AttributeRead[]
  onChange: (condition: ConditionDraft) => void
  onRemove: () => void
}) {
  const spec = attributes.find((a) => a.name === condition.attribute)
  const id = `condition-${index}`
  // The attribute being edited stays selectable, plus those not yet used.
  const choices = spec ? [spec, ...available] : available

  function setAttribute(name: string) {
    const next = attributes.find((a) => a.name === name)
    if (!next) return
    if (next.kind === "boolean") onChange({ attribute: name, operator: "equals", values: ["yes"] })
    else onChange({ attribute: name, operator: "in", values: [] })
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-end gap-3">
        <Field label="Attribute" htmlFor={`${id}-attribute`} required className="w-56">
          <SelectInput
            {...fieldA11y(`${id}-attribute`, {})}
            options={choices.map((a) => ({ value: a.name, label: a.label }))}
            value={condition.attribute}
            onValueChange={setAttribute}
          />
        </Field>
        {spec?.kind === "choice" && (
          <Field label="Condition" htmlFor={`${id}-operator`} required className="w-40">
            <SelectInput
              {...fieldA11y(`${id}-operator`, {})}
              options={(["in", "not_in", "equals"] as Operator[]).map((o) => ({ value: o, label: OPERATOR[o] }))}
              value={condition.operator}
              onValueChange={(operator) => onChange({ ...condition, operator: operator as Operator, values: operator === "equals" ? condition.values.slice(0, 1) : condition.values })}
            />
          </Field>
        )}
        {spec?.kind === "boolean" && (
          <Field label="Value" htmlFor={`${id}-value`} required className="w-32">
            <SelectInput
              {...fieldA11y(`${id}-value`, {})}
              options={[
                { value: "yes", label: "Yes" },
                { value: "no", label: "No" },
              ]}
              value={condition.values[0]}
              onValueChange={(value) => onChange({ ...condition, values: [value] })}
            />
          </Field>
        )}
        {spec?.kind === "choice" && condition.operator === "equals" && (
          <Field label="Value" htmlFor={`${id}-value`} required className="w-48">
            <SelectInput
              {...fieldA11y(`${id}-value`, {})}
              options={spec.options.map((o) => ({ value: o.value, label: o.label }))}
              value={condition.values[0]}
              onValueChange={(value) => onChange({ ...condition, values: [value] })}
              placeholder="Choose"
            />
          </Field>
        )}
        <Button type="button" variant="ghost" size="sm" onClick={onRemove} aria-label={`Remove condition ${index + 1}`}>
          <XIcon aria-hidden="true" />
          Remove
        </Button>
      </div>
      {spec?.kind === "choice" && condition.operator !== "equals" && (
        <fieldset className="flex flex-wrap gap-x-4 gap-y-2">
          <legend className="sr-only">{spec.label} values</legend>
          {spec.options.map((option) => (
            <CheckOption
              key={option.value}
              label={option.label}
              checked={condition.values.includes(option.value)}
              onChange={(on) =>
                onChange({ ...condition, values: on ? [...condition.values, option.value] : condition.values.filter((v) => v !== option.value) })
              }
            />
          ))}
        </fieldset>
      )}
    </div>
  )
}

/** What the selector matches right now, so a rule is checked before it is saved. */
function SelectorPreviewLine({
  draft,
  vocabulary,
  onPreview,
}: {
  draft: RuleDraft
  vocabulary: Vocabulary
  onPreview?: (preview: SelectorPreview | null) => void
}) {
  const preview = useMutation(previewSelectorMutation())
  const selector = React.useMemo(() => selectorOf(draft, vocabulary), [draft, vocabulary])
  const complete = draft.conditions.every((c) => c.values.length > 0)
  const key = JSON.stringify(selector)
  const { mutate, reset } = preview

  React.useEffect(() => {
    if (!complete) {
      reset()
      onPreview?.(null)
      return
    }
    const timer = window.setTimeout(() => mutate({ body: { selector: JSON.parse(key) as SelectorBody } }, { onSuccess: (r) => onPreview?.(r.data) }), 300)
    return () => window.clearTimeout(timer)
    // onPreview is a state setter in callers; the selector key is what should trigger a new count.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, complete, mutate, reset])

  const data = preview.data?.data
  const noun = SUBJECT_TYPE_PLURAL[draft.subject as SubjectType] ?? "subjects"
  return (
    <p aria-live="polite" className="rounded-md bg-subtle px-3 py-2 text-sm">
      {preview.isError ? (
        "Couldn’t count what this matches."
      ) : data ? (
        <>
          Matches <span className="mono tabular-nums">{data.count}</span> of <span className="mono tabular-nums">{data.total}</span> {noun} now
          {data.sample.length > 0 && <>: {data.sample.join(", ")}{data.count > data.sample.length ? ", …" : ""}</>}.
        </>
      ) : (
        "Counting what this matches…"
      )}
    </p>
  )
}
