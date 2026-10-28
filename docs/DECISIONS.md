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
