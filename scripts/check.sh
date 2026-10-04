#!/usr/bin/env bash

set -euo pipefail

echo "==> Ruff"
uv run ruff check src tests

echo "==> mypy"
uv run mypy src

echo "==> pytest"
pytest_output="$(mktemp -t enterprise-rag-pytest.XXXXXX)"
pytest_report="$(mktemp -t enterprise-rag-pytest-report.XXXXXX)"
trap 'rm -f "$pytest_output" "$pytest_report"' EXIT

pytest_status=0
uv run pytest -rs --cov=src --cov-report=term-missing \
  --junitxml="$pytest_report" 2>&1 | tee "$pytest_output" || pytest_status=$?

skip_attribute="$(grep -oE 'skipped="[0-9]+"' "$pytest_report" | head -n 1 || true)"
if [[ -z "$skip_attribute" ]]; then
  echo "Could not read the skipped-test count from pytest's JUnit report." >&2
  if ((pytest_status != 0)); then
    exit "$pytest_status"
  fi
  exit 1
fi
skipped_count="${skip_attribute//[^0-9]/}"

echo "==> Test skip summary"
echo "Skipped tests: $skipped_count"
if ((skipped_count > 0)); then
  grep -E '^SKIPPED ' "$pytest_output" || true
fi

if ((pytest_status != 0)); then
  exit "$pytest_status"
fi

if [[ "${REQUIRE_INTEGRATION:-0}" == "1" ]] && ((skipped_count > 0)); then
  echo "REQUIRE_INTEGRATION=1 but $skipped_count test(s) were skipped." >&2
  exit 1
fi
