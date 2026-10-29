# OpsBoard: project map

Portfolio demo: internal tool for orders/inventory/analytics. Next.js web + FastAPI +
PostgreSQL behind a Caddy edge. Flutter client later.

**Resume ritual:** read `docs/PROGRESS.md` first, then the doc relevant to the task.

## Layout
- `api/app/models.py`: schema; all integrity rules are DB constraints
- `api/app/routers/`: HTTP layer; `services/`: business rules; `schemas/`: Pydantic I/O
- `api/app/deps.py`: `Db`, `CurrentUser`, `Viewer`/`Manager`/`Admin` dependencies
- `api/app/errors.py`: raise `ApiError(status, code, message, fields)`; never return ad-hoc errors
- `api/app/seed.py`: deterministic demo data (pure generators + COPY writer)
- `api/app/db.py`, `config.py`: engine with connect/statement timeouts; env settings (required, no defaults)
- `api/alembic/versions/`: one migration per schema change; never edit an applied one
- `api/tests/`: pytest on real Postgres (`TEST_DATABASE_URL`, recreated per session)
- `web/src/app/(app)/`: signed-in pages; `web/src/components/ui/`: design-system components
- `web/src/lib/queries.ts`: all query keys/hooks; `api.ts`: fetch + ApiError; `api-schema.ts`: generated
- `web/e2e/`: Playwright + axe; `web/scripts/screenshots.mjs`: portfolio images
- `Caddyfile`: edge proxy (owns X-Forwarded-For, D13; HTTPS when SITE_ADDRESS is set)
- `deploy/`: server override, prod .env template, deploy/reset scripts (docs/DEPLOY.md)
- `docs/`: PLAN-summary, PLAN-detailed, ARCHITECTURE, DECISIONS, PROGRESS

## Commands (Docker only; Windows: `./make.ps1 <task>`)
`make setup | dev | run | seed | reseed | migrate | test | e2e | screenshots | lint | format | gen-api | stop | clean`
Web deps install inside the container (`make web-install`); never `npm install` on the host.

## Conventions
- Python 3.13, SQLAlchemy 2 typed ORM, sync engine (see DECISIONS).
- ruff + mypy strict must pass (`make lint`); CI runs lint, tests and the prod image build.
- Schema change: edit `models.py` → `docker compose run --rm api alembic revision --autogenerate -m "..."`
  → review the file → `make migrate`. `test_migrations_match_models` catches drift.
- Constraint names come from the naming convention in `Base.metadata`; tests match on them.
- Money is `Numeric(12,2)` / `Decimal`, never float. Times are timezone-aware UTC.
- No raw f-string SQL: use SQLAlchemy Core or `psycopg.sql.Identifier`.
- New route: add it to `ENDPOINTS` in `tests/test_permissions.py`; a guard test fails otherwise.
- Writes: lock the row, check `version` where the entity has one, `audit.record(...)`, then
  the router calls `db.commit()`.
- Tests: `client` gives one session per request on a savepoint (failed requests roll back);
  `login("manager")` signs in. Use `clean_db` only for tests that need real commits (races).
- SQLAlchemy 2.1 typing: `Select[A, B]`, not `Select[tuple[A, B]]`.
- Web: tokens only (bg-surface, text-muted, …), never raw colors. Every data view handles
  loading/empty/error. Inputs go through `<Field>` (label, hint, error wiring). New API
  fields → `make gen-api`. Filters belong in the URL (`useUrlState`).
- Web tests: Vitest + Testing Library, querying by role/label; e2e specs run axe via
  `expectAccessible(page)`.
- Pin exact dependency versions in `api/requirements*.txt`; verify a package exists before adding it.
