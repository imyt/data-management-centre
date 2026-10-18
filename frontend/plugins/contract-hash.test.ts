import { describe, expect, it } from "vitest"

import { contractHash, readContractHash } from "./contract-hash"

describe("contractHash", () => {
  it("matches the backend's hash for the same text (backend/tests/core/test_meta.py)", () => {
    expect(contractHash("{}\n")).toBe("sha256:ca3d163bab055381827226140568f3bef7eaac187cebd76878e0b63e9e442356")
  })

  it("ignores CRLF line endings from a Windows checkout", () => {
    expect(contractHash('{\r\n  "a": 1\r\n}\n')).toBe(contractHash('{\n  "a": 1\n}\n'))
  })

  it("reads the committed contract", () => {
    expect(readContractHash()).toMatch(/^sha256:[0-9a-f]{64}$/)
  })
})
