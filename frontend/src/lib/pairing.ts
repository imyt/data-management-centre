// The pairing check (ADR 0004 §5): is this bundle talking to the API it was built for?
import type { MetaRead } from "@/api"

export interface Pairing {
  /** The API serves a different contract than this bundle was built with: reload to get the matching bundle. */
  outdated: boolean
  /** Shown as a badge outside production, so nobody mistakes staging for production. */
  environmentBadge: string | null
}

/** Until /meta answers, or if it fails, there is nothing to warn about: the app behaves as before. */
export function comparePairing(builtContract: string, meta: MetaRead | undefined): Pairing {
  if (!meta) return { outdated: false, environmentBadge: null }
  return {
    outdated: meta.contract !== builtContract,
    environmentBadge: meta.environment === "production" ? null : meta.environment,
  }
}
