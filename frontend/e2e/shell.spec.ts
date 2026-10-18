import AxeBuilder from "@axe-core/playwright"
import { expect, test } from "@playwright/test"

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
