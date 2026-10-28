# Architecture

## Components (current: milestone 1)
```
docker compose
├── db   postgres:17-alpine, volume pgdata, bound to 127.0.0.1 only
└── api  FastAPI (Dockerfile targets: dev = reload + test tools; prod = runtime deps, non-root)
```
Planned: `web` (Next.js) in M3. The API stays stateless, so it can run as 2+ replicas behind
a load balancer. Sessions use cookies, with no in-process state.

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
