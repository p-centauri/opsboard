#!/usr/bin/env bash
# Build and (re)start OpsBoard on a server. Safe to run repeatedly.
#   ./deploy/deploy.sh          pull, build, migrate, restart
#   ./deploy/deploy.sh --seed   same, then load demo data (first deploy only)
set -euo pipefail

cd "$(dirname "$0")/.."
compose() { docker compose -f docker-compose.yml -f deploy/docker-compose.server.yml "$@"; }

[[ -f .env ]] || { echo "Missing .env: copy deploy/.env.production.example to .env and fill it in." >&2; exit 1; }
if grep -q "CHANGE_ME" .env; then
  echo ".env still contains CHANGE_ME placeholders. Fill in real values first." >&2
  exit 1
fi

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git pull --ff-only
fi

compose build
compose up -d db
compose run --rm api alembic upgrade head
compose up -d --remove-orphans

if [[ "${1:-}" == "--seed" ]]; then
  compose run --rm api python -m app.seed
fi

compose ps
echo "Deployed. Check: https://$(grep -E '^SITE_ADDRESS=' .env | cut -d= -f2)/login"
