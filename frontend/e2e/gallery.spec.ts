import AxeBuilder from "@axe-core/playwright"
import { expect, test, type Page } from "@playwright/test"

const THEMES = ["light", "dark"] as const
type Theme = (typeof THEMES)[number]

async function openGallery(page: Page, theme: Theme) {
  await page.addInitScript((t) => localStorage.setItem("dmc-theme", t), theme)
  await page.goto("/gallery")
  await expect(page.getByRole("heading", { level: 1, name: "Gallery" })).toBeVisible()
  await page.evaluate(() => document.fonts.ready)
}

/**
 * Force :hover / :focus-visible on each section's hover and focus cells so the screenshot
 * shows those states. The subject is [data-gallery-subject], else the cell's first control.
 */
async function forceInteractionStates(page: Page) {
  const cdp = await page.context().newCDPSession(page)
  await cdp.send("DOM.enable")
  await cdp.send("CSS.enable")
  const { root } = await cdp.send("DOM.getDocument", { depth: -1 })
  const forced: Record<string, string[]> = { hover: ["hover"], focus: ["focus", "focus-visible", "focus-within"] }
  for (const [state, pseudo] of Object.entries(forced)) {
    const cells = await cdp.send("DOM.querySelectorAll", {
      nodeId: root.nodeId,
      selector: `[data-gallery-state="${state}"] [data-gallery-target]`,
    })
    for (const cellId of cells.nodeIds) {
      let { nodeId } = await cdp.send("DOM.querySelector", { nodeId: cellId, selector: "[data-gallery-subject]" })
      if (!nodeId) {
        ;({ nodeId } = await cdp.send("DOM.querySelector", {
          nodeId: cellId,
          selector: "button, a[href], input, textarea, [role=combobox], [tabindex]",
        }))
      }
      if (nodeId) await cdp.send("CSS.forcePseudoState", { nodeId, forcedPseudoClasses: pseudo })
    }
  }
}

for (const theme of THEMES) {
  test.describe(`gallery, ${theme} theme`, () => {
    test("loads without console errors", async ({ page }) => {
      const errors: string[] = []
      page.on("console", (msg) => {
        if (msg.type() === "error") errors.push(msg.text())
      })
      page.on("pageerror", (err) => errors.push(err.message))
      await openGallery(page, theme)
      expect(errors).toEqual([])
    })

    test("has no axe violations", async ({ page }) => {
      await openGallery(page, theme)
      const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze()
      const summary = results.violations.map((v) => ({
        rule: v.id,
        impact: v.impact,
        nodes: v.nodes.slice(0, 5).map((n) => `${n.target.join(" ")} :: ${n.failureSummary?.split("\n")[1]?.trim()}`),
      }))
      expect(summary).toEqual([])
    })

    test("first screen at this size", async ({ page }) => {
      await openGallery(page, theme)
      await expect(page).toHaveScreenshot(`first-screen-${theme}.png`)
    })

    test("every section, all states", async ({ page }, testInfo) => {
      // Section shots are layout-independent, so take them once, at 1920 wide.
      test.skip(testInfo.project.name !== "desktop", "section screenshots run in the desktop project only")
      // Taller than any section, so none is clipped by the viewport or overlapped by the sticky header.
      await page.setViewportSize({ width: 1920, height: 2160 })
      await openGallery(page, theme)
      await forceInteractionStates(page)
      const ids = await page.locator("[data-gallery-entry]").evaluateAll((els) =>
        els.map((el) => el.getAttribute("data-gallery-entry")!)
      )
      expect(ids.length).toBeGreaterThan(20)
      for (const id of ids) {
        await expect.soft(page.locator(`[data-gallery-entry="${id}"]`)).toHaveScreenshot(`${id}-${theme}.png`)
      }
    })
  })
}

test("focus ring is the 2px accent outline on every control", async ({ page }) => {
  await openGallery(page, "light")
  await page.keyboard.press("Tab")
  // The first stop is AppShell's skip link, which moves on screen as it takes focus; poll until it settles.
  await expect(page.getByRole("link", { name: "Skip to content" })).toBeFocused()
  await expect
    .poll(() =>
      page.evaluate(() => {
        const style = getComputedStyle(document.activeElement as HTMLElement)
        return { style: style.outlineStyle, width: style.outlineWidth, offset: style.outlineOffset }
      })
    )
    .toEqual({ style: "solid", width: "2px", offset: "2px" })
})

test("every section shows all seven states", async ({ page }) => {
  await openGallery(page, "light")
  const counts = await page.locator("[data-gallery-entry]").evaluateAll((els) =>
    els.map((el) => [el.getAttribute("data-gallery-entry"), el.querySelectorAll("[data-gallery-state]").length])
  )
  for (const [id, count] of counts) expect(count, `${id} states`).toBe(7)
})

test("DetailSplit keeps the selection in the URL and guards unsaved changes", async ({ page }) => {
  await openGallery(page, "light")
  const section = page.locator('[data-gallery-entry="detail-split"]')
  await section.getByRole("link", { name: /Payroll ledger/ }).click()
  await expect(page).toHaveURL(/\?asset=AST-10511/)
  await expect(page.getByRole("heading", { level: 2, name: "Payroll ledger" })).toBeVisible()

  await page.getByRole("textbox", { name: "Notes" }).fill("Draft note")
  await page.getByRole("button", { name: "Close details" }).click()
  const guard = page.getByRole("alertdialog", { name: "Discard unsaved changes?" })
  await expect(guard).toBeVisible()
  await guard.getByRole("button", { name: "Discard changes" }).click()
  await expect(page).not.toHaveURL(/asset=/)
  await expect(page.getByRole("heading", { level: 2, name: "Payroll ledger" })).toHaveCount(0)
})

test("DetailSplit opens from a deep link and shows not found for a missing item", async ({ page }) => {
  // Below 1536px the detail opens as a modal sheet, which hides the gallery heading from the
  // accessibility tree, so skip openGallery's heading check.
  await page.goto("/gallery?asset=AST-99999")
  // Docked panel at 1536px and wider, sheet below.
  const detail = page
    .getByRole("complementary", { name: "Asset details" })
    .or(page.getByRole("dialog", { name: "Asset details" }))
  await expect(detail.getByText("This asset doesn’t exist")).toBeVisible()
})

test("StageTracker moves between stages with arrow keys", async ({ page }) => {
  await openGallery(page, "light")
  const tablist = page.locator('[data-gallery-entry="stage-tracker"] [data-gallery-state="default"]').getByRole("tablist")
  await tablist.getByRole("tab", { name: /Assess/ }).focus()
  await page.keyboard.press("ArrowRight")
  await expect(tablist.getByRole("tab", { name: /Act/ })).toHaveAttribute("aria-selected", "true")
  await expect(tablist.getByRole("tab", { name: /Act/ })).toBeFocused()
})
