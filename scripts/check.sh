#!/usr/bin/env bash

set -euo pipefail

echo "==> Ruff"
uv run ruff check src tests

echo "==> mypy"
uv run mypy src

echo "==> pytest"
pytest_output="$(mktemp -t enterprise-rag-pytest.XXXXXX)"
trap 'rm -f "$pytest_output"' EXIT

pytest_status=0
uv run pytest -rs --cov=src --cov-report=term-missing 2>&1 | tee "$pytest_output" || pytest_status=$?
if ((pytest_status != 0)); then
  exit "$pytest_status"
fi

skip_match="$(grep -oE '[0-9]+ skipped' "$pytest_output" | tail -n 1 || true)"
skipped_count="${skip_match%% *}"
skipped_count="${skipped_count:-0}"

echo "==> Test skip summary"
echo "Skipped tests: $skipped_count"
if ((skipped_count > 0)); then
  grep -E '^SKIPPED ' "$pytest_output" || true
fi

if [[ "${REQUIRE_INTEGRATION:-0}" == "1" ]] && ((skipped_count > 0)); then
  echo "REQUIRE_INTEGRATION=1 but $skipped_count test(s) were skipped." >&2
  exit 1
fi
