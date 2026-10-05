#!/usr/bin/env bash
# Remove what the demo created, narrowest first.
#   scripts/teardown.sh             delete leftover demo sandboxes (brief-*, probe-*)
#   scripts/teardown.sh --data      also empty the demo tables (Alembic downgrade to base)
# The database users, the embedding model and the gateway provider are removed by
# the operator: scripts/operator/db-admin.sh --drop and
# `openshell provider delete deepagents-genai`.
set -euo pipefail
cd "$(dirname "$0")/.."
openshell sandbox list </dev/null 2>/dev/null | awk 'NR>1 && $1 ~ /^(brief-[xyz]|probe)-[0-9]{6}$/ {print $1}' |
  while read -r sb; do echo "$ openshell sandbox delete $sb"; openshell sandbox delete "$sb" </dev/null || true; done
if [[ "${1:-}" == "--data" ]]; then
  echo "$ alembic downgrade base"
  uv run alembic downgrade base
fi
echo "TEARDOWN OK"
