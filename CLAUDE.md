# OpsBoard: project map

Portfolio demo: internal tool for orders/inventory/analytics. FastAPI + PostgreSQL now;
Next.js web (M3) and Flutter (later) follow.

**Resume ritual:** read `docs/PROGRESS.md` first, then the doc relevant to the task.

## Layout
- `api/app/models.py`: schema; all integrity rules are DB constraints
- `api/app/seed.py`: deterministic demo data (pure generators + COPY writer)
- `api/app/db.py`, `config.py`: engine with connect/statement timeouts; env settings (required, no defaults)
- `api/alembic/versions/`: one migration per schema change; never edit an applied one
- `api/tests/`: pytest on real Postgres (`TEST_DATABASE_URL`, recreated per session)
- `docs/`: PLAN-summary, PLAN-detailed, ARCHITECTURE, DECISIONS, PROGRESS

## Commands (Docker only; Windows: `./make.ps1 <task>`)
`make setup | dev | run | seed | reseed | migrate | test | lint | format | stop | clean`

## Conventions
- Python 3.13, SQLAlchemy 2 typed ORM, sync engine (see DECISIONS).
- ruff + mypy strict must pass (`make lint`); CI runs lint, tests and the prod image build.
- Schema change: edit `models.py` → `docker compose run --rm api alembic revision --autogenerate -m "..."`
  → review the file → `make migrate`. `test_migrations_match_models` catches drift.
- Constraint names come from the naming convention in `Base.metadata`; tests match on them.
- Money is `Numeric(12,2)` / `Decimal`, never float. Times are timezone-aware UTC.
- No raw f-string SQL: use SQLAlchemy Core or `psycopg.sql.Identifier`.
- Pin exact dependency versions in `api/requirements*.txt`; verify a package exists before adding it.
