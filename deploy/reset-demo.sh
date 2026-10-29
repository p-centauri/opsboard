#!/usr/bin/env bash
# Restore the public demo to fresh seed data (run nightly from cron, see docs/DEPLOY.md).
# Visitors' changes and sessions are wiped; everyone signs in again with the demo buttons.
set -euo pipefail

cd "$(dirname "$0")/.."
echo "$(date -u +%FT%TZ) resetting demo data"
docker compose -f docker-compose.yml -f deploy/docker-compose.server.yml \
  exec -T api python -m app.seed --reset
