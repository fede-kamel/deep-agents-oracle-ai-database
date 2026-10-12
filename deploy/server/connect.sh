#!/usr/bin/env bash
# Open SSH to the demo VM through OCI Bastion, from any network. Creates a
# 3-hour port-forwarding session to the VM's private IP and forwards it to
# localhost:2222. Reuses the tunnel if it is already up.
#   deploy/server/connect.sh            # open the tunnel
#   ssh -p 2222 opc@127.0.0.1           # then use it (scp -P 2222 too)
# Reads the bastion and VM from Terraform outputs; needs the OCI profile that
# Terraform uses (oci_profile in terraform.tfvars, or OCI_PROFILE).
set -euo pipefail
cd "$(dirname "$0")/../terraform"

tfvar() { sed -nE "s/^$1 *= *\"(.*)\"/\1/p" terraform.tfvars; }
PROFILE="${OCI_PROFILE:-$(tfvar oci_profile)}"
REGION=$(tfvar region)
KEY="${SSH_KEY:-$HOME/.ssh/id_ed25519}"
PORT=2222

if ssh -p "$PORT" -i "$KEY" -o ConnectTimeout=5 -o BatchMode=yes \
     -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null opc@127.0.0.1 true 2>/dev/null; then
  echo "tunnel already up: ssh -p $PORT opc@127.0.0.1"
  exit 0
fi

# A stale forward (expired session, replaced VM) still holds the port.
pkill -f "ssh .*-L $PORT:" 2>/dev/null || true

BASTION=$(terraform output -raw bastion_id)
TARGET=$(terraform output -raw private_ip)
OCI=(--profile "$PROFILE" --auth api_key --region "$REGION")

echo "creating bastion session to $TARGET:22 ..."
SESSION=$(oci bastion session create-port-forwarding "${OCI[@]}" \
  --bastion-id "$BASTION" --display-name "ssh-$(date +%s)" \
  --target-private-ip "$TARGET" --target-port 22 \
  --ssh-public-key-file "$KEY.pub" --session-ttl 10800 \
  --wait-for-state SUCCEEDED --query 'data.resources[0].identifier' --raw-output 2>/dev/null)
HOST=$(oci bastion session get "${OCI[@]}" --session-id "$SESSION" \
  --query 'data."ssh-metadata".command' --raw-output 2>/dev/null \
  | grep -oE 'ocid1\.bastionsession[^@]+@host\.bastion\.[a-z0-9-]+\.oci\.oraclecloud\.com')

# A new session can refuse the key for a few seconds after SUCCEEDED.
for attempt in 1 2 3 4 5 6; do
  if ssh -i "$KEY" -fN -L "$PORT:$TARGET:22" \
       -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR \
       -o ServerAliveInterval=60 -o ExitOnForwardFailure=yes "$HOST"; then
    echo "tunnel up for 3 hours: ssh -p $PORT opc@127.0.0.1"
    exit 0
  fi
  echo "bastion not ready yet (attempt $attempt), retrying ..."
  sleep 10
done
echo "could not open the tunnel; session $SESSION" >&2
exit 1
