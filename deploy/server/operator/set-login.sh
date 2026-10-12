#!/usr/bin/env bash
# OPERATOR STEP (on the VM, your own terminal): set the web login. Reads the
# password without echoing it, stores only its bcrypt hash for Caddy
# (/etc/caddy/demo-auth.env, root-only), and restarts Caddy.
set -euo pipefail
read -rp "Login user name: " DEMO_USER
read -rsp "Login password (not echoed): " pw; echo
hash=$(printf '%s\n' "$pw" | caddy hash-password)
unset pw
printf 'DEMO_USER=%s\nDEMO_HASH=%s\n' "$DEMO_USER" "$hash" | sudo tee /etc/caddy/demo-auth.env >/dev/null
sudo chmod 600 /etc/caddy/demo-auth.env
sudo systemctl enable caddy >/dev/null 2>&1
sudo systemctl restart caddy
echo "login set for $DEMO_USER"
