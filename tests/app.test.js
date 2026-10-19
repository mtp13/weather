const { describe, it, beforeEach, afterEach } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const {
  MESSAGES,
  formatDate,
  upcomingDays,
  statusMessage,
  createCard,
  renderCards,
  loadWeather,
  initializeApp,
} = require("../app.js");

const rootDir = path.resolve(__dirname, "..");

function day(overrides = {}) {
  return {
    date: "2026-07-07",
    city: "Test City",
    country: "Testland",
    max_temp: 73,
    min_temp: 53,
    weather: "Overcast",
    status: "ok",
    ...overrides,
  };
}

// A tiny DOM: just enough for createElement/append/replaceChildren/textContent.
class MockElement {
  constructor(tag) {
    this.tag = tag;
    this.className = "";
    this.dataset = {};
    this.attrs = {};
    this.children = [];
    this.hidden = false;
    this._text = "";
  }
  set textContent(value) {
    this._text = String(value);
    this.children = [];
  }
  get textContent() {
    return this._text + this.children.map((c) => c.textContent).join("");
  }
  setAttribute(k, v) {
    this.attrs[k] = String(v);
  }
  append(...nodes) {
    for (const node of nodes) {
      this.children.push(
        typeof node === "string"
          ? Object.assign(new MockElement("#text"), { _text: node })
          : node,
      );
    }
  }
  replaceChildren(...nodes) {
    this.children = [];
    this._text = "";
    this.append(...nodes);
  }
  find(predicate) {
    if (predicate(this)) return this;
    for (const child of this.children) {
      const found = child.find(predicate);
      if (found) return found;
    }
    return null;
  }
}

function jsonResponse(body, ok = true) {
  return { ok, json: async () => body };
}

describe("Static assets & markup", () => {
  const html = fs.readFileSync(path.join(rootDir, "index.html"), "utf8");
  const refs = [...html.matchAll(/\b(?:href|src)="([^"]*)"/g)].map((m) => m[1]);

  it("references only files that exist", () => {
    assert.ok(refs.length > 0);
    for (const ref of refs) {
      assert.ok(fs.existsSync(path.join(rootDir, ref)), `Missing file: ${ref}`);
    }
  });

  it("keeps every href and src relative (no root-anchored paths, no <base>)", () => {
    for (const ref of refs) {
      assert.ok(!ref.startsWith("/"), `Root-anchored path: ${ref}`);
      assert.ok(!/^[a-z]+:/i.test(ref), `Absolute URL: ${ref}`);
    }
    assert.doesNotMatch(html, /<base\b/i);
  });

  it("has no inline scripts, inline styles or on* handlers (CSP-safe)", () => {
    for (const [tag] of html.matchAll(/<script\b[^>]*>/gi)) {
      assert.match(tag, /\bsrc="/, `Inline script: ${tag}`);
    }
    assert.doesNotMatch(html, /<style\b/i, "Inline <style> block");
    assert.doesNotMatch(html, /\sstyle="/i, "Inline style attribute");
    assert.doesNotMatch(html, /\son[a-z]+="/i, "Inline on* handler");
  });

  it("has a lowercase doctype, charset, viewport, and a status region", () => {
    assert.match(html, /^<!doctype html>/);
    assert.match(html, /<meta charset="utf-8"/i);
    assert.match(html, /<meta name="viewport"/);
    assert.match(html, /<script src="app\.js" defer><\/script>/);
    assert.match(html, /id="status"[^>]*role="status"/);
  });

  it("app.js builds cards without innerHTML", () => {
    const js = fs.readFileSync(path.join(rootDir, "app.js"), "utf8");
    assert.doesNotMatch(js, /innerHTML|insertAdjacentHTML|document\.write/);
  });
});

describe("formatDate", () => {
  it("formats an ISO date as weekday, month and day", () => {
    assert.equal(formatDate("2026-07-07"), "Tuesday, Jul 7");
    assert.equal(formatDate("2026-12-31"), "Thursday, Dec 31");
  });

  it("does not depend on the process timezone", () => {
    const original = process.env.TZ;
    process.env.TZ = "Pacific/Kiritimati";
    try {
      assert.equal(formatDate("2026-07-07"), "Tuesday, Jul 7");
    } finally {
      if (original === undefined) delete process.env.TZ;
      else process.env.TZ = original;
    }
  });
});

describe("upcomingDays and statusMessage", () => {
  it("hides past days and keeps ok and out_of_range", () => {
    const days = [
      day({ status: "past" }),
      day({ status: "ok" }),
      day({ status: "out_of_range" }),
    ];
    assert.deepEqual(
      upcomingDays(days).map((d) => d.status),
      ["ok", "out_of_range"],
    );
    assert.equal(statusMessage(days), "");
  });

  it("says the trip dates have passed when every date has passed", () => {
    const days = [day({ status: "past" }), day({ status: "past" })];
    assert.equal(statusMessage(days), "Trip dates have passed");
  });

  it("says there is no data for an empty list", () => {
    assert.equal(statusMessage([]), MESSAGES.empty);
  });
});

describe("DOM rendering (mock DOM)", () => {
  let els;

  beforeEach(() => {
    els = {
      "weather-list": new MockElement("ul"),
      status: new MockElement("p"),
    };
    global.document = {
      getElementById: (id) => els[id] ?? null,
      createElement: (tag) => new MockElement(tag),
    };
  });

  afterEach(() => {
    delete global.document;
  });

  it("builds an ok card from textContent with temperatures", () => {
    const card = createCard(day());
    assert.equal(card.tag, "li");
    assert.equal(card.dataset.status, "ok");
    assert.match(card.textContent, /Tuesday, Jul 7/);
    assert.match(card.textContent, /Test City/);
    assert.match(card.textContent, /Overcast/);
    assert.match(card.textContent, /High 73°F/);
    assert.match(card.textContent, /Low 53°F/);
    const time = card.find((e) => e.tag === "time");
    assert.equal(time.attrs.datetime, "2026-07-07");
  });

  it("never interprets data as markup", () => {
    const card = createCard(day({ city: "<img src=x onerror=alert(1)>" }));
    assert.equal(
      card.find((e) => e.className === "city").textContent,
      "<img src=x onerror=alert(1)>",
    );
  });

  it("shows the range message for out_of_range days", () => {
    const card = createCard(
      day({
        status: "out_of_range",
        max_temp: null,
        min_temp: null,
        weather: null,
      }),
    );
    assert.match(card.textContent, /Forecast available ~16 days ahead/);
    assert.doesNotMatch(card.textContent, /°F/);
  });

  it("renders only upcoming cards and hides the status when there are some", () => {
    initializeApp(() => new Promise(() => {}));
    renderCards([day({ status: "past" }), day({ date: "2026-07-08" })]);
    assert.equal(els["weather-list"].children.length, 1);
    assert.equal(els.status.hidden, true);
  });

  it("shows the all-past message instead of an empty list", async () => {
    await initializeApp(async () =>
      jsonResponse([day({ status: "past" }), day({ status: "past" })]),
    );
    assert.equal(els["weather-list"].children.length, 0);
    assert.equal(els.status.textContent, "Trip dates have passed");
    assert.equal(els.status.hidden, false);
  });

  it("shows a loading message while the request is pending", () => {
    initializeApp(() => new Promise(() => {}));
    assert.equal(els.status.textContent, MESSAGES.loading);
    assert.equal(els.status.dataset.state, "loading");
  });

  it("shows the empty message for an empty list", async () => {
    await initializeApp(async () => jsonResponse([]));
    assert.equal(els.status.textContent, MESSAGES.empty);
  });

  it("shows the JSON error from a 502", async () => {
    await initializeApp(async () =>
      jsonResponse({ error: "The weather service is unavailable." }, false),
    );
    assert.equal(els.status.dataset.state, "error");
    assert.equal(
      els.status.textContent,
      "Error: The weather service is unavailable.",
    );
    assert.equal(els["weather-list"].children.length, 0);
  });

  it("shows a generic error when the response is not JSON or the request fails", async () => {
    await initializeApp(async () => ({
      ok: false,
      json: async () => {
        throw new Error("bad");
      },
    }));
    assert.equal(els.status.textContent, `Error: ${MESSAGES.fetchFailed}`);

    await loadWeather(async () => {
      throw new TypeError("offline");
    });
    assert.equal(els.status.textContent, `Error: ${MESSAGES.fetchFailed}`);

    await loadWeather(async () => jsonResponse({ not: "a list" }));
    assert.equal(els.status.textContent, `Error: ${MESSAGES.fetchFailed}`);
  });

  it("requests the relative ./api/weather URL", async () => {
    const urls = [];
    await initializeApp(async (url) => {
      urls.push(url);
      return jsonResponse([]);
    });
    assert.deepEqual(urls, ["./api/weather"]);
  });
});

describe("Vercel deployment config", () => {
  const vercel = JSON.parse(
    fs.readFileSync(path.join(rootDir, "vercel.json"), "utf8"),
  );
  const headersFor = (source) =>
    Object.fromEntries(
      vercel.headers
        .find((rule) => rule.source === source)
        .headers.map(({ key, value }) => [key, value]),
    );

  it("sends a strict CSP and the security headers on every path", () => {
    const headers = headersFor("/(.*)");
    const csp = headers["Content-Security-Policy"];
    assert.match(csp, /default-src 'self'/);
    assert.match(csp, /script-src 'self'(;|$)/);
    assert.match(csp, /style-src 'self'(;|$)/);
    assert.match(csp, /connect-src 'self'(;|$)/);
    assert.match(csp, /object-src 'none'/);
    assert.match(csp, /frame-ancestors 'none'/);
    assert.doesNotMatch(csp, /unsafe-|https?:|\*/);
    assert.equal(headers["X-Content-Type-Options"], "nosniff");
    assert.ok(headers["Referrer-Policy"]);
    assert.ok(headers["Permissions-Policy"]);
  });

  it("revalidates index.html only, and does not touch the API's cache header", () => {
    const rule = vercel.headers.find((r) =>
      r.headers.some((h) => h.key === "Cache-Control"),
    );
    const pattern = new RegExp(`^${rule.source}$`);
    assert.ok(pattern.test("/index.html"));
    assert.ok(!pattern.test("/api/weather"));
    assert.equal(vercel.builds, undefined);
    assert.equal(vercel.routes, undefined);
  });

  it("keeps tooling files out of the deployment but not the Python runtime files", () => {
    const ignored = fs
      .readFileSync(path.join(rootDir, ".vercelignore"), "utf8")
      .split("\n");
    for (const entry of [
      "package.json",
      "package-lock.json",
      "tests/",
      "e2e/",
      "AGENTS.md",
      ".github/",
    ]) {
      assert.ok(ignored.includes(entry), `.vercelignore is missing ${entry}`);
    }
    for (const entry of [
      "pyproject.toml",
      "uv.lock",
      ".python-version",
      "api/",
      "itinerary.json",
    ]) {
      assert.ok(
        !ignored.includes(entry),
        `.vercelignore must not list ${entry}`,
      );
    }
  });
});
