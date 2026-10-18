import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { createClientConfig } from "./api-config"
import { DEV_USER_HEADER, fetchAsDevUser, getDevUser, setDevUser } from "./dev-user"

function memoryStorage(): Storage {
  const items = new Map<string, string>()
  return {
    get length() {
      return items.size
    },
    clear: () => items.clear(),
    getItem: (key) => items.get(key) ?? null,
    key: (index) => [...items.keys()][index] ?? null,
    removeItem: (key) => void items.delete(key),
    setItem: (key, value) => void items.set(key, value),
  }
}

describe("dev user header", () => {
  let fetchMock: ReturnType<typeof vi.fn>

  beforeEach(() => {
    vi.stubGlobal("localStorage", memoryStorage())
    fetchMock = vi.fn(async () => new Response("{}"))
    vi.stubGlobal("fetch", fetchMock)
  })

  afterEach(() => vi.unstubAllGlobals())

  const sentHeader = () => (fetchMock.mock.calls[0][0] as Request).headers.get(DEV_USER_HEADER)

  it("sends the chosen persona on every request", async () => {
    setDevUser("priya.raman")
    await fetchAsDevUser("http://dmc.test/api/v1/me")

    expect(getDevUser()).toBe("priya.raman")
    expect(sentHeader()).toBe("priya.raman")
  })

  it("sends no header until a persona is chosen, and after it is cleared", async () => {
    setDevUser("priya.raman")
    setDevUser(null)
    await fetchAsDevUser("http://dmc.test/api/v1/me")

    expect(getDevUser()).toBeNull()
    expect(sentHeader()).toBeNull()
  })

  it("is the generated client's fetch", () => {
    expect(createClientConfig({}).fetch).toBe(fetchAsDevUser)
  })
})
