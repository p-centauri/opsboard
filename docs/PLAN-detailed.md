# OpsBoard — detailed plan

## 1. Goal and audience
Upwork clients posting "admin dashboard", "internal tool", "CRM", "inventory system",
"Next.js + FastAPI" jobs. The demo must prove, in under 60 seconds of clicking:
1. It's a real app (auth, roles, validation, errors handled), not a template.
2. It handles real data volume (100k+ orders, fast filters and charts).
3. The code is clean and tested (public repo, CI badge, README with architecture).

Mirrors confirmed experience: enterprise registries, data-heavy forms, dashboards, REST APIs,
high-load analytics. No claims about real clients anywhere in the repo.

## 2. Domain model (data model first)
| Table | Key columns | Notes |
|---|---|---|
| `users` | id, email (unique), password_hash, role (`viewer`/`manager`/`admin`), is_active | argon2 hashes |
| `customers` | id, name, email, country, created_at | trigram index on name for search |
| `products` | id, sku (unique), name, price, stock_qty, low_stock_threshold | `price` numeric(12,2) |
| `orders` | id, number (unique), customer_id, status, total, created_at, updated_at, version | indexes: (status, created_at), (customer_id, created_at), (created_at) |
| `order_items` | id, order_id, product_id, qty, unit_price | unit_price copied at order time |
| `audit_log` | id, user_id, entity, entity_id, action, diff (jsonb), created_at | append-only |

- Money: `numeric`, never float. Totals computed server-side from items.
- `version` column → optimistic locking: update sends `version`; mismatch → 409.
- Status workflow enforced server-side:
  `draft → confirmed → shipped → delivered`, `draft|confirmed → cancelled`. Confirming reserves
  stock in the same transaction (row lock on products; fails with 409 if insufficient).
- Migrations: Alembic, one migration per change, reversible.

## 3. API (FastAPI)
Explicit Pydantic input/output schemas on every endpoint (no ORM objects leaked, no mass assignment).

| Method & path | Role | Notes |
|---|---|---|
| `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` | any | httpOnly, Secure, SameSite=Lax cookie session (JWT, short TTL); rate-limited login |
| `GET /orders` | viewer+ | filters: status[], date_from/to, customer_id, min/max total, q; sort whitelist; page+page_size (max 100) |
| `GET /orders/{id}` | viewer+ | 404 for missing |
| `POST /orders`, `PATCH /orders/{id}` | manager+ | validates items, recomputes total, requires `version` on PATCH |
| `POST /orders/{id}/transition` | manager+ | body `{to, version}`; 409 on illegal transition / stale version / no stock |
| `GET /orders/export.csv` | viewer+ | same filters; streamed; row cap documented |
| `GET/POST/PATCH /customers`, `/products` | viewer read, manager write | |
| `GET /analytics/summary`, `/analytics/revenue-trend`, `/analytics/top-products`, `/analytics/status-breakdown` | viewer+ | date range params; single aggregate SQL each |
| `GET /users`, `PATCH /users/{id}` | admin | can't demote self |
| `GET /audit` | admin | paginated |
| `GET /health` | public | DB ping |

Errors: one JSON shape `{error: {code, message, fields?}}`; 422 field errors map onto form fields.

## 4. Web (Next.js)
- App Router, TypeScript strict, Tailwind with design tokens (light + dark), TanStack Query for
  server state, react-hook-form + zod (schemas mirror API), Recharts for charts.
- Pages: `/login` (with "Try as Viewer / Manager" demo buttons), `/` dashboard, `/orders`,
  `/orders/[id]`, `/orders/new`, `/customers`, `/products`, `/admin/users`, `/admin/audit`.
- Filters live in the URL (shareable, back button works). Debounced search.
- Every view has loading (skeletons, no layout shift), empty, error (with retry), and
  no-permission states; write buttons hidden/disabled by role, and the server enforces anyway.
- Accessibility: semantic tables, labelled inputs, keyboard-navigable, visible focus, WCAG 2.2 AA
  contrast. Works at 320px (registry collapses to cards on mobile).
- Load the `frontend-ui-ux` skill and run its checklist before calling the UI done.

## 5. Data & performance
- `make seed`: deterministic Faker seed — 1k customers, 300 products, ~100k orders over 2 years,
  realistic seasonality. Demo users per role.
- Target (measured, not assumed): registry and analytics endpoints p95 < 200 ms on 100k orders
  locally. Measure with a small script; fix with indexes/queries, record results in README.

## 6. Repo layout
```
opsboard/
  api/            FastAPI app (app/, alembic/, tests/), pyproject.toml
  web/            Next.js app (src/, tests/, e2e/)
  docs/           PLAN-*, ARCHITECTURE, DECISIONS, PROGRESS
  docker-compose.yml   db + api + web
  Makefile, make.ps1   dev, run, test, seed, lint, migrate, reset-demo
  .github/workflows/ci.yml
  CLAUDE.md, README.md
```

## 7. Testing
- API: pytest + httpx against a real Postgres (Compose service in CI). Covers happy paths,
  validation errors, every illegal transition, stale-version 409, stock race (two concurrent
  confirms for last unit → exactly one succeeds), authz negative tests per role and per object,
  CSV export filters.
- Web: Vitest + Testing Library for forms/filters/state rendering; Playwright e2e for
  login → filter orders → create order → confirm → see it on dashboard; viewer cannot edit.
- CI: lint (ruff, eslint), type-check (mypy/pyright-lite, tsc), tests, build images.

## 8. Deploy (milestone 4)
- Web on Vercel; API + Postgres on a managed host with a free/cheap tier (Render, Fly.io, Railway,
  Neon — pick at deploy time after checking current pricing; free tiers change).
- Public demo safety: demo users only, no sign-up, admin role not exposed publicly, write rate
  limits, scheduled reset to seed snapshot (GitHub Actions cron calling a protected reset command).
- Secrets via host env vars; `.env.example` in repo, never real values.

## 9. Upwork deliverable
- Portfolio item: title (e.g. "Operations Dashboard — Next.js + FastAPI + PostgreSQL"), role
  ("Full-stack developer — solo"), problem/solution/result description, skills tags,
  3–4 screenshots (dashboard, registry with filters, order form with validation, mobile view),
  links to live demo + GitHub.
- Same screenshots reused in proposals for matching jobs.

## 10. Decisions & trade-offs
| Decision | Why | Rejected |
|---|---|---|
| Orders/inventory domain | Most common Upwork internal-tool ask; maps to your registry/form/dashboard work | Niche gov-style domain (less relatable) |
| Monorepo, 2 apps | One repo link for clients; Compose runs everything | Separate repos |
| Cookie session (httpOnly JWT) | Safe against XSS token theft; simple for a web client | localStorage tokens |
| Offset pagination | Users need "page N of M" in registries; fine at 100k with indexes | Keyset (add only if measured slow) |
| No Redis/queues/caching | No requirement needs them yet (YAGNI); measure first | Pre-emptive caching |
| Optimistic locking | Real multi-user edit safety; shows seniority | Last-write-wins |
| Flutter later, same API | Reuses backend; second portfolio item for low cost | Building both at once |

## 11. Risks / open questions
- Free hosting cold starts make the live demo slow on first hit → note in README; consider a
  small paid instance (~$5–7/mo) if it hurts first impressions.
- GitHub account for the public repo — which username? (needed at milestone 1)
- Exact library versions chosen and verified at milestone 1, not assumed here.
