import type { EvaluationResultRead } from "@/api"
import { formatTimestamp } from "@/lib/format"

export interface FactRow {
  label: string
  value: string
}

type Dict = Record<string, unknown>

function dict(value: unknown): Dict {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? (value as Dict) : {}
}

function text(value: unknown): string | null {
  return typeof value === "string" && value !== "" ? value : null
}

function when(value: unknown): string | null {
  const raw = text(value)
  return raw ? formatTimestamp(new Date(raw)) : null
}

function compact(rows: Array<FactRow | null>): FactRow[] {
  return rows.filter((row): row is FactRow => row !== null)
}

function row(label: string, value: string | null): FactRow | null {
  return value === null ? null : { label, value }
}

/** The facts behind a result as label and value rows. Known rule types read well; any other falls back to the raw keys. */
export function factRows(result: EvaluationResultRead): FactRow[] {
  const facts = dict(result.facts)
  if (typeof facts.error === "string") return compact([row("Why it could not be evaluated", facts.error), row("Day", text(facts.as_of))])
  if (result.control.rule_type === "retention_window") {
    const retention = dict(facts.retention)
    const table = dict(facts.table)
    const days = typeof retention.days === "number" ? `${retention.days.toLocaleString()} days` : null
    return compact([
      row("Retention policy", text(retention.policy_name) && days ? `${text(retention.policy_name)} (${days})` : null),
      row("Table", text(table.path) && text(table.data_store) ? `${text(table.path)} in ${text(table.data_store)}` : text(table.path)),
      row("Date column", text(table.column)),
      row("Oldest record", when(table.oldest_record_at) ?? (table.path ? "The table is empty" : null)),
      row("Harvest it rests on", when(table.harvest_taken_at)),
      row("Measured on", text(facts.as_of)),
    ])
  }
  return Object.entries(facts).map(([label, value]) => ({
    label: label.replaceAll("_", " "),
    value: typeof value === "string" ? value : JSON.stringify(value),
  }))
}

/** "3,900 days" against "3,650 days", when the rule measured something. */
export function measurement(result: EvaluationResultRead): { measured: string; threshold: string } | null {
  if (result.measured === null || result.threshold === null) return null
  const unit = result.unit ? ` ${result.unit}` : ""
  return {
    measured: `${result.measured.toLocaleString()}${unit}`,
    threshold: `${result.threshold.toLocaleString()}${unit}`,
  }
}

/** The facts a result rests on, as the "Based on" list of ExplainWhy. */
export function resultSources(result: EvaluationResultRead) {
  return [
    { label: `${result.control.code}, rule version ${result.control.rule_version}` },
    ...factRows(result).map((fact) => ({ label: `${fact.label}: ${fact.value}` })),
  ]
}
