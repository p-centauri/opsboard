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

## Next: Milestone 3 (web)
1. Next.js app (App Router, TS strict, Tailwind tokens, TanStack Query), Compose `web` service,
   `/api` proxy to the API (D12)
2. Login with "Try as Viewer / Manager" buttons; session-aware layout; role-aware UI
3. Dashboard: KPI tiles with deltas, revenue trend, status breakdown, top products, date range
4. Orders registry with URL-synced filters, order detail, draft editor, transition buttons,
   409 handling (reload prompt)
5. Customers, products (low-stock view), admin users and audit
6. Loading/empty/error/forbidden states, 320px layout, a11y checklist; Vitest + Playwright

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
- Production deploy must set `FORWARDED_ALLOW_IPS` to the proxy, so the per-IP rate limit
  sees real client IPs (M4).
