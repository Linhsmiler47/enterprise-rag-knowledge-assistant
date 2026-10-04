#!/usr/bin/env bash

set -euo pipefail

echo "==> Ruff"
uv run ruff check src tests

echo "==> mypy"
uv run mypy src

echo "==> pytest"
uv run pytest --cov=src --cov-report=term-missing
