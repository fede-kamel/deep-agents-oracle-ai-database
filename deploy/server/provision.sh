#!/usr/bin/env bash
# Provision the demo VM from the laptop, end to end, after `terraform apply`:
# tunnel, code, system packages (reboot once for Landlock), DNS cache,
# OpenShell, sandbox image, Python env, front end, web service. Idempotent.
# Secrets come from OCI Vault (store them once with
# deploy/server/operator/vault-put.sh); the VM reads them itself.
set -euo pipefail
cd "$(dirname "$0")/../.."

SSH=(ssh -p 2222 -i "${SSH_KEY:-$HOME/.ssh/id_ed25519}" -o StrictHostKeyChecking=no
     -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ServerAliveInterval=30)
on_vm() { "${SSH[@]}" opc@127.0.0.1 "$@" </dev/null; }
log() { printf '== %s\n' "$*"; }

deploy/server/connect.sh

log "code"
{ git ls-files; find deploy/server -type f; } | sort -u \
  | COPYFILE_DISABLE=1 tar -czf - -T - \
  | "${SSH[@]}" opc@127.0.0.1 'mkdir -p deepagents && tar -xzf - -C deepagents 2>/dev/null'

log "config (non-secret)"
CFG="$HOME/.config/deepagents-oracle-health/config.json"
"${SSH[@]}" opc@127.0.0.1 'mkdir -p ~/.config/deepagents-oracle-health && chmod 700 ~/.config/deepagents-oracle-health && umask 077 && cat > ~/.config/deepagents-oracle-health/config.json' < "$CFG"

log "front end (built here: npm on the VM is unreliable)"
[ -f web/dist/index.html ] || (cd web && npm ci && npm run build)
COPYFILE_DISABLE=1 tar -czf - -C web dist | "${SSH[@]}" opc@127.0.0.1 'tar -xzf - -C deepagents/web 2>/dev/null'

log "system"
on_vm 'bash deepagents/deploy/server/bootstrap.sh'
if on_vm 'test -f ~/.reboot-required'; then
  log "reboot for Landlock"
  on_vm 'rm -f ~/.reboot-required; sudo systemctl reboot' || true
  sleep 20
  until on_vm true 2>/dev/null; do sleep 5; done
fi
on_vm 'grep -q landlock /sys/kernel/security/lsm' || { echo "Landlock is not active" >&2; exit 1; }

on_vm 'bash deepagents/deploy/server/dns.sh'
on_vm 'bash deepagents/deploy/server/openshell.sh'

log "sandbox image and Python env"
on_vm 'cd deepagents && docker build -q -t deepagents-oracle-health:0.1 sandbox/ && ~/.local/bin/uv sync --quiet'

HOST=$(terraform -chdir=deploy/terraform output -raw host)
VAULT=$(terraform -chdir=deploy/terraform output -raw vault_id)
COMP=$(sed -nE 's/^compartment_id *= *"(.*)"/\1/p' deploy/terraform/terraform.tfvars)
on_vm "cd deepagents && DEMO_HOST=$HOST bash deploy/server/web.sh"
on_vm "bash deepagents/deploy/server/secrets.sh $VAULT $COMP"
log "provisioned: $(terraform -chdir=deploy/terraform output -raw url)"
