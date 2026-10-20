# AGENTS.md

Guidance for AI coding agents (Claude Code, Gemini CLI, Codex, etc.) working in
this repo. `CLAUDE.md` and `GEMINI.md` just import this file, so edit this one.

## Project

A trip weather forecast page. A small Vercel Python function (`api/weather.py`)
reads the trip from `itinerary.json`, asks [Open-Meteo](https://open-meteo.com/)
for each city's daily forecast, and returns JSON. A static page (`index.html`,
`app.js`, `style.css`) fetches it and shows one card per upcoming day.

- Python is pinned to 3.14 in both `.python-version` and `requires-python` in
  `pyproject.toml`. If the version changes, update both.
- **The function has no runtime dependencies**: it uses only the standard
  library (`urllib`, `json`). Don't add `requests`, `pandas` or similar.
  Dependencies are managed with **uv**; `pyproject.toml` and `uv.lock` are the
  source of truth, and `uv.lock` is never edited by hand. Only dev dependencies
  (ruff, pytest) are allowed.
- **Dev dependencies for tooling are allowed in the frontend too, runtime
  dependencies are not, and there must never be a build step.** The browser
  loads `app.js` directly as a classic `<script defer>`, not an ES module. Don't
  add frameworks, runtime npm packages, a bundler or a build pipeline unless
  asked.

## Commands

```sh
uv sync                               # install Python dev tooling from pyproject.toml + uv.lock
npm ci                                # install Node dev tooling from package-lock.json
uv run ruff check .                   # lint Python
uv run ruff format .                  # format Python (add --check to only check)
uv run pytest                         # Python tests (tests/), no network
uv run python api/weather.py          # print the real forecast as a table (calls Open-Meteo)
npm test                              # node --test tests/*.test.js (Node built-in test runner)
npm run test:e2e                      # playwright test (Desktop Chromium + Mobile WebKit E2E & axe a11y)
npm run format                        # prettier --write .
npm run lint                          # npm run format:check && npm run lint:html
node --check app.js                   # syntax check (CI runs this too)
vercel dev                            # run the page and the real function at http://localhost:3000
python3 -m http.server 4371           # static page only; /api/weather will 404 unless mocked
```

Run commands from the repo root. CI (`.github/workflows/ci.yml`) runs three jobs
on pull requests and pushes to `master` (superseded runs on the same ref are
cancelled): `python` (`uv sync --locked`, `ruff check`, `ruff format --check`,
`pytest`), `test` (`npm ci`, `npm run lint`, `node --check app.js`, `npm test`)
and `e2e` (Playwright and axe).

## Layout

| File                                                                    | Purpose                                                                                                          |
| ----------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `api/weather.py`                                                        | The Vercel function: itinerary loading, one Open-Meteo request, `build_results`, and the `handler` class         |
| `itinerary.json`                                                        | The trip: cities and dates (see below). Public on purpose                                                        |
| `index.html`                                                            | Markup only: a `role="status"` message area and an empty `<ul id="weather-list">`                                |
| `app.js`                                                                | Fetches `./api/weather` and renders cards with DOM APIs                                                          |
| `style.css`                                                             | Styles. The status area is styled from `data-state`                                                              |
| `cruise.png`                                                            | Favicon and apple-touch icon                                                                                     |
| `vercel.json`, `.vercelignore`                                          | Security/CSP and cache headers, plus the deploy exclusion list                                                   |
| `pyproject.toml`, `uv.lock`, `.python-version`                          | Project metadata, locked dev dependencies, Python version, `[tool.ruff]` and `[tool.pytest.ini_options]` config  |
| `package.json`, `package-lock.json`                                     | Node dev tooling only (Prettier, html-validate, Playwright, axe); no `build` script                              |
| `.prettierrc`, `.prettierignore`, `.htmlvalidate.json`, `.editorconfig` | Formatter and linter configuration                                                                               |
| `.git-blame-ignore-revs`                                                | Formatting-only commits to ignore in `git blame`                                                                 |
| `tests/test_vercel_json.py`                                             | Guards the `vercel.json` branch-deployment rule (only the default branch deploys)                                |
| `tests/`                                                                | `test_weather.py`, `test_vercelignore.py` (pytest); `app.test.js` (node:test); `conftest.py`                     |
| `tests/fixtures/`                                                       | Made-up itinerary and real recorded Open-Meteo responses for the Python tests                                    |
| `e2e/`                                                                  | `weather.spec.js` (Playwright + axe), `csp-fixture.js` (applies the `vercel.json` CSP), `fixtures/` (mocked API) |
| `playwright.config.js`                                                  | Playwright projects (root and `/weather/` subfolder) and local web servers                                       |
| `.github/workflows/ci.yml`, `dependabot.yml`                            | CI jobs and monthly dependency updates (uv, npm, GitHub Actions)                                                 |
| `deferred-review-items.md`                                              | Persistent list of review findings deferred to a later PR                                                        |

## How it works

- **Updating a trip:** edit `itinerary.json`. It is a list of objects with
  `name`, `country`, `latitude`, `longitude` and `dates` (ISO `YYYY-MM-DD`
  strings, one per day of the visit). Add one entry per visit; a city visited
  twice gets two entries. Keep the format as it is; `itinerary.json` stays
  public and tests use fixtures, never the real file.
- **Forecast limit:** Open-Meteo's free API forecasts 16 days ahead
  (`FORECAST_DAYS`). Dates beyond that get `status: "out_of_range"`.
- **One request:** `fetch_forecasts()` sends every city in one call
  (comma-separated `latitude`/`longitude`) to the `daily` endpoint with
  `timezone=auto`, so each high, low and weather code belongs to the city's
  **local** calendar day. One location returns an object and several return a
  list; the code wraps the object in a list. The last forecast day can be
  `null`.
- **Pure core:** `load_itinerary(path)`,
  `fetch_forecasts(cities, fetch=urlopen_json)` and
  `build_results(itinerary, forecasts, now)` take their inputs as arguments so
  tests inject a fake `fetch` and a fixed `now`. `build_response()` returns
  `(status, headers, body)`, and `handler.do_GET` only writes it. "Today" is
  each city's own local date, from the response's `utc_offset_seconds`, never
  the server's date.
- **Result shape:** each result has `date`, `city`, `country`, `max_temp`,
  `min_temp`, `weather` and `status`: `ok`, `past` (before today in the city's
  timezone) or `out_of_range`. Temperatures are whole degrees Fahrenheit,
  rounded half up. Weather codes map through `WEATHER_DESCRIPTIONS`; an unknown
  code reads "Unknown".
- **Responses:** 200 with
  `Cache-Control: public, s-maxage=1800, stale-while-revalidate=3600` so
  Vercel's CDN caches it (the CDN strips those directives from what clients see;
  look for `x-vercel-cache`). An upstream failure is `502` and anything else
  `500`, both `{"error": "…"}` with `no-store`, logged to stderr. Never put a
  traceback or upstream text in a response body.
- **`app.js` runs in the browser and in Node.** At the bottom, `initializeApp()`
  runs only if `document` exists and `module.exports` is set only if `module`
  exists. Keep both guards and don't touch the DOM at the top level. DOM lookups
  belong in `bindDomElements()`; if you add a `getElementById` lookup, add it to
  the mock in `tests/app.test.js`.
- **Rendering:** cards are built with `createElement` and `textContent`, never
  `innerHTML`. Past days are hidden; when every date has passed, or the list is
  empty, the status area says so ("Trip dates have passed", "No weather data
  available"); `out_of_range` cards say "Forecast available ~16 days ahead"; a
  failed request shows the JSON `error` text.

## Conventions

- Markdown is wrapped at 80 columns: `.prettierrc` has a `*.md` override
  (`proseWrap: always`), so `npm run format` rewraps prose and
  `npm run format:check` flags long lines.
- **ruff** (Python) and **Prettier** (JS, CSS, HTML, Markdown, YAML, JSON) are
  the source of truth for formatting, so don't hand-format against them.
  `.editorconfig` sets LF line endings, a final newline, 4-space indentation for
  Python and 2 spaces for everything else. Formatting-only commits are separate
  and listed in `.git-blame-ignore-revs`. Every commit must pass `ruff check`,
  `ruff format --check`, `pytest`, `npm run lint` and `npm test`.
- `itinerary.json` and the recorded `tests/fixtures/open_meteo_*.json` are
  excluded from Prettier so they keep their formatting.
- Python style: plain functions, a short docstring on each, `UPPER_CASE`
  constants, ruff rules `E F W I B UP`. Use `X | None`, not `Optional[X]`.
- **No inline scripts, inline styles, `on*=` attributes or third-party
  resources,** because they would break the Content Security Policy in
  `vercel.json`. Everything is `'self'`; `connect-src 'self'` is there only
  because the page fetches its own `./api/weather`. If another origin is truly
  needed, update the CSP and document why here.
- Style the UI from state with `data-*` attributes (`data-state`,
  `data-status`), not inline styles from JS.
- Accessibility is required: loading, empty, all-past and error text live in the
  `role="status"` region, dates are `<time datetime>`, and axe must report zero
  violations.
- Paths stay relative (`./api/weather`, `style.css`), because the app is served
  at both a root and `/weather/`.

## Testing

- `uv run pytest` never touches the network or the real `itinerary.json`:
  `fetch` is injected, or `urlopen_json` is monkeypatched, and tests read
  `tests/fixtures/itinerary.json` (made up) and the recorded Open-Meteo
  responses `open_meteo_multi.json` and `open_meteo_single.json`. Pin "now" by
  passing `now`. Cover the single-city object shape, the null last day, past,
  out-of-range, and a city whose local date differs from the UTC date.
  `tests/test_vercelignore.py` guards `.vercelignore` and checks that
  `vercel.json` has no `builds` or `routes`.
- To refresh a fixture, call the real API once (see `forecast_url()` for the
  parameters), remove `generationtime_ms` and update the dates and expectations
  in the tests.
- `npm test` covers formatting, status handling, rendering against a mock DOM,
  static markup checks and the Vercel config with only `node:test` and
  `node:assert/strict`.
- `npm run test:e2e` runs Playwright in Desktop Chromium and Mobile WebKit at
  `/` (port 4371) and `/weather/` (port 4372; served from `.e2e-root/weather`,
  and no running server is reused, so free those ports first). Every test mocks
  `**/api/weather` with a fixture from `e2e/fixtures/` and **never calls
  Open-Meteo**. Specs import `test`/`expect` from `./csp-fixture`, so the
  production CSP is enforced, and the harness fails on any `console.error`, page
  error or CSP violation. axe runs on every state. If a test uses a fake clock,
  call `page.clock.resume()` before scanning, because axe needs real timers.
- Add or update tests for any behaviour change, and run everything before you
  finish. Playwright can't connect to localhost in some sandboxes; run it
  outside the sandbox there.

## Deployment

- Hosted on **Vercel**: static files plus the Python function in `api/` (Vercel
  detects it; `vercel.json` has no `builds` or `routes`, and must not get any).
- Production is `https://mike.pullen.dev/weather/`, proxied from this Vercel
  project (`weather-mike-pullen.vercel.app`) by the main site
  (`mtp13/mike.pullen.dev`). The Vercel project URL serves the app from `/`.
- All paths must stay relative. Never use root-anchored paths (`/…`) or a
  `<base>` tag.
- Only `master` is deployed (`git.deploymentEnabled` in `vercel.json`), so
  feature branches and PRs get no Vercel preview (and no `Vercel` check on PRs,
  which is expected) because the Hobby plan caps deployments at 100/day. Test on
  localhost instead. The keys are minimatch patterns: keep `"**": false` (a bare
  `*` does not match branch names containing `/`, such as `feat/x`, so they
  would still deploy) and keep the explicit `"master": true` (Vercel deploys a
  branch if any matching rule is `true`, so `master` still deploys). This only
  blocks Git-triggered deployments: CLI `vercel` deploys and deploy hooks still
  count. `tests/test_vercel_json.py` guards this. Headers and `.vercelignore`
  can only be checked with `curl` against production after merging. A change to
  the function or to `.vercelignore` also needs someone to confirm the
  production deploy succeeded after merging.
- **To opt a branch into a Vercel preview,** add it to that branch's own
  `vercel.json`, because the rule is read per branch:
  `{"master": true, "feat/x": true, "**": false}`. Pushing the branch then
  deploys it and the preview URL appears on the PR. Every deployment counts
  against the 100/day budget, so drop the entry when the branch is finished.
- `.vercelignore` excludes `package.json`, `package-lock.json`, tests and
  tooling configs, so Vercel skips `npm install`. It must **not** exclude
  `pyproject.toml`, `uv.lock`, `.python-version`, `README.md` (the
  `pyproject.toml` readme), `api/` or `itinerary.json`, because the Python build
  needs them. If you add a tooling file, add it to `.vercelignore`.
- Security headers (strict CSP, `X-Content-Type-Options`, `Referrer-Policy`,
  `Permissions-Policy`) and the `index.html` cache rule live in `vercel.json`.
  Never commit secrets.

## Git & GitHub

- Commit locally as often as you like, but push once per unit of work: every
  push to `master` is a Vercel deployment and every PR push is a CI run. Don't
  push WIP commits, and batch review fixes into one push.
- The repo is on GitHub at `mtp13/weather` (remote `origin`), and `master` is
  the default branch (it stays `master`). The repo is public, so never commit
  secrets.
- Before making changes, check the current branch. If you're on `master`, create
  a feature branch first (`feat/…`, `fix/…`, `chore/…`, `docs/…`). If you're
  already on a feature branch for related work, keep using it. Once a PR is
  merged, start new work on a fresh branch from an up-to-date `master`, and
  never push to a merged branch.
- When the work is finished, run `uv run ruff format .`, `uv run ruff check .`,
  `uv run pytest`, `npm run format`, `npm run lint`, `npm test` and
  `npm run test:e2e`. Commit only once all of them pass, then push the branch
  and open a pull request against `master` with `gh pr create`. Every commit
  must be formatted, not just the last one before a PR. Give the PR a summary
  and test notes. You don't need to ask first. If a PR is already open for the
  branch, push to update it.
- Use the `gh` CLI for PRs, issues and checking CI runs. Each PR runs CI through
  GitHub Actions; check it with `gh pr checks` and fix any failures.
- Never commit to, push to or force-push `master` directly.
