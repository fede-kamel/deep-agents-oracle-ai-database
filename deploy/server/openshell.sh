#!/usr/bin/env bash
# Install OpenShell 0.1.2 (CLI + gateway) on Oracle Linux 9 aarch64 and run
# the gateway as a user service with the Docker compute driver. Idempotent.
# No secrets: the gateway generates its own mTLS PKI.
set -euo pipefail

VER=0.1.2
ARCH=aarch64
BASE="https://github.com/NVIDIA/OpenShell/releases/download/v$VER"
log() { printf '== %s\n' "$*"; }

if ! openshell --version 2>/dev/null | grep -q "$VER"; then
  log "download and verify OpenShell $VER"
  tmp=$(mktemp -d)
  (cd "$tmp"
   for f in "openshell-$VER-1.fc44.$ARCH.rpm" "openshell-gateway-$VER-1.fc44.$ARCH.rpm" \
            openshell-checksums-sha256.txt openshell-gateway-checksums-sha256.txt; do
     curl -fsSLO "$BASE/$f"
   done
   grep -h -E "openshell(-gateway)?-$VER-1\.fc44\.$ARCH\.rpm" ./*checksums* | sha256sum -c --quiet
   sudo dnf -y -q install "./openshell-$VER-1.fc44.$ARCH.rpm" "./openshell-gateway-$VER-1.fc44.$ARCH.rpm" >/dev/null)
  rm -rf "$tmp"
fi

log "gateway config (docker driver)"
mkdir -p "$HOME/.config/openshell"
cat > "$HOME/.config/openshell/gateway.toml" <<'EOF'
# Server-side gateway. Sandbox supervisors run as Docker containers on the
# host network, so they call back on loopback (host.docker.internal does not
# resolve on Linux). The listener stays on 127.0.0.1 and requires mTLS.
[openshell]
version = 2

[openshell.gateway]
compute_driver = "docker"
bind_address = "127.0.0.1:17670"

[openshell.drivers.docker]
socket_path = "/var/run/docker.sock"
grpc_endpoint = "https://127.0.0.1:17670"
EOF

log "gateway service"
sudo loginctl enable-linger "$USER"
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
systemctl --user daemon-reload
systemctl --user enable openshell-gateway >/dev/null 2>&1
systemctl --user restart openshell-gateway
openshell gateway add --local https://127.0.0.1:17670 </dev/null >/dev/null 2>&1 || true
for _ in $(seq 1 30); do
  openshell status </dev/null >/dev/null 2>&1 && break
  sleep 2
done
openshell status </dev/null
log "openshell done"
