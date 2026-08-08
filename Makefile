.DEFAULT_GOAL := help
IMAGE_NAME ?= enterprise-rag-knowledge-assistant
PACKAGE := enterprise_rag_knowledge_assistant

.PHONY: help setup dev down test test-unit lint fmt build ci smoke clean migrate ingest eval

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | sed 's/:.*## /\t/'

setup: ## Install dependencies and create .env if missing
	uv sync
	@test -f .env || cp .env.example .env

dev: ## Run the local stack (Docker Compose)
	docker compose -f deploy/local/docker-compose.yml -f deploy/local/docker-compose.override.yml up --build

down: ## Stop and remove the local stack
	docker compose -f deploy/local/docker-compose.yml -f deploy/local/docker-compose.override.yml down

test: ## Run the full test suite with coverage
	uv run pytest --cov=src --cov-report=term-missing

test-unit: ## Run only unit tests (no external services required)
	uv run pytest tests/unit -v

lint: ## Lint and type-check
	uv run ruff check src tests
	uv run mypy src

fmt: ## Auto-format
	uv run ruff format src tests

build: ## Build the Docker image
	docker build -t $(IMAGE_NAME):latest .

ci: lint test build ## The single target CI calls: lint + test + build

smoke: ## Smoke-test a running instance (BASE_URL=http://localhost:8000)
	./scripts/smoke-test.sh $${BASE_URL:-http://localhost:8000}

clean: ## Remove local build/cache artifacts
	rm -rf .venv .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage dist build
	find . -type d -name __pycache__ -exec rm -rf {} +

migrate: ## Create the pgvector extension and tables (idempotent)
	uv run python -m $(PACKAGE).cli init-db

ingest: ## Ingest the sample knowledge base (or DIR=<path>)
	uv run python -m $(PACKAGE).cli ingest $${DIR:-data/sample}

eval: ## Run the evaluation harness against a live provider (see docs/evaluation.md)
	uv run python scripts/evaluate.py
