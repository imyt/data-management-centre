import { describe, expect, it } from "vitest"

import type { RuleTypeRead, RuleVersionRead, Vocabulary } from "@/api"
import { draftFromVersion, draftProblem, emptyDraft, selectorOf } from "@/features/controls/rule-draft"

const vocabulary: Vocabulary = {
  rule_types: [],
  subject_types: [
    {
      type: "asset",
      label: "Asset",
      attributes: [
        { name: "is_stored", label: "Stored", kind: "boolean", options: [] },
        {
          name: "data_category",
          label: "Data category",
          kind: "choice",
          options: [
            { value: "personal", label: "Personal" },
            { value: "payment", label: "Payment" },
          ],
        },
      ],
    },
  ],
}

describe("rule drafts", () => {
  it("round-trips a stored selector", () => {
    const stored = {
      id: "v1",
      version: 2,
      params: { grace_days: 3 },
      selector: { subject: "asset", where: { is_stored: true, "data_category.in": ["personal", "payment"] } },
    } as unknown as RuleVersionRead
    const draft = draftFromVersion("retention_window", stored)

    expect(draft.conditions).toEqual([
      { attribute: "is_stored", operator: "equals", values: ["yes"] },
      { attribute: "data_category", operator: "in", values: ["personal", "payment"] },
    ])
    expect(selectorOf(draft, vocabulary)).toEqual(stored.selector)
  })

  it("starts a new rule from the rule type's defaults", () => {
    const rule = { key: "harvest_fresh", subjects: ["data_store"], params: [{ name: "max_age_hours", default: 48 }] } as unknown as RuleTypeRead

    expect(emptyDraft(rule)).toEqual({ ruleType: "harvest_fresh", subject: "data_store", params: { max_age_hours: 48 }, conditions: [] })
  })

  it("says what is missing before a rule can be saved", () => {
    const rule = { key: "harvest_fresh", params: [{ name: "max_age_hours", label: "Longest time", kind: "integer", minimum: 1 }] } as unknown as RuleTypeRead
    const base = { ruleType: "harvest_fresh", subject: "asset", params: { max_age_hours: 48 }, conditions: [] }

    expect(draftProblem(base, rule)).toBeNull()
    expect(draftProblem({ ...base, params: { max_age_hours: Number.NaN } }, rule)).toMatch(/whole number/)
    expect(draftProblem({ ...base, conditions: [{ attribute: "data_category", operator: "in", values: [] }] }, rule)).toMatch(/value for every condition/)
  })
})
