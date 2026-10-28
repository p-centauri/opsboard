# Everything runs in Docker, so the only host requirements are Docker + make.
# Windows: use make.ps1 with the same task names (./make.ps1 dev).
COMPOSE := docker compose
API := $(COMPOSE) run --rm api

.DEFAULT_GOAL := help
.PHONY: help setup dev run stop logs migrate seed reseed test lint format clean

help: ## List tasks
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-8s %s\n", $$1, $$2}'

.env:
	cp .env.example .env

setup: .env ## Create .env and build images
	$(COMPOSE) build

dev: .env ## Start db + api with auto-reload (foreground)
	$(COMPOSE) up --build

run: .env ## Start db + api in the background (prod image)
	API_TARGET=prod $(COMPOSE) up --build -d

stop: ## Stop containers
	$(COMPOSE) down

logs: ## Follow container logs
	$(COMPOSE) logs -f

migrate: .env ## Apply database migrations
	$(API) alembic upgrade head

seed: .env migrate ## Load demo data (fails if data exists)
	$(API) python -m app.seed

reseed: .env migrate ## Replace all data with fresh demo data
	$(API) python -m app.seed --reset

test: .env ## Run API tests against a real Postgres
	$(API) pytest

lint: .env ## Lint, format check, type check
	$(API) sh -c "ruff check . && ruff format --check . && mypy app tests"

format: .env ## Auto-format and fix lint
	$(API) sh -c "ruff format . && ruff check --fix ."

clean: ## Stop containers and DELETE the database volume
	$(COMPOSE) down -v
