import AxeBuilder from "@axe-core/playwright"
import { expect, test, type Page } from "@playwright/test"

import { readContractHash } from "../plugins/contract-hash"

const BUILT_CONTRACT = readContractHash()

/** Answers GET /api/v1/meta, so these tests need no backend. */
async function serveMeta(page: Page, meta: { environment: string; contract?: string }) {
  await page.route("**/api/v1/meta", (route) =>
    route.fulfill({
      json: { version: "0.1.0", commit: "24a18c3", contract: BUILT_CONTRACT, ...meta },
    })
  )
}

test.beforeEach(async ({ page }) => {
  await serveMeta(page, { environment: "production" })
})

const SECTIONS = [
  { name: "Inbox", path: "/" },
  { name: "Assets", path: "/assets" },
  { name: "Applications", path: "/applications" },
  { name: "Controls", path: "/controls" },
  { name: "Reports", path: "/reports" },
]

test("the five sections are reachable from the header", async ({ page }) => {
  await page.goto("/")
  const main = page.getByRole("navigation", { name: "Main" })
  for (const section of SECTIONS) {
    await main.getByRole("link", { name: section.name, exact: true }).click()
    await expect(page).toHaveURL(section.path)
    await expect(page.getByRole("heading", { level: 1, name: section.name })).toBeVisible()
    await expect(main.getByRole("link", { name: section.name, exact: true })).toHaveAttribute("aria-current", "page")
  }
})

for (const section of SECTIONS) {
  test(`${section.name} has no axe violations`, async ({ page }) => {
    await page.goto(section.path)
    await expect(page.getByRole("heading", { level: 1, name: section.name })).toBeVisible()
    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze()
    expect(results.violations.map((v) => v.id)).toEqual([])
  })
}

test.describe("pairing with the API", () => {
  test("production with a matching contract shows neither badge nor banner", async ({ page }) => {
    await page.goto("/")
    await expect(page.getByRole("heading", { level: 1, name: "Inbox" })).toBeVisible()
    await expect(page.locator("[data-slot=environment-badge]")).toHaveCount(0)
    await expect(page.getByRole("alert")).toHaveCount(0)
  })

  test("outside production the header names the environment", async ({ page }) => {
    await serveMeta(page, { environment: "staging" })
    await page.goto("/assets")
    await expect(page.locator("[data-slot=environment-badge]")).toHaveText("Environment: staging")
    await expect(page.getByRole("alert")).toHaveCount(0)
  })

  test("a different contract shows the update banner, which can't be dismissed", async ({ page }) => {
    await serveMeta(page, { environment: "staging", contract: "sha256:0000" })
    await page.goto("/")
    const banner = page.getByRole("alert")
    await expect(banner).toContainText("DMC has been updated. Reload to continue.")
    await expect(banner.getByRole("button")).toHaveText(["Reload"])
    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze()
    expect(results.violations.map((v) => v.id)).toEqual([])
  })
})
