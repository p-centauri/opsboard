# OpsBoard

An operations dashboard for orders, inventory and analytics: the kind of internal tool most
businesses run on. It's built to production standards and seeded with 100k realistic orders,
so performance is measured on real data volume, not a toy dataset.

> **Status:** milestone 1 of 4 (backend foundation) is done. The API endpoints and web UI are
> next. See [docs/PROGRESS.md](docs/PROGRESS.md).

## Stack
FastAPI · SQLAlchemy 2 · PostgreSQL 17 · Alembic · Docker Compose · GitHub Actions.
Next.js web app in milestone 3.

## Quick start
Requires Docker. macOS/Linux use `make`; Windows uses `./make.ps1` with the same task names.

```bash
make setup     # create .env from .env.example, build images
make seed      # apply migrations, load 100k demo orders (~10 s)
make dev       # db + api with auto-reload → http://localhost:8000/health
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

## Layout
```
api/            FastAPI service
  app/          models.py (schema), seed.py, db.py, config.py, main.py
  alembic/      migrations
  tests/        pytest against real Postgres
docs/           plan, architecture, decisions, progress
docker-compose.yml, Makefile, make.ps1, .github/workflows/ci.yml
```

## Design highlights
- **The database enforces integrity:** uniqueness, value ranges, allowed statuses and roles,
  and foreign keys are all constraints. Tests prove each one rejects bad data.
- **Optimistic locking:** every order has a `version` column, so concurrent edits can't
  silently overwrite each other (enforced in the API from milestone 2).
- **Race-free order numbers:** `ORD-0000123` is a generated column derived from the id.
- **Deterministic, fast seed:** the same `--seed` always gives the same data. Rows are
  bulk-loaded with `COPY` in bounded batches, in a single transaction, so a failed seed
  leaves nothing behind.
- **Migrations are tested:** CI checks that models and migrations match, and that the
  schema downgrades and upgrades cleanly.

More detail: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · [docs/DECISIONS.md](docs/DECISIONS.md)
