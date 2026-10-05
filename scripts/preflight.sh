#!/usr/bin/env bash
# Read-only preflight: is this machine ready to run the demo?
# Prints one PASS/FAIL line per check and exits non-zero if any check fails.
# Changes nothing: no gateway, Docker, or database writes.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG="${DA_CONFIG:-$HOME/.config/deepagents-oracle-health/config.json}"
SECRETS="$(dirname "$CONFIG")/secrets"
IMAGE="${DA_SANDBOX_IMAGE:-deepagents-oracle-health:0.1}"
PROVIDER="${DA_PROVIDER:-deepagents-genai}"
fail=0

check() {
  local name="$1"; shift
  local out
  if out="$("$@" 2>&1)"; then
    printf 'PASS  %-34s %s\n' "$name" "$(printf '%s' "$out" | tail -1 | cut -c1-80)"
  else
    printf 'FAIL  %-34s %s\n' "$name" "$(printf '%s' "$out" | tail -1 | cut -c1-80)"
    fail=1
  fi
}

docker_cli() { command -v docker >/dev/null && docker "$@" || "$HOME/.rd/bin/docker" "$@"; }

check "uv"                       uv --version
check "openshell CLI"            openshell --version
check "gateway connected"        sh -c 'openshell status </dev/null | grep -q "Status: Connected" && openshell status </dev/null | grep Version'
check "sandbox image present"    sh -c "$(declare -f docker_cli); docker_cli image inspect '$IMAGE' --format '{{.Id}}' | cut -c1-19"
check "provider on gateway"      sh -c "openshell provider get '$PROVIDER' </dev/null >/dev/null && echo '$PROVIDER (key held by the gateway)'"
check "config file"              sh -c "test -f '$CONFIG' && echo '$CONFIG'"
check "secrets directory 0700"   sh -c "test \"\$(stat -f %Lp '$SECRETS' 2>/dev/null || stat -c %a '$SECRETS')\" = 700 && echo 'owner-only'"
for u in DA_OWNER DA_AGENT_X DA_AGENT_Y DA_AGENT_Z; do
  check "secret $u present"      sh -c "test -s '$SECRETS/$u' && echo 'present (not read)'"
done
check "database schema at head"  sh -c "cd '$ROOT' && uv run --quiet alembic current 2>/dev/null | grep '(head)' | sed 's/^/alembic: /'"
check "row-level security"       sh -c "cd '$ROOT' && uv run --quiet python scripts/verify.py --rls-only"
check "vector stores loaded"     sh -c "cd '$ROOT' && uv run --quiet python db/stats.py"

echo
if [ "$fail" -eq 0 ]; then echo "PREFLIGHT OK"; else echo "PREFLIGHT FAILED"; fi
exit "$fail"
