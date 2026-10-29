# Everything runs in Docker, so the only host requirements are Docker + make.
# Windows: use make.ps1 with the same task names (./make.ps1 dev).
# Dev: also loads docker-compose.override.yml (reload, bind mounts, test tools).
COMPOSE := docker compose
# Production-like images, no bind mounts.
PROD := docker compose -f docker-compose.yml
API := $(COMPOSE) run --rm --no-deps api
WEB := $(COMPOSE) run --rm --no-deps web

.DEFAULT_GOAL := help
.PHONY: help setup web-install dev run stop logs migrate seed reseed test test-api test-web \
	e2e screenshots lint lint-api lint-web format gen-api clean

help: ## List tasks
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-12s %s\n", $$1, $$2}'

.env:
	cp .env.example .env

setup: .env ## Create .env, build images, install web deps
	$(COMPOSE) build
	$(MAKE) web-install

web-install: ## Install web dependencies (inside the container)
	$(WEB) npm ci --no-audit --no-fund

dev: .env ## Start db + api + web with reload (foreground) → http://localhost:3000
	$(COMPOSE) up --build

run: .env ## Start the production-like stack in the background
	$(PROD) up --build -d

stop: ## Stop containers
	$(COMPOSE) down

logs: ## Follow container logs
	$(COMPOSE) logs -f

migrate: .env ## Apply database migrations
	$(COMPOSE) run --rm api alembic upgrade head

seed: .env migrate ## Load demo data (fails if data exists)
	$(COMPOSE) run --rm api python -m app.seed

reseed: .env migrate ## Replace all data with fresh demo data
	$(COMPOSE) run --rm api python -m app.seed --reset

test: test-api test-web ## Run all unit/integration tests

test-api: .env ## API tests against a real Postgres
	$(COMPOSE) run --rm api pytest

test-web: .env ## Web component tests (Vitest)
	$(WEB) npm test

e2e: .env ## Browser + accessibility tests on the production build (needs `make seed` once)
	$(PROD) up -d --build --wait
	$(COMPOSE) --profile e2e run --rm --no-deps e2e
	@echo "The production stack is still running; \`make dev\` switches back to dev."

screenshots: .env ## Portfolio screenshots of the prod stack → docs/screenshots (run `make run` first)
	$(COMPOSE) --profile e2e run --rm --no-deps -v "$(CURDIR)/docs/screenshots:/out" e2e node scripts/screenshots.mjs

lint: lint-api lint-web ## Lint + type check everything

lint-api: .env
	$(API) sh -c "ruff check . && ruff format --check . && mypy app tests"

lint-web: .env
	$(WEB) npm run lint

format: .env ## Auto-format and fix lint (API)
	$(API) sh -c "ruff format . && ruff check --fix ."

gen-api: .env ## Regenerate web/src/lib/api-schema.ts from the running API
	$(COMPOSE) run --rm web npm run gen:api

clean: ## Stop containers and DELETE the database volume
	$(COMPOSE) down -v
