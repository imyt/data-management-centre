import { defineConfig, devices } from "@playwright/test"

// Gallery screenshots and axe checks (frontend.instructions.md: Tests).
// Layouts are checked at the three DESIGN.md sizes.
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  expect: {
    toHaveScreenshot: { maxDiffPixelRatio: 0.002, animations: "disabled", caret: "hide" },
  },
  use: {
    baseURL: "http://localhost:5173",
    reducedMotion: "reduce",
    trace: "on-first-retry",
  },
  projects: [
    { name: "laptop", use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 800 } } },
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1920, height: 1080 } } },
    { name: "ultrawide", use: { ...devices["Desktop Chrome"], viewport: { width: 3440, height: 1440 } } },
  ],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:5173/dev/components",
    reuseExistingServer: !process.env.CI,
  },
})
