#!/usr/bin/env bash
# Install the demo's secrets on the VM from OCI Vault, using the VM's
# instance principal (deploy/terraform/vault.tf). Nothing is printed.
#   secrets.sh <vault-ocid> <compartment-ocid>
# Writes the database passwords to the owner-only secrets directory, stores
# the GenAI key in the OpenShell gateway, and sets the Caddy login.
set -euo pipefail
VAULT=$1
COMP=$2
export OCI_CLI_AUTH=instance_principal
export PATH="$HOME/.local/bin:$PATH"
SECRETS_DIR="$HOME/.config/deepagents-oracle-health/secrets"
log() { printf '== %s\n' "$*"; }

get() {
  oci secrets secret-bundle get-secret-bundle-by-name --vault-id "$VAULT" --secret-name "$1" \
    --query 'data."secret-bundle-content".content' --raw-output 2>/dev/null | base64 -d
}

log "database passwords"
mkdir -p "$SECRETS_DIR"; chmod 700 "$SECRETS_DIR"
names=$(oci vault secret list --compartment-id "$COMP" --vault-id "$VAULT" --lifecycle-state ACTIVE --all \
  --query 'data[*]."secret-name"' 2>/dev/null | jq -r '.[] | select(startswith("deepagents-db-"))')
for n in $names; do
  f="$SECRETS_DIR/${n#deepagents-db-}"
  (umask 077; get "$n" > "$f")
  echo "${n#deepagents-db-}"
done

log "GenAI key -> gateway"
# read in genai-provider.sh fails at end of input without a newline.
{ get deepagents-genai-key; echo; } | (cd "$HOME/deepagents" && scripts/operator/genai-provider.sh) >/dev/null
openshell provider get deepagents-genai </dev/null >/dev/null && echo "provider deepagents-genai ready"

log "web login -> Caddy"
login=$(get deepagents-login)
user=$(printf '%s' "$login" | head -n1)
hash=$({ printf '%s' "$login" | tail -n +2; echo; } | caddy hash-password)
unset login
printf 'DEMO_USER=%s\nDEMO_HASH=%s\n' "$user" "$hash" | sudo tee /etc/caddy/demo-auth.env >/dev/null
sudo chmod 600 /etc/caddy/demo-auth.env
sudo systemctl enable caddy >/dev/null 2>&1
sudo systemctl restart caddy
echo "login set for $user"
log "secrets done"
