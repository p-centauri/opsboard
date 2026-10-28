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

## Request flow (from M2)
HTTP → FastAPI route (Pydantic input schema) → auth/role check per object → SQLAlchemy
in a single transaction → Pydantic output schema. Every error uses the same shape:
`{"error": {"code", "message", "fields?"}}`.

## Seed pipeline
Pure generators (`random.Random(seed)` + seeded Faker) produce typed rows. A writer
bulk-loads them with `COPY` in batches of 10k orders, inside one transaction, and then syncs
the identity sequences. Generation is separate from I/O, so the generators are unit-tested
without a database.

## Timeouts
DB connect timeout is 5 s and statement timeout is 10 s, both configurable through
`Settings`. `pool_pre_ping` discards dead connections.
