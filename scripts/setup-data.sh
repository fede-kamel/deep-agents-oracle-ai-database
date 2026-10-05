#!/usr/bin/env bash
# Build the data layer, as the schema owner (no ADMIN, no secret on screen):
# Alembic migrations, the synthetic rows, then the in-database embeddings.
set -euo pipefail
cd "$(dirname "$0")/.."
# A coding agent's sandbox may not write ~/.cache; keep the dataset cache in the repo.
export HF_HOME="${HF_HOME:-$PWD/.cache/huggingface}"
echo "$ alembic upgrade head";        uv run alembic upgrade head
echo "$ python db/seed.py";           uv run python db/seed.py
echo "$ python db/embed.py";          uv run python -u db/embed.py 2>&1 | grep -v -E "Warning|Generating|examples/s"
echo "SETUP-DATA OK"
