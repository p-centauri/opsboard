# Progress

_Last updated: 2026-10-29_

## Done: Milestone 1 (foundation)
Schema with DB constraints, migration 0001, deterministic 100k-order seed, `/health`, Docker
(dev/prod targets), Makefile + make.ps1, CI.

## Done: Milestone 2 (API)
- Error shape `{"error": {code, message, fields?}}` for every failure, including 404, 405,
  malformed JSON and unhandled errors (500, no details leaked)
- Auth: login/logout/me, server-side sessions (D8), hardened cookie, DB-backed rate limit
  (D9), timing-equalized unknown-email path; role dependencies (viewer < manager < admin)
- Customers and products: list (search with escaped wildcards, sort allowlist, pagination),
  detail, create, partial update (nulls and unknown fields rejected), 409 on duplicate SKU
- Orders: filters (status[], dates, customer, total range, number/customer search), sort,
  pagination; create and edit drafts (prices copied, total computed); transitions over a fixed
  graph; confirm reserves stock atomically (conditional UPDATE in product-id order), cancel
  releases it; optimistic locking via `version` (409 `stale_version`)
- Audit log for every write, in the same transaction; admin `GET /audit`
- Admin user management: role and active flag, ends that user's sessions, can't modify self
- Analytics: summary with previous-period comparison, revenue trend (day/week/month,
  zero-filled), top products, status breakdown
- CSV export: streamed in batches through a server-side cursor; CSV-injection-safe; refuses
  (422) above 100k rows instead of silently truncating
- Migration 0002 (user_sessions, login_failures)
- **242 tests**: role matrix over every route (plus a check that no route is left out),
  real concurrent races (last unit of stock; same-version edits), rollback on failed
  confirm, filters, analytics math, export, auth hardening

### Measured latency (100k orders, dev laptop, 30 requests each)
All endpoints are under the 200 ms p95 target. The slowest are order search `q` (p95 ~140 ms),
deep pages sorted by customer name (~112 ms) and the 2-year top-products query (~88 ms).
Everything else is under 66 ms.

## Done: Milestone 3 (web)
- Next.js 16 app behind a Caddy edge (D13), same-origin `/api` proxy (D12), API types
  generated from OpenAPI (D14)
- Sign-in with one-click demo accounts; session-aware shell (sidebar, or a menu on phones);
  role-aware navigation and actions; validated `next` redirect after sign-in
- Dashboard: KPI tiles with period deltas (direction shown in text, not only color), revenue
  trend (validated chart color, tooltip, table view), status breakdown, top products,
  date ranges of complete UTC days (D16)
- Orders: URL-synced filters (search, status, dates, customer), sort, pagination, cards on
  phones, CSV export with readable errors, draft editor with customer/product search,
  transitions with a cancel confirmation, stale-version and out-of-stock messages
- Customers, products (edits send only changed fields, so stock isn't overwritten), admin
  users (role, deactivation) and audit log
- Every view: loading skeletons, empty and filtered-empty states, errors with retry,
  forbidden notices
- Tests: 51 Vitest (API client, open-redirect guard, date ranges, form rules, components
  queried by role/label, login flows); 10 Playwright e2e on desktop and phone (320/412px)
  with axe WCAG 2.2 AA checks (passed twice in a row); production stack smoke-tested
- Bugs found by the checks and fixed: dev assets blocked for the `edge` host (no hydration
  in e2e), success-badge contrast 4.47:1, grid blowout causing a 46px sideways scroll at
  320px, URL-driven checkboxes snapping back (now optimistic), spoofable/shared client IP
  for the rate limit (D13)
- Checked by hand in the browser: login validation, dashboard (dark, and light at 375px), order
  create → confirm (stock −3) → cancel (stock restored), dialog focus/Escape behaviour

## Milestone 4 (ship): in progress
Done:
- Deploy kit (`deploy/`): server Compose override (only 80/443 public, restart policies,
  Caddy certificate volumes), production `.env` template, `deploy.sh` (refuses
  placeholders; build, migrate, start, optional seed), `reset-demo.sh` for nightly cron, and
  docs/DEPLOY.md
- Rehearsed a first deploy locally with the server config over real HTTPS (Caddy local CA):
  HTTP→HTTPS 308, HSTS, `Server` header stripped, `Secure` cookie, spoofed `X-Forwarded-For`
  ignored, migrate + seed + reset working
- Portfolio screenshots via `make screenshots` (6 × 1600×1200, from the production build)
- Upwork entry: docs/UPWORK-PORTFOLIO.md (title, role, description, skills, captions; every
  claim mapped to evidence)
- Found while taking screenshots, and fixed: search results from the previous query stayed
  clickable while typing (regression test confirmed failing before the fix); duplicate seeded
  product names (D19)

- e2e now runs against the production build, behind a web healthcheck: no on-demand
  compiles (dev compiles took up to 5.4 s against 5 s assertion timeouts), and it tests
  what ships. A flake was traced to the tests themselves: the wrong-password test used
  `manager@demo.local`, so repeated runs tripped the rate limit (working as designed) and
  locked the account for later tests. It now uses a unique email; 3 consecutive runs passed
  10/10.

Waiting on the owner:
1. A VPS (2 GB RAM) and a hostname pointing at it, then follow docs/DEPLOY.md
2. GitHub username, so the repo can be pushed and CI can run for the first time
3. Fill in the live-demo and GitHub links in docs/UPWORK-PORTFOLIO.md, then add the entry on
   Upwork

## Known issues / notes
- `make.ps1` is untested: PowerShell isn't installed on the dev Mac. Verify on Windows.
- CI hasn't run: the repo isn't on GitHub yet, and a GitHub username is needed to push.
- Order search `q` ORs an order-number prefix with a customer-name match, so neither index is
  used fully. It's fine at 100k (p95 ~140 ms); revisit in M4 if it grows (e.g. a UNION of two
  indexed queries).
- Product `PATCH stock_qty` sets an absolute value. The row is locked, but a manager working
  from a stale screen can overwrite a reservation made in between. Consider a
  stock-adjustment endpoint (+/- delta) if the UI needs it.
- More than 30 local `make e2e` runs within 15 minutes would trip the per-IP login cap
  (one failed sign-in per run). CI starts with a fresh database each time.
- Starlette warns that TestClient's `httpx` is deprecated in favour of `httpx2`. Harmless;
  revisit when upgrading.
- Deployment must keep D13: api/web reachable only via a proxy that overwrites
  `X-Forwarded-For`; otherwise the rate limit can be spoofed or turned into a global lockout.
