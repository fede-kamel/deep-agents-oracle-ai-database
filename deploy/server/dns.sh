#!/usr/bin/env bash
# Local caching resolver for the VM, so the OpenShell sandbox proxy keeps its
# database mappings. The proxy maps the database host to a synthetic address
# for the DNS answer's remaining TTL (clamped to 1-30 s). The VCN resolver
# often answers adb.<region>.oci.oraclecloud.com with a TTL of a few seconds,
# so mappings expired between a lookup and python-oracledb's reconnect.
# Unbound keeps answers for at least 5 minutes and refreshes them before they
# expire. Upstream stays the VCN resolver. Idempotent.
set -euo pipefail
log() { printf '== %s\n' "$*"; }

log "unbound"
sudo dnf -y -q install unbound >/dev/null
sudo tee /etc/unbound/conf.d/deepagents.conf >/dev/null <<'EOF'
server:
    interface: 127.0.0.1
    access-control: 127.0.0.0/8 allow
    cache-min-ttl: 300
    prefetch: yes
    serve-expired: yes
    serve-expired-ttl: 300

forward-zone:
    name: "."
    forward-addr: 169.254.169.254
EOF
sudo unbound-checkconf >/dev/null
sudo systemctl enable --now unbound >/dev/null 2>&1
sudo systemctl restart unbound

log "use it"
# NetworkManager owns resolv.conf on Oracle Linux; tell it to use 127.0.0.1.
con=$(nmcli -g NAME,DEVICE connection show --active | awk -F: '$2!="lo" && $2!="docker0"{print $1; exit}')
sudo nmcli connection modify "$con" ipv4.ignore-auto-dns yes ipv4.dns 127.0.0.1
sudo nmcli connection up "$con" >/dev/null
grep nameserver /etc/resolv.conf
cfg="$HOME/.config/deepagents-oracle-health/config.json"
host=$([ -f "$cfg" ] && jq -r .db_host "$cfg" || echo oracle.com)
dig +noall +answer "$host" A @127.0.0.1
log "dns done"
