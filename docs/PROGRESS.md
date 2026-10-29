# Progress

_Last updated: 2026-10-28_

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

## Next: Milestone 4 (ship)
1. Pick hosting (check current pricing). Keep D13: only the edge is public, and it
   overwrites `X-Forwarded-For`
2. Production secrets, `COOKIE_SECURE=true`, HTTPS, demo DB reset schedule
3. Push to GitHub (needs the username), make CI green, add a CI badge
4. Screenshots (dashboard, orders, editor, phone) and the Upwork portfolio entry
5. Optional performance pass on order search `q`

## Known issues / notes
- `make.ps1` is untested: PowerShell isn't installed on the dev Mac. Verify on Windows.
- CI hasn't run: the repo isn't on GitHub yet, and a GitHub username is needed to push.
- Order search `q` ORs an order-number prefix with a customer-name match, so neither index is
  used fully. It's fine at 100k (p95 ~140 ms); revisit in M4 if it grows (e.g. a UNION of two
  indexed queries).
- Product `PATCH stock_qty` sets an absolute value. The row is locked, but a manager working
  from a stale screen can overwrite a reservation made in between. Consider a
  stock-adjustment endpoint (+/- delta) if the UI needs it.
- Starlette warns that TestClient's `httpx` is deprecated in favour of `httpx2`. Harmless;
  revisit when upgrading.
- Deployment must keep D13: api/web reachable only via a proxy that overwrites
  `X-Forwarded-For`; otherwise the rate limit can be spoofed or turned into a global lockout.
