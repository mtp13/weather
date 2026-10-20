# Deferred Review Items

Findings raised by the automated PR review (MiniMax via OpenCode) and user
feedback that are tracked across PRs. Each item lists where it came from, its
status, why it was deferred, and what to do about it.

---

## PR #7 — Deferred Items (Future Consideration)

### Deployment

#### D-1 — Branches cut before the deploy rule still create previews

- **Where:** `vercel.json` (`git.deploymentEnabled`).
- **Status:** Deferred (accepted behaviour).
- **Impact:** The rule is read from each branch's own `vercel.json`, so any
  branch pushed before PR #7 landed keeps creating preview deployments until it
  is rebased onto `master` or deleted. Each one counts against the Hobby plan's
  100 deployments/day.
- **Do:** Rebase or delete any long-lived branches that predate PR #7.

#### D-2 — CLI deploys and deploy hooks still count

- **Where:** `vercel.json` (`git.deploymentEnabled`).
- **Status:** Deferred (accepted behaviour).
- **Impact:** The rule only blocks Git-triggered deployments. A manual
  `vercel --prod` or a deploy hook still consumes the daily budget, and this
  project has no deploy hooks configured.
- **Do:** Count CLI deploys and hooks against the budget by hand.

#### D-3 — No `$schema` in `vercel.json`

- **Where:** `vercel.json`.
- **Status:** Deferred (optional).
- **Impact:** Without `"$schema": "https://openapi.vercel.sh/vercel.json"`
  editors cannot validate the `git` block, so a typo in it is only caught when a
  deployment silently does not happen.
- **Do:** Add the `$schema` key in a later change, in the same pass as any other
  `vercel.json` edit.
