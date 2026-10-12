#!/usr/bin/env bash
# Prepare an Oracle Linux 9 (aarch64) VM to run the demo server side.
# Idempotent: safe to run again. Runs as the login user (opc) with sudo.
# Installs Docker, Node, uv, the OCI CLI, git and Caddy. OpenShell is installed by
# deploy/server/openshell.sh. No secrets are handled here.
set -euo pipefail

log() { printf '== %s\n' "$*"; }

log "base packages"
sudo dnf -y -q install dnf-plugins-core git jq tar >/dev/null

log "docker"
if ! command -v docker >/dev/null; then
  sudo dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo >/dev/null
  sudo dnf -y -q install docker-ce docker-ce-cli containerd.io docker-buildx-plugin >/dev/null
fi
sudo systemctl enable --now docker >/dev/null
sudo usermod -aG docker "$USER"

log "node 22"
if ! node --version 2>/dev/null | grep -q '^v2[2-9]'; then
  sudo dnf -y -q module reset nodejs >/dev/null 2>&1 || true
  sudo dnf -y -q module enable nodejs:22 >/dev/null
  sudo dnf -y -q install nodejs npm >/dev/null
fi

log "uv"
command -v uv >/dev/null || [ -x "$HOME/.local/bin/uv" ] || curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null

log "oci cli (reads secrets from OCI Vault with the instance principal)"
command -v oci >/dev/null || "$HOME/.local/bin/uv" tool install --quiet oci-cli

log "caddy"
if ! command -v caddy >/dev/null; then
  sudo dnf -y -q copr enable @caddy/caddy epel-9-aarch64 >/dev/null
  sudo dnf -y -q install caddy >/dev/null
fi

log "firewall: 80, 443"
if systemctl is-active --quiet firewalld; then
  sudo firewall-cmd -q --permanent --add-service=http --add-service=https
  sudo firewall-cmd -q --reload
fi

log "landlock at boot"
# The UEK kernel builds Landlock but leaves it out of the active LSM list;
# OpenShell sandboxes refuse to start without it. Takes effect after reboot.
if ! grep -q landlock /sys/kernel/security/lsm; then
  sudo grubby --update-kernel=ALL --args="lsm=landlock,lockdown,capability,yama,selinux,bpf,ima,evm"
  touch "$HOME/.reboot-required"
fi

docker --version
node --version
"$HOME/.local/bin/uv" --version 2>/dev/null || uv --version
caddy version
log "bootstrap done"
