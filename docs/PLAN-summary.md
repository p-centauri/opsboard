# OpsBoard — plan at a glance

**What:** a public, production-grade internal-tools demo (orders, inventory, analytics) for the
Upwork portfolio. Shows exactly what clients hire for: data-heavy registries, forms, dashboards,
REST APIs, roles, and performance on real-sized data.

**Stack:** Next.js (App Router, TypeScript, Tailwind) · FastAPI · PostgreSQL · Docker Compose ·
GitHub Actions. Later: Flutter app on the same API.

**Features**
- Dashboard: KPI tiles, revenue trend, orders by status, top products, date-range filter (server-side aggregates)
- Orders registry: server-side pagination, sort, multi-filter, search, CSV export
- Order form: line items, client + server validation, status workflow, optimistic locking
- Customers & products CRUD; low-stock view
- Auth + roles (viewer / manager / admin), per-object authorization, audit log
- Seeded with ~100k orders so performance is real, not toy
- Live demo with one-click demo logins and scheduled data reset

**Milestones**
1. Foundation — repo, Compose, schema + migrations, seed, Makefile/make.ps1, CI
2. API — auth/RBAC, CRUD, workflow, analytics, CSV export, tests
3. Web — layout, login, dashboard, registry, forms, all UI states, tests
4. Ship — e2e, latency check on 100k rows, README + screenshots, deploy, Upwork portfolio entry
5. Later — Flutter mobile client on the same API (second portfolio item)

**Run (once built):** `make dev` · `make test` · `make seed` (Windows: `./make.ps1 dev`, etc.)

**Done =** public GitHub repo + live URL + Upwork portfolio item (title, description, skills, 3–4 screenshots).
