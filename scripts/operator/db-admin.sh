#!/usr/bin/env bash
# OPERATOR STEP (your own terminal, not the coding agent's): one-time database
# setup as ADMIN. Reads the ADMIN password without echoing it, creates the
# schema owner and the three read-only agent users, writes their generated
# passwords to the owner-only secrets directory, and loads the in-database
# embedding model. Pass --drop to remove everything it created.
set -euo pipefail
cd "$(dirname "$0")/../.."
read -rsp "ADMIN password for the Autonomous Database (not echoed): " DA_ADMIN_PASSWORD; echo
export DA_ADMIN_PASSWORD
uv run python db/setup_admin.py "$@"
unset DA_ADMIN_PASSWORD
