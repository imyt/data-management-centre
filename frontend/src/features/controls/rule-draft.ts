import type { RuleTypeRead, RuleVersionRead, SelectorBody, Vocabulary } from "@/api"
import type { Operator } from "@/features/controls/labels"

export interface ConditionDraft {
  attribute: string
  operator: Operator
  /** Option values; "yes" or "no" for a yes/no attribute. */
  values: string[]
}

export type ParamValue = number | string[]

export interface RuleDraft {
  ruleType: string
  subject: string
  params: Record<string, ParamValue>
  conditions: ConditionDraft[]
}

const SUFFIXES: [string, Operator][] = [
  [".not_in", "not_in"],
  [".in", "in"],
]

/** The draft a stored rule version starts from, so a new version edits the current one. */
export function draftFromVersion(ruleType: string, version: RuleVersionRead): RuleDraft {
  const conditions = Object.entries(version.selector.where ?? {}).map(([key, value]): ConditionDraft => {
    const suffix = SUFFIXES.find(([s]) => key.endsWith(s))
    const attribute = suffix ? key.slice(0, -suffix[0].length) : key
    if (typeof value === "boolean") return { attribute, operator: "equals", values: [value ? "yes" : "no"] }
    return { attribute, operator: suffix ? suffix[1] : "equals", values: Array.isArray(value) ? value : [value] }
  })
  return { ruleType, subject: version.selector.subject, params: version.params as Record<string, ParamValue>, conditions }
}

export function emptyDraft(rule: RuleTypeRead): RuleDraft {
  return {
    ruleType: rule.key,
    subject: rule.subjects[0] ?? "asset",
    params: Object.fromEntries(rule.params.map((p) => [p.name, p.default])),
    conditions: [],
  }
}

export function selectorOf(draft: RuleDraft, vocabulary: Vocabulary): SelectorBody {
  const attributes = vocabulary.subject_types.find((s) => s.type === draft.subject)?.attributes ?? []
  const where: Record<string, boolean | string | string[]> = {}
  for (const c of draft.conditions) {
    const spec = attributes.find((a) => a.name === c.attribute)
    if (spec?.kind === "boolean") where[c.attribute] = c.values[0] === "yes"
    else if (c.operator === "equals") where[c.attribute] = c.values[0] ?? ""
    else where[`${c.attribute}.${c.operator}`] = c.values
  }
  return { subject: draft.subject, where }
}

/** Why a draft cannot be saved yet, in a sentence; null when it can. */
export function draftProblem(draft: RuleDraft, rule: RuleTypeRead | undefined): string | null {
  if (!rule) return "Choose a rule type."
  for (const spec of rule.params) {
    const value = draft.params[spec.name]
    if (spec.kind === "integer" && !(typeof value === "number" && Number.isInteger(value) && value >= spec.minimum)) {
      return `${spec.label} must be a whole number of at least ${spec.minimum}.`
    }
    if (spec.kind === "choices" && !(Array.isArray(value) && value.length > 0)) return `Choose at least one: ${spec.label.toLowerCase()}.`
  }
  if (draft.conditions.some((c) => c.values.length === 0)) return "Choose a value for every condition."
  return null
}
