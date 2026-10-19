const fs = require("node:fs");
const path = require("node:path");
const { test, expect } = require("./csp-fixture");
const AxeBuilder = require("@axe-core/playwright").default;

function fixture(name) {
  return JSON.parse(
    fs.readFileSync(path.join(__dirname, "fixtures", `${name}.json`), "utf8"),
  );
}

// Serve a fixture for ./api/weather. E2E never reaches Open-Meteo or the real function.
async function mockApi(page, name, status = 200) {
  const requests = [];
  await page.route("**/api/weather", async (route) => {
    requests.push(route.request().url());
    await route.fulfill({
      status,
      contentType: "application/json",
      body: JSON.stringify(fixture(name)),
    });
  });
  return requests;
}

async function expectNoAxeViolations(page) {
  const scan = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();
  expect(scan.violations).toEqual([]);
}

test.describe("Weather E2E & Accessibility", () => {
  let consoleErrors = [];
  let pageErrors = [];
  let cspViolations = [];
  // Set by tests that expect the browser to log a failed request.
  let allowedConsoleErrors = [];

  test.beforeEach(async ({ page }) => {
    consoleErrors = [];
    pageErrors = [];
    cspViolations = [];
    allowedConsoleErrors = [];

    page.on("console", (msg) => {
      if (msg.type() === "error") {
        consoleErrors.push(msg.text());
      }
    });

    page.on("pageerror", (err) => {
      pageErrors.push(err.message);
    });

    await page.addInitScript(() => {
      window.__cspViolations = [];
      document.addEventListener("securitypolicyviolation", (e) => {
        window.__cspViolations.push(
          `${e.violatedDirective}: ${e.blockedURI || "inline"}`,
        );
      });
    });
  });

  test.afterEach(async ({ page }) => {
    const violations = await page
      .evaluate(() => window.__cspViolations || [])
      .catch(() => []);
    cspViolations.push(...violations);

    const unexpected = consoleErrors.filter(
      (text) => !allowedConsoleErrors.some((re) => re.test(text)),
    );
    expect(unexpected, "Expected zero console.error messages").toEqual([]);
    expect(pageErrors, "Expected zero uncaught page errors").toEqual([]);
    expect(cspViolations, "Expected zero CSP violations").toEqual([]);
  });

  test("renders a card for every day when all are upcoming", async ({
    page,
  }) => {
    const requests = await mockApi(page, "all-ok");
    await page.goto("./");

    const cards = page.locator("#weather-list > li");
    await expect(cards).toHaveCount(3);
    await expect(page.locator("#status")).toBeHidden();

    const first = cards.first();
    await expect(first.locator("time")).toHaveText("Tuesday, Jul 7");
    await expect(first.locator("time")).toHaveAttribute(
      "datetime",
      "2026-07-07",
    );
    await expect(first.locator("h2")).toHaveText("Fixture Falls");
    await expect(first).toContainText("Testland");
    await expect(first).toContainText("Overcast");
    await expect(first.locator(".high")).toHaveText("↑ High 73°F");
    await expect(first.locator(".low")).toHaveText("↓ Low 53°F");
    await expect(cards.nth(2)).toContainText("Thunderstorm");

    // The page asks for the relative ./api/weather URL, so it works under /weather/.
    expect(requests).toHaveLength(1);
    expect(new URL(requests[0]).pathname).toMatch(/\/api\/weather$/);
  });

  test("hides past days and says when a forecast is not yet available", async ({
    page,
  }) => {
    await mockApi(page, "mixed");
    await page.goto("./");

    const cards = page.locator("#weather-list > li");
    await expect(cards).toHaveCount(2);
    await expect(page.getByText("Sunday, Jul 5")).toHaveCount(0);
    await expect(cards.first()).toContainText("Tuesday, Jul 7");
    await expect(cards.first()).toContainText("73°F");
    await expect(cards.nth(1)).toContainText(
      "Forecast available ~16 days ahead",
    );
    await expect(cards.nth(1)).not.toContainText("°F");
    await expect(page.locator("#status")).toBeHidden();
  });

  test("shows 'Trip dates have passed' when every date has passed", async ({
    page,
  }) => {
    await mockApi(page, "all-past");
    await page.goto("./");

    await expect(page.locator("#status")).toHaveText("Trip dates have passed");
    await expect(page.locator("#status")).toHaveAttribute("role", "status");
    await expect(page.locator("#weather-list > li")).toHaveCount(0);
  });

  test("shows a message for an empty list", async ({ page }) => {
    await mockApi(page, "empty");
    await page.goto("./");

    await expect(page.locator("#status")).toHaveText(
      "No weather data available",
    );
    await expect(page.locator("#weather-list > li")).toHaveCount(0);
  });

  test("shows the API's error message after a 502", async ({ page }) => {
    // Chromium logs a console.error for any failed (non-2xx) resource load.
    allowedConsoleErrors = [/502/];
    await mockApi(page, "error", 502);
    await page.goto("./");

    await expect(page.locator("#status")).toHaveText(
      "Error: The weather service is unavailable.",
    );
    await expect(page.locator("#status")).toHaveAttribute(
      "data-state",
      "error",
    );
    await expect(page.locator("#weather-list > li")).toHaveCount(0);
  });

  test("shows a loading message until the request completes", async ({
    page,
  }) => {
    let release;
    const gate = new Promise((resolve) => (release = resolve));
    await page.route("**/api/weather", async (route) => {
      await gate;
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(fixture("all-ok")),
      });
    });
    await page.goto("./");

    await expect(page.locator("#status")).toHaveText("Loading weather data…");
    release();
    await expect(page.locator("#weather-list > li")).toHaveCount(3);
    await expect(page.locator("#status")).toBeHidden();
  });

  test("loads its own stylesheet, script and icon over relative paths", async ({
    page,
  }) => {
    await mockApi(page, "all-ok");
    const failed = [];
    page.on("response", (res) => {
      if (res.status() >= 400) failed.push(`${res.status()} ${res.url()}`);
    });
    await page.goto("./");
    await expect(page.locator("#weather-list > li")).toHaveCount(3);
    expect(failed).toEqual([]);
    // style.css applied: the cards have a white background.
    await expect(page.locator(".weather-card").first()).toHaveCSS(
      "background-color",
      "rgb(255, 255, 255)",
    );
  });

  for (const name of ["all-ok", "mixed", "all-past", "empty"]) {
    test(`accessibility: axe finds no wcag2a/wcag2aa violations (${name})`, async ({
      page,
    }) => {
      await mockApi(page, name);
      await page.goto("./");
      await expect(page.locator("#status[data-state=loading]")).toHaveCount(0);
      await expectNoAxeViolations(page);
    });
  }

  test("accessibility: axe finds no violations on the error state", async ({
    page,
  }) => {
    allowedConsoleErrors = [/502/];
    await mockApi(page, "error", 502);
    await page.goto("./");
    await expect(page.locator("#status")).toHaveAttribute(
      "data-state",
      "error",
    );
    await expectNoAxeViolations(page);
  });
});
