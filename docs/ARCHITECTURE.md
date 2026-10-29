# Architecture

## Components
```
browser ──► edge (Caddy, :3000 on the host) ──► web (Next.js) ──/api/*──► api (FastAPI) ──► db
             sets X-Forwarded-For (D13)          same-origin rewrite (D12)   stateless       Postgres 17
```
- `docker-compose.yml` is production-like: prod images, no bind mounts, only `edge` (and the
  API/DB on 127.0.0.1 for dev tools) published. `docker-compose.override.yml` (auto-loaded)
  adds dev targets, bind mounts and the `e2e` Playwright service.
- The API is stateless (sessions and rate limits live in Postgres), so it can run as 2+
  replicas behind a load balancer.

## Web app (`web/`)
```
src/app/            routes. (app)/ is the signed-in area (layout loads /auth/me)
  login/            sign-in + demo buttons (DEMO_PASSWORD at runtime)
src/components/ui/  design-system pieces: Button, Field, DataTable, Pagination, Notice, ...
src/lib/api.ts      fetch wrapper → ApiError {status, code, message, fields}
src/lib/queries.ts  every query key + hook; writes invalidate what they affect
src/lib/api-schema.ts  generated from OpenAPI (D14), never edited by hand
src/proxy.ts        UX redirect to /login when there's no session cookie (the API authorizes)
```
Design tokens live in `globals.css` (light + dark, AA contrast); components use token classes
only. Tables become card lists below `md`, so phones never scroll sideways.

## Data model
`users`, `customers`, `products`, `orders`, `order_items`, `audit_log`. The source of truth is
`api/app/models.py`, and the rationale is in PLAN-detailed §2.

Invariants enforced by the database:
- Unique `users.email` (lowercase), `products.sku`, `orders.number`, and (`order_id`, `product_id`).
- `CHECK` constraints: non-negative money and stock, positive qty, valid role and status,
  ISO-2 country, `version >= 1`.
- `order_items` cascade-delete with their order; other foreign keys restrict.

Invariants enforced by the application (from M2): `orders.total = Σ qty × unit_price`, the
status transition graph, stock reservation on confirm, and `version` checks on update.

Indexes support the planned queries: registry filters (`status, created_at`),
(`customer_id, created_at`), date ranges (`created_at`), top products (`order_items.product_id`),
and customer search (trigram GIN on `customers.name`).

## API layers
```
routers/   HTTP only: params, status codes, commit
services/  business rules: orders (transitions, stock, locking), analytics, auth, export
schemas/   Pydantic I/O: inputs forbid unknown fields; outputs are explicit models
deps.py    request session (rolled back unless committed), current user, role gates
errors.py  ApiError + handlers → {"error": {code, message, fields?}}
audit.py   audit rows written inside the caller's transaction
```
Request: route → `Viewer`/`Manager`/`Admin` dependency (session cookie → user → role rank)
→ input schema → service → `db.commit()` → output schema. Any exception before the commit
rolls back the whole request.

Authorization: single-tenant, so object-level access is role-level. The role matrix test
covers every route, and a guard test fails if a new route is missing from it.

## Concurrency
- Order writes lock the order row (`SELECT … FOR UPDATE`) and compare `version`, giving 409
  `stale_version` on a mismatch.
- Confirm runs `UPDATE products SET stock = stock - q WHERE id = ? AND stock >= q` in
  product-id order. The conditional update can't oversell, and the fixed order avoids deadlocks.
- Login failures and sessions live in Postgres, so limits and logout hold across replicas.

## Seed pipeline
Pure generators (`random.Random(seed)` + seeded Faker) produce typed rows. A writer
bulk-loads them with `COPY` in batches of 10k orders, inside one transaction, and then syncs
the identity sequences. Generation is separate from I/O, so the generators are unit-tested
without a database.

## Timeouts
DB connect timeout is 5 s and statement timeout is 10 s, both configurable through
`Settings`. `pool_pre_ping` discards dead connections.
