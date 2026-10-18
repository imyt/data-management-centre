import { QueryClient } from "@tanstack/react-query"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { getDevUser } from "@/lib/dev-user"

import { switchPersona } from "./use-identity"

describe("switchPersona", () => {
  beforeEach(() => {
    const items = new Map<string, string>()
    vi.stubGlobal("localStorage", {
      getItem: (key: string) => items.get(key) ?? null,
      setItem: (key: string, value: string) => void items.set(key, value),
      removeItem: (key: string) => void items.delete(key),
    })
  })

  afterEach(() => vi.unstubAllGlobals())

  it("stores the persona and drops data fetched as the previous one", async () => {
    const queryClient = new QueryClient()
    queryClient.setQueryData(["getMe"], { data: { display_name: "Hannah Becker" } })

    await switchPersona(queryClient, "priya.raman")

    expect(getDevUser()).toBe("priya.raman")
    expect(queryClient.getQueryData(["getMe"])).toBeUndefined()
  })

  it("clears the persona to act as the default again", async () => {
    await switchPersona(new QueryClient(), "priya.raman")
    await switchPersona(new QueryClient(), null)

    expect(getDevUser()).toBeNull()
  })
})
