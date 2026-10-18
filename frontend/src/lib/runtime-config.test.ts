import { describe, expect, it } from "vitest"

import { parseRuntimeConfig } from "./runtime-config"

describe("parseRuntimeConfig", () => {
  it("reads the API base URL without a trailing slash", () => {
    expect(parseRuntimeConfig({ apiBaseUrl: "https://dmc-api.example.com/" })).toEqual({
      apiBaseUrl: "https://dmc-api.example.com",
    })
  })

  it("falls back to same-origin for anything else", () => {
    expect(parseRuntimeConfig(null)).toEqual({})
    expect(parseRuntimeConfig({ apiBaseUrl: "" })).toEqual({})
    expect(parseRuntimeConfig({ apiBaseUrl: 42 })).toEqual({})
  })
})
