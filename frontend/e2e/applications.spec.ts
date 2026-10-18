import AxeBuilder from "@axe-core/playwright"
import { expect, test, type Page, type Route } from "@playwright/test"

// The Applications screen against a fake API, so e2e runs without a backend. The fake keeps state
// for one test and answers in the API's shapes (contracts/openapi.json).

const FINANCE = { id: "dom-finance", code: "finance", name: "Finance", description: null }
const EU = { id: "reg-eu", code: "eu", name: "European Union", description: null }
const ACTIONS = ["add_data_store", "add_environment", "edit"]
const NOW = "2026-10-18T09:00:00Z"

interface FakeOptions {
  listStatus?: number
  canCreate?: boolean
}

type Json = Record<string, unknown>

async function fakeApi(page: Page, { listStatus = 200, canCreate = true }: FakeOptions = {}) {
  const applications: Json[] = []

  const problem = (route: Route, status: number, detail: string) =>
    route.fulfill({
      status,
      contentType: "application/problem+json",
      json: { type: "about:blank", title: "Error", status, detail, request_id: "e2e" },
    })
  const list = (data: Json[]) => ({ data, allowed_actions: [], meta: { evaluated_at: null, stale_after: null, next_cursor: null, total: data.length } })

  await page.route("**/api/v1/**", async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname.replace("/api/v1", "")
    const method = request.method()

    if (path === "/reference/domains") return route.fulfill({ json: list([FINANCE]) })
    if (path === "/reference/regions") return route.fulfill({ json: list([EU]) })

    if (path === "/applications" && method === "GET") {
      if (listStatus !== 200) return problem(route, listStatus, "Failed")
      const q = url.searchParams.get("q")?.toLowerCase()
      const rows = applications.filter((a) => !q || String(a.name).toLowerCase().includes(q))
      return route.fulfill({ json: { ...list(rows), allowed_actions: canCreate ? ["create"] : [] } })
    }
    if (path === "/applications" && method === "POST") {
      const body = request.postDataJSON() as Json
      const application = {
        id: `app-${applications.length + 1}`,
        ...body,
        domain: { id: FINANCE.id, code: FINANCE.code, name: FINANCE.name },
        app_owner_id: null,
        tech_owner_id: null,
        created_at: NOW,
        updated_at: NOW,
        environments: [],
      }
      applications.push(application)
      return route.fulfill({ status: 201, json: { data: application, allowed_actions: ACTIONS, meta: {} } })
    }

    const appMatch = path.match(/^\/applications\/([^/]+)(\/environments)?$/)
    if (appMatch) {
      const application = applications.find((a) => a.id === appMatch[1])
      if (!application) return problem(route, 404, "Application does not exist.")
      const environments = application.environments as Json[]
      if (appMatch[2] && method === "POST") {
        const body = request.postDataJSON() as Json
        const environment = { id: `env-${environments.length + 1}`, application_id: application.id, name: body.name, type: body.type, region: EU, created_at: NOW, data_stores: [] }
        environments.push(environment)
        return route.fulfill({ status: 201, json: { data: environment, allowed_actions: [], meta: {} } })
      }
      return route.fulfill({ json: { data: application, allowed_actions: ACTIONS, meta: {} } })
    }

    const storeMatch = path.match(/^\/environments\/([^/]+)\/data-stores$/)
    if (storeMatch && method === "POST") {
      const environment = applications.flatMap((a) => a.environments as Json[]).find((e) => e.id === storeMatch[1])
      if (!environment) return problem(route, 404, "Environment does not exist.")
      const body = request.postDataJSON() as Json
      const store = { id: "store-1", environment_id: environment.id, ...body, region: EU, harvest_status: "never", last_harvested_at: null, created_at: NOW }
      ;(environment.data_stores as Json[]).push(store)
      return route.fulfill({ status: 201, json: { data: store, allowed_actions: [], meta: {} } })
    }

    return problem(route, 404, `No fake for ${method} ${path}`)
  })
}

/** The detail opens docked at 1536px and wider, in a sheet below. */
function detail(page: Page) {
  return page.getByRole("complementary", { name: "Application details" }).or(page.getByRole("dialog", { name: "Application details" }))
}

async function choose(page: Page, label: string, option: string) {
  await detail(page).getByRole("combobox", { name: label }).click()
  await page.getByRole("option", { name: option, exact: true }).click()
}

test("register an application with an environment and a data store", async ({ page }) => {
  await fakeApi(page)
  await page.goto("/applications")
  await expect(page.getByText("No applications yet")).toBeVisible()

  await page.getByRole("button", { name: "Register application" }).first().click()
  await expect(page).toHaveURL(/\?application=new/)
  const panel = detail(page)
  await panel.getByRole("textbox", { name: "Name" }).fill("Order management")
  await panel.getByRole("textbox", { name: "Code" }).fill("ORD")
  await choose(page, "Domain", "Finance")
  await choose(page, "Criticality", "High")
  await choose(page, "Hosting", "Public cloud")
  await panel.getByRole("button", { name: "Register application" }).click()

  await expect(page).toHaveURL(/\?application=app-1/)
  await expect(panel.getByRole("heading", { level: 2, name: "Order management" })).toBeVisible()
  await expect(panel.getByRole("tab", { name: /Know/ })).toHaveAttribute("aria-selected", "true")

  await panel.getByRole("button", { name: "Add environment" }).click()
  await panel.getByRole("textbox", { name: "Environment name" }).fill("Production")
  await choose(page, "Type", "Production")
  await choose(page, "Region", "European Union")
  await panel.getByRole("button", { name: "Add environment" }).click()
  await expect(panel.getByRole("heading", { level: 4, name: "Production" })).toBeVisible()

  await panel.getByRole("button", { name: "Add data store" }).click()
  await panel.getByRole("textbox", { name: "Data store name" }).fill("orders-db")
  await choose(page, "Type", "Relational database")
  await panel.getByRole("textbox", { name: "Platform" }).fill("PostgreSQL 18")
  await choose(page, "Region", "European Union")
  const connection = panel.getByRole("textbox", { name: "Connection reference" })
  await connection.fill("postgresql://admin:secret@db/orders")
  await connection.blur()
  await expect(panel.getByText("Enter a secret reference")).toBeVisible()
  await connection.fill("vault:dmc/orders-db")
  await panel.getByRole("button", { name: "Add data store" }).click()

  const stores = panel.getByRole("list", { name: "Data stores in Production" })
  await expect(stores.getByText("orders-db", { exact: true })).toBeVisible()
  await expect(stores.getByText("Not harvested")).toBeVisible()
  await expect(panel.getByRole("tab", { name: /Know/ })).toContainText("1 data store")

  // Below 1536px the detail is a modal sheet that hides the list; close it to see the new row.
  await panel.getByRole("button", { name: "Close details" }).click()
  await expect(page.getByRole("table", { name: "Applications" }).getByRole("cell", { name: "ORD", exact: true })).toBeVisible()
})

test("a deep link to a missing application shows not found", async ({ page }) => {
  await fakeApi(page)
  await page.goto("/applications?application=app-404")
  await expect(detail(page).getByText("This application doesn’t exist")).toBeVisible()
})

test("a failing list shows the error state with a retry", async ({ page }) => {
  await fakeApi(page, { listStatus: 500 })
  await page.goto("/applications")
  await expect(page.getByRole("alert").getByText("This didn’t load")).toBeVisible()
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible()
})

test("register is hidden when the API does not allow it", async ({ page }) => {
  await fakeApi(page, { canCreate: false })
  await page.goto("/applications")
  await expect(page.getByText("No applications yet")).toBeVisible()
  await expect(page.getByRole("button", { name: "Register application" })).toHaveCount(0)
})

test("a forbidden list shows no access", async ({ page }) => {
  await fakeApi(page, { listStatus: 403 })
  await page.goto("/applications")
  await expect(page.getByText("You don’t have access")).toBeVisible()
})

test("applications has no axe violations with a detail open", async ({ page }) => {
  await fakeApi(page)
  await page.goto("/applications?application=new")
  await expect(detail(page).getByRole("textbox", { name: "Name" })).toBeVisible()
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze()
  expect(results.violations.map((v) => v.id)).toEqual([])
})
