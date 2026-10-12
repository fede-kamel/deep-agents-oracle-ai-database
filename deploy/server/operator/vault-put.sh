#!/usr/bin/env bash
# OPERATOR STEP (your own terminal, on the laptop): store the demo's secrets
# in OCI Vault, once. The VM reads them at provisioning; nobody is asked again.
#   - database passwords: uploaded from your secrets directory, file by file
#   - GenAI key: created and sent straight to the vault, never displayed
#   - web login: asked once (hidden), stored as is; the VM hashes it for Caddy
# Existing secrets are kept. Rotate one with: --genai, --login, --db.
set -euo pipefail
cd "$(dirname "$0")/../../terraform"

tfvar() { sed -nE "s/^$1 *= *\"(.*)\"/\1/p" terraform.tfvars; }
PROFILE="${OCI_PROFILE:-$(tfvar oci_profile)}"
REGION=$(tfvar region)
COMP=$(tfvar compartment_id)
VAULT=$(terraform output -raw vault_id)
KEY=$(terraform output -raw vault_key_id)
SECRETS_DIR="$HOME/.config/deepagents-oracle-health/secrets"
OCI=(--profile "$PROFILE" --auth api_key --region "$REGION")

want_genai=0 want_login=0 want_db=0
for a in "$@"; do
  case "$a" in --genai) want_genai=1 ;; --login) want_login=1 ;; --db) want_db=1 ;; esac
done

secret_id() {
  oci vault secret list "${OCI[@]}" --compartment-id "$COMP" --vault-id "$VAULT" --name "$1" \
    --lifecycle-state ACTIVE --query 'data[0].id' --raw-output 2>/dev/null || true
}

# put NAME < value. The value goes base64 into a 0600 temp file, never argv.
put() {
  local name=$1 tmp id
  tmp=$(mktemp); chmod 600 "$tmp"
  id=$(secret_id "$name")
  if [ -n "$id" ] && [ "$id" != "null" ]; then
    jq -n --arg c "$(base64 | tr -d '\n')" '{secretContentContent:$c}' > "$tmp"
    oci vault secret update-base64 "${OCI[@]}" --secret-id "$id" --from-json "file://$tmp" >/dev/null
    echo "updated $name"
  else
    jq -n --arg c "$(base64 | tr -d '\n')" --arg comp "$COMP" --arg v "$VAULT" --arg k "$KEY" --arg n "$name" \
      '{compartmentId:$comp, vaultId:$v, keyId:$k, secretName:$n, secretContentContent:$c}' > "$tmp"
    oci vault secret create-base64 "${OCI[@]}" --from-json "file://$tmp" >/dev/null
    echo "stored $name"
  fi
  rm -f "$tmp"
}
have() { local id; id=$(secret_id "$1"); [ -n "$id" ] && [ "$id" != "null" ]; }

# Database passwords, as created by scripts/operator/db-admin.sh.
for f in "$SECRETS_DIR"/*; do
  name="deepagents-db-$(basename "$f")"
  if [ "$want_db" = 1 ] || ! have "$name"; then put "$name" < "$f"; fi
done

# GenAI key: a new key goes straight from OCI into the vault.
if [ "$want_genai" = 1 ] || ! have deepagents-genai-key; then
  oci generative-ai api-key create --profile "$PROFILE" --auth api_key --region us-chicago-1 \
    --compartment-id "$COMP" --display-name "deepagents-server-$(date +%Y%m%d%H%M)" \
    --key-details "[{\"keyName\":\"primary\",\"timeExpiry\":\"$(date -u -v+1y +%Y-%m-%dT00:00:00Z 2>/dev/null || date -u -d '+1 year' +%Y-%m-%dT00:00:00Z)\"}]" 2>/dev/null \
  | jq -r '[..|strings|select(startswith("sk-"))][0]' | tr -d '\n' | put deepagents-genai-key
fi

# Web login.
if [ "$want_login" = 1 ] || ! have deepagents-login; then
  read -rp "Web login user name: " user
  read -rsp "Web login password (not echoed): " pw; echo
  printf '%s\n%s' "$user" "$pw" | put deepagents-login
  unset pw
fi
echo "Vault is ready. New secrets can take a minute to become readable."
