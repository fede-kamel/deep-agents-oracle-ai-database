#!/usr/bin/env bash
# Install the demo in OCI, end to end, from the laptop:
#   1. infrastructure (Terraform: private subnet, VM, Bastion, load balancer, Vault)
#   2. secrets into OCI Vault, only those not stored yet (asks for the web login once)
#   3. the VM: packages, OpenShell, image, web app, secrets from the Vault
# Rerun any time; every step is idempotent. Needs terraform, oci, jq, ssh.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f deploy/terraform/terraform.tfvars ] || {
  echo "Copy deploy/terraform/terraform.tfvars.example to terraform.tfvars and fill it in." >&2; exit 1; }
[ -f "$HOME/.config/deepagents-oracle-health/config.json" ] || {
  echo "Missing ~/.config/deepagents-oracle-health/config.json (see codex/SPEC.md section 4)." >&2; exit 1; }

terraform -chdir=deploy/terraform init -input=false >/dev/null
terraform -chdir=deploy/terraform apply
deploy/server/operator/vault-put.sh
deploy/server/provision.sh
