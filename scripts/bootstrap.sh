#!/usr/bin/env bash
# One-shot local setup: install deps, create .env, print next steps.
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v uv >/dev/null 2>&1; then
  echo "error: uv is not installed. See https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
fi

echo "==> Installing dependencies (uv sync)"
uv sync

if [ ! -f .env ]; then
  echo "==> Creating .env from .env.example"
  cp .env.example .env
else
  echo "==> .env already exists, leaving it untouched"
fi

cat <<'EOF'

Bootstrap complete. Next steps:
  make dev    # run the local stack (Docker Compose)
  make test   # run the test suite
  make lint   # lint + type-check
EOF
