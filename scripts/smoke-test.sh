#!/usr/bin/env bash
# Smoke-test a running instance. Usage: ./scripts/smoke-test.sh [BASE_URL]
set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
FAIL=0

check() {
  local path="$1"
  local expected="$2"
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' "${BASE_URL}${path}")
  if [ "$code" = "$expected" ]; then
    echo "OK   ${path} -> ${code}"
  else
    echo "FAIL ${path} -> ${code} (expected ${expected})"
    FAIL=1
  fi
}

echo "Smoke-testing ${BASE_URL}"
check "/live" 200
check "/ready" 200
check "/health" 200

exit $FAIL
