#!/usr/bin/env bash
# OPERATOR STEP, in your own terminal: save the agent user's database login to
# an owner-only file the run script uploads into the sandbox (and the sandbox
# deletes after reading). The password is read without echo and never printed.
set -euo pipefail
DIR="$HOME/.config/deep-agent-sample"; FILE="$DIR/db.env"
read -rp  "TLS connect string (DSN) of the database: " DSN
read -rsp "Password of SAMPLE_AGENT_A (not echoed): " PW; echo
mkdir -p "$DIR"; chmod 700 "$DIR"
umask 077
printf 'SAMPLE_DB_DSN=%q\nSAMPLE_DB_USER=SAMPLE_AGENT_A\nSAMPLE_DB_PASSWORD=%q\nSAMPLE_PATIENT=SYN-A\n' "$DSN" "$PW" > "$FILE"
unset PW
echo "Saved $FILE (0600). Reply 'done'; do not paste this output."
