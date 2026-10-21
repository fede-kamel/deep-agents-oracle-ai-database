#!/usr/bin/env bash
# Run the sample agent once in a fresh OpenShell sandbox, then delete it.
#   SAMPLE_DB_HOST=<database host> ./run_in_sandbox.sh
# Needs: the image (docker build -t deep-agent-sample:0.1 sandbox/), the provider
# (operator/genai-provider.sh) and the login file (operator/save-db-login.sh).
set -euo pipefail
cd "$(dirname "$0")"
HOST="${SAMPLE_DB_HOST:?set SAMPLE_DB_HOST to the database host name}"
PORT="${SAMPLE_DB_PORT:-1521}"
IMAGE="${SAMPLE_IMAGE:-deep-agent-sample:0.1}"
PROVIDER="${SAMPLE_PROVIDER:-sample-genai}"
LOGIN="$HOME/.config/deep-agent-sample/db.env"
[[ -f "$LOGIN" ]] || { echo "ABORT: run operator/save-db-login.sh first" >&2; exit 2; }
SB="sample-$(date +%H%M%S)"
work="$(mktemp -d)"
cleanup() { openshell sandbox delete "$SB" </dev/null >/dev/null 2>&1 || true; rm -rf "${work:?}"; }
trap cleanup EXIT

sed -e "s|__DB_HOST__|$HOST|" -e "s|__DB_PORT__|$PORT|" sandbox/policy.template.yaml > "$work/policy.yaml"
# A database on a private address (a local container, for example) must be
# allowed by IP as well as by name: SAMPLE_DB_ALLOWED_IP=172.17.0.2
if [[ -n "${SAMPLE_DB_ALLOWED_IP:-}" ]]; then
  awk -v ip="$SAMPLE_DB_ALLOWED_IP" '{print} /^        tls: skip/ {print "        allowed_ips: [\"" ip "/32\"]"}' \
    "$work/policy.yaml" > "$work/policy.ip.yaml" && mv "$work/policy.ip.yaml" "$work/policy.yaml"
fi
mkdir -p "$work/app" "$work/secrets"
cp agent.py "$work/app/"
install -m 600 "$LOGIN" "$work/secrets/db.env"

echo "\$ openshell sandbox create --name $SB --from $IMAGE --provider $PROVIDER --policy policy.yaml"
openshell sandbox create --name "$SB" --from "$IMAGE" --provider "$PROVIDER" --policy "$work/policy.yaml" \
  --no-auto-providers --detach -- sleep infinity </dev/null
for _ in $(seq 1 60); do
  openshell sandbox exec --name "$SB" -- /usr/local/bin/python3.12 -c "print('ready')" </dev/null 2>/dev/null | grep -q ready && break
  sleep 2
done
# OpenShell 0.1.2: the first settings poll (about 10 s after start) closes open
# connections (NVIDIA/OpenShell#3994). Start the agent after it.
for _ in $(seq 1 30); do
  openshell logs "$SB" -n 400 --source sandbox </dev/null 2>/dev/null | grep -q "Settings poll: config change detected" && break
  sleep 1
done
openshell sandbox upload "$SB" "$work/app" /sandbox </dev/null
openshell sandbox upload "$SB" "$work/secrets" /sandbox </dev/null
echo "\$ openshell sandbox exec --name $SB -- python3.12 agent.py"
openshell sandbox exec --name "$SB" --workdir /sandbox/app -- /bin/sh -c \
  'set -a; . /sandbox/secrets/db.env; set +a; rm -f /sandbox/secrets/db.env; exec /usr/local/bin/python3.12 agent.py' </dev/null
