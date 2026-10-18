import { createHash } from "node:crypto"
import { readFileSync } from "node:fs"
import path from "node:path"
import type { Plugin } from "vite"

// The bundle embeds the hash of the contract its client was generated from; GET /api/v1/meta
// reports the hash of the contract the API serves (ADR 0004 §5, ADR 0008). Must match
// backend/app/core/contract.py: sha256 of the UTF-8 text with LF line endings.
export const CONTRACT_PATH = path.resolve(import.meta.dirname, "../../contracts/openapi.json")

export function contractHash(text: string): string {
  return `sha256:${createHash("sha256").update(text.replace(/\r\n/g, "\n"), "utf8").digest("hex")}`
}

export function readContractHash(file = CONTRACT_PATH): string {
  return contractHash(readFileSync(file, "utf8"))
}

const ID = "virtual:dmc-contract"
const RESOLVED_ID = `\0${ID}`

/** `import { CONTRACT_HASH } from "virtual:dmc-contract"`; re-read when the contract changes in dev. */
export function contractHashPlugin(file = CONTRACT_PATH): Plugin {
  return {
    name: "dmc-contract-hash",
    resolveId: (id) => (id === ID ? RESOLVED_ID : undefined),
    load(id) {
      if (id !== RESOLVED_ID) return undefined
      this.addWatchFile(file)
      return `export const CONTRACT_HASH = ${JSON.stringify(readContractHash(file))}\n`
    },
  }
}
