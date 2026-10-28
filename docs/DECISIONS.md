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
