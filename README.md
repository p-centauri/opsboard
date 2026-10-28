# OpsBoard

An operations dashboard for orders, inventory and analytics: the kind of internal tool most
businesses run on. It's built to production standards and seeded with 100k realistic orders,
so performance is measured on real data volume, not a toy dataset.

> **Status:** milestones 1–2 of 4 are done: the backend foundation and a complete REST API
> with 242 tests. The web UI is next. See [docs/PROGRESS.md](docs/PROGRESS.md).

## Stack
FastAPI · SQLAlchemy 2 · PostgreSQL 17 · Alembic · Docker Compose · GitHub Actions.
Next.js web app in milestone 3.

## Quick start
Requires Docker. macOS/Linux use `make`; Windows uses `./make.ps1` with the same task names.

```bash
make setup     # create .env from .env.example, build images
make seed      # apply migrations, load 100k demo orders (~10 s)
make dev       # db + api with auto-reload → http://localhost:8000/docs
make test      # tests against a real Postgres
make lint      # ruff + mypy (strict)
```

| Task | What it does |
|---|---|
| `setup` | Create `.env`, build images |
| `dev` / `run` | Start with reload (dev image) / in background (prod image) |
| `stop`, `logs` | Stop containers / follow logs |
| `migrate` | Apply Alembic migrations |
| `seed` / `reseed` | Load demo data / replace all data with fresh demo data |
| `test`, `lint`, `format` | Tests / lint + type check / auto-format |
| `clean` | Stop and **delete the database volume** |

Demo users: `viewer@demo.local` and `manager@demo.local` (password `SEED_DEMO_PASSWORD`),
plus `admin@demo.local` (password `SEED_ADMIN_PASSWORD`). Both are set in `.env`.

## API
Interactive docs at `/docs` once running. All endpoints except `/health` and `/auth/login`
require a session cookie.

| Area | Endpoints | Role |
|---|---|---|
| Auth | `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` | any |
| Orders | `GET /orders` (filters, sort, pages), `GET /orders/export.csv`, `GET /orders/{id}` | viewer |
| | `POST /orders`, `PATCH /orders/{id}`, `POST /orders/{id}/transition` | manager |
| Customers, products | `GET` list/detail | viewer |
| | `POST`, `PATCH` | manager |
| Analytics | `/analytics/summary`, `/revenue-trend`, `/top-products`, `/status-breakdown` | viewer |
| Admin | `GET /users`, `PATCH /users/{id}`, `GET /audit` | admin |

Errors always look like `{"error": {"code": "stale_version", "message": "...", "fields": {...}}}`.

## Layout
```
api/            FastAPI service
  app/          models.py (schema), routers/ (HTTP), services/ (rules), schemas/ (I/O),
                deps.py (session, auth, roles), errors.py, seed.py
  alembic/      migrations
  tests/        pytest against real Postgres
docs/           plan, architecture, decisions, progress
docker-compose.yml, Makefile, make.ps1, .github/workflows/ci.yml
```

## Design highlights
- **The database enforces integrity:** uniqueness, value ranges, allowed statuses and roles,
  and foreign keys are all constraints. Tests prove each one rejects bad data.
- **Optimistic locking:** every order has a `version` column, so concurrent edits can't
  silently overwrite each other. A stale edit gets a 409 rather than overwriting.
- **Stock can't oversell:** confirming an order reserves stock with conditional, row-locked
  updates. A test runs two parallel requests for the last unit and confirms that exactly
  one wins.
- **Hardened auth:** server-side sessions (revocable, safe with multiple replicas), an
  httpOnly/Secure/SameSite cookie, a login rate limit that can't be used to lock out shared
  accounts, and every route covered by a role-permission test.
- **Fast on real volume:** with 100k orders every endpoint has p95 < 200 ms, and a full CSV
  export of all orders streams in about 0.5 s.
- **Race-free order numbers:** `ORD-0000123` is a generated column derived from the id.
- **Deterministic, fast seed:** the same `--seed` always gives the same data. Rows are
  bulk-loaded with `COPY` in bounded batches, in a single transaction, so a failed seed
  leaves nothing behind.
- **Migrations are tested:** CI checks that models and migrations match, and that the
  schema downgrades and upgrades cleanly.

More detail: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · [docs/DECISIONS.md](docs/DECISIONS.md)
