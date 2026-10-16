import { describe, expect, it } from "vitest"

import { fieldA11y } from "@/patterns/field"

describe("fieldA11y", () => {
  it("returns only the id when there is no hint or error", () => {
    expect(fieldA11y("name", {})).toEqual({ id: "name", "aria-invalid": undefined, "aria-describedby": undefined })
  })

  it("points at the hint", () => {
    expect(fieldA11y("name", { hint: "Shown in search." })["aria-describedby"]).toBe("name-hint")
  })

  it("marks the control invalid and points at hint and error", () => {
    const attrs = fieldA11y("days", { hint: "Counted from the last update.", error: "Enter a number above zero." })
    expect(attrs["aria-invalid"]).toBe(true)
    expect(attrs["aria-describedby"]).toBe("days-hint days-error")
  })
})
