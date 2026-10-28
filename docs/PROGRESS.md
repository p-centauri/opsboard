# Progress

_Last updated: 2026-10-28_

## Done: Milestone 1 (foundation)
- Repo, Docker Compose (db + api), Dockerfile with dev and prod (non-root) targets
- Schema for all 6 tables with constraints, indexes and naming convention; Alembic migration `0001`
- Deterministic seed: 1k customers, 300 products, 100k orders in about 10 s
  (`make seed` / `make reseed`)
- `GET /health` (200, or 503 with the error shape)
- Makefile + make.ps1, GitHub Actions CI (lint, tests, prod image build)
- 40 tests: constraints, migrations (drift + down/up), seed (determinism, invariants,
  atomicity, CLI), health

## Next: Milestone 2 (API)
1. Error shape and exception handlers; settings for the cookie/JWT secret
2. Auth: login/logout/me, httpOnly cookie, login rate limit, role dependency
3. Customers and products CRUD, plus the low-stock filter
4. Orders: list (filters/sort/pagination), detail, create, PATCH with `version`, transitions
   with stock reservation (row locks), audit log entries
5. Analytics endpoints, CSV export (streamed)
6. Tests for each endpoint, including negative authorization tests and concurrency tests

## Known issues / notes
- `make.ps1` is untested: PowerShell isn't installed on the dev Mac. Verify on Windows.
- CI has not run yet because the repo isn't on GitHub. A GitHub username is needed to push.
- Starlette shows a deprecation warning for `httpx` in TestClient and suggests `httpx2`.
  The tests are unaffected. Evaluate the switch when the test client gets more use in M2.
