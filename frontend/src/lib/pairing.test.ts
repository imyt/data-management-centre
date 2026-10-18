import { describe, expect, it } from "vitest"

import type { MetaRead } from "@/api"

import { comparePairing } from "./pairing"

const BUILT = "sha256:aaaa"

function meta(overrides: Partial<MetaRead> = {}): MetaRead {
  return { environment: "staging", version: "0.1.0", commit: "24a18c3", contract: BUILT, ...overrides }
}

describe("comparePairing", () => {
  it("is quiet until the API answers", () => {
    expect(comparePairing(BUILT, undefined)).toEqual({ outdated: false, environmentBadge: null })
  })

  it("flags a bundle built from a different contract", () => {
    expect(comparePairing(BUILT, meta({ contract: "sha256:bbbb" })).outdated).toBe(true)
    expect(comparePairing(BUILT, meta()).outdated).toBe(false)
  })

  it("badges every environment except production", () => {
    expect(comparePairing(BUILT, meta({ environment: "staging" })).environmentBadge).toBe("staging")
    expect(comparePairing(BUILT, meta({ environment: "local" })).environmentBadge).toBe("local")
    expect(comparePairing(BUILT, meta({ environment: "production" })).environmentBadge).toBeNull()
  })

  it("still flags an outdated bundle in production", () => {
    expect(comparePairing(BUILT, meta({ environment: "production", contract: "sha256:bbbb" }))).toEqual({
      outdated: true,
      environmentBadge: null,
    })
  })
})
