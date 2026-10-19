const { defineConfig, devices } = require("@playwright/test");

// Playwright doesn't officially support this local OS, so skip its host check outside CI.
if (!process.env.CI) {
  process.env.PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS = "true";
}

// Trailing slashes matter: tests navigate with page.goto("./").
// Each repo gets its own ports, so a server left running for another app is
// never mistaken for this one.
const ROOT_URL = "http://localhost:4371/";
const SUBFOLDER_URL = "http://localhost:4372/weather/";

module.exports = defineConfig({
  testDir: "./e2e",
  testMatch: "*.spec.js",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: [["html", { open: "never" }], ["list"]],
  use: {
    reducedMotion: "reduce",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "Desktop Chromium",
      use: { ...devices["Desktop Chrome"], baseURL: ROOT_URL },
    },
    {
      name: "Mobile WebKit",
      use: { ...devices["iPhone 14"], baseURL: ROOT_URL },
    },
    {
      name: "Desktop Chromium (subfolder)",
      use: { ...devices["Desktop Chrome"], baseURL: SUBFOLDER_URL },
    },
    {
      name: "Mobile WebKit (subfolder)",
      use: { ...devices["iPhone 14"], baseURL: SUBFOLDER_URL },
    },
  ],
  webServer: [
    {
      command: "python3 -m http.server 4371",
      url: ROOT_URL,
      // Fail instead of silently testing whatever already holds the port.
      reuseExistingServer: false,
    },
    {
      // Serves the repo under /weather/, like the production subfolder.
      command:
        "mkdir -p .e2e-root && ln -sfn .. .e2e-root/weather && python3 -m http.server 4372 --directory .e2e-root",
      url: SUBFOLDER_URL,
      // Fail instead of silently testing whatever already holds the port.
      reuseExistingServer: false,
    },
  ],
});
