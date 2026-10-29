# Decisions

ADR-style, newest last. Don't re-open a decision without new information.

### D1: Orders/inventory domain (2026-10-28)
It's the most common internal-tool request on Upwork, and it maps directly to past work on
registries, data-heavy forms and dashboards.

### D2: Monorepo with Docker-only toolchain (2026-10-28)
Every task runs inside containers, so the host only needs Docker and make (or PowerShell on
Windows). macOS, Windows and CI then behave the same. Rejected: local venv setup per OS.

### D3: Sync SQLAlchemy + psycopg 3 (2026-10-28)
FastAPI runs sync endpoints in a threadpool, which is ample for this load and simpler to write
and test. Revisit only if measurements show threadpool saturation. Rejected: async SQLAlchemy
(more complexity, no measured need).

### D4: Integrity in the database, not just code (2026-10-28)
Uniqueness, ranges and allowed values are constraints with deterministic names (a naming
convention), so no code path, race or manual SQL can break them. Status and role are
`text` + `CHECK` rather than a Postgres enum, because adding a value is then a simple migration.

### D5: Order number as a generated column (2026-10-28)
`'ORD-' || lpad(id, 7, '0')` is unique by construction. Rejected: computing "max + 1" in the
app, which is a check-then-act race.

### D6: Identity `BY DEFAULT` + COPY seeding (2026-10-28)
The seed provides explicit ids so parent and child rows can be bulk-loaded without
round-trips, then it advances the sequences. 100k orders take about 10 s.

### D7: Plain requirements files with exact pins (2026-10-28)
The API is an app, not a library, so no build backend is needed. `pyproject.toml` holds tool
config only. Rejected: Poetry or uv (extra tooling with no current need).

### D8: Server-side sessions instead of JWT (2026-10-28)
The cookie holds a random 256-bit token. Postgres stores only its SHA-256, with an expiry.
Logout, deactivation and role changes revoke sessions immediately, and every API replica sees
the same state. The cost is one indexed lookup per request. Rejected: JWT, because it can't be
revoked before it expires without adding a denylist, which is server state anyway, and it
would need a new dependency.

### D9: Login rate limit in Postgres, keyed by email+IP and by IP (2026-10-28)
Five failures per email+IP and 30 per IP in 15 minutes. Keying by email alone would let anyone
lock the public demo accounts. It's a soft limit: concurrent attempts can overshoot by a few.
Rejected: Redis, since there's no other need for it yet; in-process counters, which break
with 2+ replicas.

### D10: Revenue counts booked orders only (2026-10-28)
Revenue, order counts, trends, top products and customer lifetime value include only
confirmed, shipped and delivered orders (`BOOKED_STATUSES`). Drafts aren't sales and
cancelled orders never were. The cancellation rate uses all orders.

### D11: Money is a JSON string; times and dates are UTC (2026-10-28)
`"12.50"`, never a float, so clients never see binary rounding. Date filters are UTC days, and
`date_to` is inclusive.

### D12: Same-origin web app, no CORS (2026-10-28)
In M3, Next.js will proxy `/api/*` to the API, so the session cookie is first-party and
SameSite=Lax plus JSON-only bodies cover CSRF. The API therefore enables no CORS.

### D13: Caddy edge proxy owns the client IP (2026-10-28)
Measured: the Next.js rewrite proxy passed a client-supplied `X-Forwarded-For` through
unchanged (so the rate limit could be bypassed with fake IPs), and without that header the API
saw every user as the web container (so 30 failures from anyone would lock out everyone).
Self-hosted Next can't read the socket address in rewrites, `proxy.ts` or route handlers. So
Caddy (`edge`) is the only published entry point: it sets `X-Forwarded-For` from the TCP
connection and discards client values. Next forwards that header, and the API trusts it.
Verified: a spoofed header was ignored and the real connection IP was recorded.
**Deployment must keep this invariant:** web and api reachable only through a proxy that
overwrites `X-Forwarded-For`.

### D14: API types generated from OpenAPI (2026-10-28)
`make gen-api` writes `web/src/lib/api-schema.ts` from FastAPI's schema with
`openapi-typescript`, so the frontend and backend can't silently drift apart. The generated
file is committed, and regenerated whenever an API schema changes.

### D15: TypeScript 5.9, not 7.0 (2026-10-28)
npm `latest` is the 7.0 native port, but `openapi-typescript` declares `typescript ^5`, and
Next's type-checking uses the TypeScript JS API. Revisit when both support 7.

### D16: Dashboard ranges are complete UTC days ending yesterday (2026-10-28)
Including today showed the partial day as a revenue cliff, and biased every period-over-period
delta downward (seen in the first browser check). Revenue figures are whole dollars on tiles,
exact elsewhere.

### D17: Client data via TanStack Query; filters in the URL (2026-10-28)
The UI is an authenticated internal tool, so pages are client components that fetch through
typed hooks (`lib/queries.ts`). Previous results stay visible while the next page loads.
Retries happen only on network/5xx errors, and any 401 sends the user to `/login?next=…`
(validated against open redirects). Filters, sort and page live in the query string, so views
are shareable and the back button works.
