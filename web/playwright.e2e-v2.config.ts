import { defineConfig, devices } from "@playwright/test";
import * as dotenv from "dotenv";

dotenv.config({ path: ".vscode/.env" });

// Parallel config for the rebuilt e2e suite (tests/e2e-v2), ported 1:1 from
// tests/e2e against the post-rename codebase (Onyx*->Om*, persona->agent,
// EE dissolution, Vespa->OpenSearch). Visual-regression steps are skipped for
// now. Run: npx playwright test --config playwright.e2e-v2.config.ts
export default defineConfig({
  globalSetup: require.resolve("./tests/e2e-v2/global-setup"),
  timeout: 100000, // 100 seconds timeout
  expect: {
    timeout: 15000, // 15 seconds timeout for all assertions to reduce flakiness
    toHaveScreenshot: {
      // Allow up to 1% of pixels to differ (accounts for anti-aliasing, subpixel rendering)
      maxDiffPixelRatio: 0.01,
      // Threshold per-channel (0-1): how different a pixel can be before it counts as changed
      threshold: 0.2,
    },
  },
  retries: process.env.CI ? 2 : 0, // Retry failed tests 2 times in CI, 0 locally

  workers: process.env.CI ? 2 : undefined, // Limit to 2 parallel workers in CI to reduce flakiness

  reporter: [["list"]],
  // Only run Playwright tests from tests/e2e-v2 directory (ignore Jest tests in src/)
  testMatch: /.*\/tests\/e2e-v2\/.*\.spec\.ts/,
  outputDir: "output/playwright-v2",
  use: {
    // Base URL for the application, can be overridden via BASE_URL environment variable
    baseURL: process.env.BASE_URL || "http://localhost:3000",
    // Capture trace on failure
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "admin",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1280, height: 720 },
        storageState: "admin_auth.json",
      },
      grepInvert: /@exclusive/,
    },
    {
      // this suite runs independently and serially + slower
      // we should be cautious about bloating this suite
      name: "exclusive",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1280, height: 720 },
        storageState: "admin_auth.json",
      },
      grep: /@exclusive/,
      workers: 1,
    },
  ],
});
