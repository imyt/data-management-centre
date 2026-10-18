import type { SubjectType } from "@/api"

// Words for the API's value sets, in sentence case (DESIGN.md: Content).

export const SUBJECT_TYPE: Record<SubjectType, string> = {
  asset: "Asset",
  data_store: "Data store",
  application: "Application",
}

export const SUBJECT_TYPE_PLURAL: Record<SubjectType, string> = {
  asset: "assets",
  data_store: "data stores",
  application: "applications",
}

export function subjectLabel(type: string): string {
  return SUBJECT_TYPE[type as SubjectType] ?? type
}

export const OPERATOR = {
  equals: "is",
  in: "is one of",
  not_in: "is none of",
} as const

export type Operator = keyof typeof OPERATOR

/** Where a subject opens in the app, when it has a screen of its own. */
export function subjectPath(type: string, id: string): string | null {
  if (type === "asset") return `/assets?asset=${id}`
  if (type === "application") return `/applications?application=${id}`
  return null
}
