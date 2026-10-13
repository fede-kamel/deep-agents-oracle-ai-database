#!/usr/bin/env bash
# Run the web application as a user service on 127.0.0.1:8765 and put Caddy
# in front of it: HTTPS (Let's Encrypt) on <load-balancer-ip>.sslip.io plus basic
# auth. The login hash comes from deploy/server/operator/set-login.sh; this
# script never sees the password. Idempotent.
set -euo pipefail

REPO="$HOME/deepagents"
# The public address is the load balancer's (terraform output host); the
# VM itself is private and its outbound address is the NAT gateway's.
HOST="${DEMO_HOST:?set DEMO_HOST to the load balancer host name (terraform output -raw host)}"
log() { printf '== %s\n' "$*"; }

log "web service on 127.0.0.1:8765"
mkdir -p "$HOME/.config/systemd/user"
cat > "$HOME/.config/systemd/user/deepagents-web.service" <<EOF
[Unit]
Description=deepagents web application
After=openshell-gateway.service
Wants=openshell-gateway.service

[Service]
WorkingDirectory=$REPO
Environment=PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=$HOME/.local/bin/uv run uvicorn ui.server:app --host 127.0.0.1 --port 8765
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
systemctl --user daemon-reload
systemctl --user enable deepagents-web >/dev/null 2>&1
# A restart kills the run the server is driving. Wait for a run in progress.
while curl -fsS --max-time 5 http://127.0.0.1:8765/api/runs 2>/dev/null | grep -qE '"status": ?"running"'; do
  echo "a run is in progress; waiting before restarting the web service ..."
  sleep 30
done
systemctl --user restart deepagents-web

log "caddy for https://$HOST"
# HTTP/1.1 and HTTP/2 only: the load balancer forwards TCP, so HTTP/3 (UDP)
# can never arrive, and advertising it would make browsers try it first.
# flush_interval -1 passes the event stream through unbuffered.
sudo tee /etc/caddy/Caddyfile >/dev/null <<EOF
{
	servers {
		protocols h1 h2
	}
}

$HOST {
	basic_auth {
		{\$DEMO_USER} {\$DEMO_HASH}
	}
	reverse_proxy 127.0.0.1:8765 {
		flush_interval -1
	}
}
EOF
sudo mkdir -p /etc/systemd/system/caddy.service.d
sudo tee /etc/systemd/system/caddy.service.d/demo-auth.conf >/dev/null <<'EOF'
[Service]
EnvironmentFile=/etc/caddy/demo-auth.env
EOF
sudo systemctl daemon-reload
if sudo test -f /etc/caddy/demo-auth.env; then
  sudo systemctl enable caddy >/dev/null 2>&1
  # A running Caddy takes the new file without dropping connections.
  if systemctl is-active --quiet caddy; then sudo systemctl reload caddy; else sudo systemctl restart caddy; fi
  echo "https://$HOST"
else
  echo "login not set: run deploy/server/operator/set-login.sh on the VM, then rerun this script"
fi
log "web done"
