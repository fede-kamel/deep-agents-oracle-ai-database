#!/usr/bin/env bash
# Measure the sandbox boundary from inside: what the agent's sandbox can reach,
# and what it cannot. Creates one sandbox with the same image, provider and
# policy as a real run, runs six probes, prints PASS/FAIL, deletes the sandbox.
#
#   scripts/safety_probe.sh            # prints the report; evidence/ keeps a copy
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE="${DA_SANDBOX_IMAGE:-deepagents-oracle-health:0.1}"
PROVIDER="${DA_PROVIDER:-deepagents-genai}"
CONFIG="${DA_CONFIG:-$HOME/.config/deepagents-oracle-health/config.json}"
cfg() { python3 -c "import json,sys; print(json.load(open(sys.argv[1]))[sys.argv[2]])" "$CONFIG" "$1"; }

SB="probe-$(date +%H%M%S)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"; openshell sandbox delete "$SB" </dev/null >/dev/null 2>&1 || true' EXIT
sed -e "s|__DB_HOST__|$(cfg db_host)|" -e "s|__DB_PORT__|$(cfg db_port)|" "$ROOT/sandbox/policy.template.yaml" >"$WORK/policy.yaml"

openshell sandbox create --name "$SB" --from "$IMAGE" --provider "$PROVIDER" --policy "$WORK/policy.yaml" \
  --label app=deepagents-oracle-health --no-auto-providers --detach -- sleep infinity </dev/null >/dev/null
for _ in $(seq 1 60); do
  openshell sandbox exec --name "$SB" -- /usr/local/bin/python3.12 -c "print('ready')" </dev/null 2>/dev/null | grep -q ready && break
  sleep 2
done
for _ in $(seq 1 30); do
  openshell logs "$SB" -n 400 --source sandbox </dev/null 2>/dev/null | grep -q "Settings poll: config change detected" && break
  sleep 1
done

cat >"$WORK/probe.py" <<'PY'
import json, os, socket, sys, urllib.request, urllib.error
region, model, db_host, db_port = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
results = []

def record(name, ok, detail):
    results.append((name, ok, detail))

key = os.environ.get("OCI_GENAI_API_KEY", "")
record("key in the sandbox is a placeholder", key.startswith("openshell:resolve:"), key.split(":")[0] + ":" + key.split(":")[1] + ":..." if ":" in key else "(missing)")

req = urllib.request.Request(
    f"https://inference.generativeai.{region}.oci.oraclecloud.com/openai/v1/chat/completions",
    data=json.dumps({"model": model, "messages": [{"role": "user", "content": "Reply with the word ok."}], "max_tokens": 20}).encode(),
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "Accept-Encoding": "gzip, deflate"},
    method="POST")
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        record("OCI GenAI chat completion", r.status == 200, f"HTTP {r.status} (proxy swapped the placeholder)")
except urllib.error.HTTPError as e:
    record("OCI GenAI chat completion", False, f"HTTP {e.code}")
except Exception as e:
    record("OCI GenAI chat completion", False, repr(e)[:80])

try:
    socket.create_connection((db_host, db_port), timeout=10).close()
    record("Oracle AI Database listener", True, f"TCP {db_host}:{db_port} opened")
except Exception as e:
    record("Oracle AI Database listener", False, repr(e)[:80])

for host, port, label in [("example.com", 443, "unlisted host"),
                          (f"objectstorage.{region}.oraclecloud.com", 443, "OCI Object Storage API"),
                          ("pypi.org", 443, "package registry")]:
    try:
        socket.create_connection((host, port), timeout=10).close()
        record(f"refused: {label}", False, f"{host} connected")
    except Exception as e:
        record(f"refused: {label}", True, f"{host} -> {type(e).__name__}: {str(e)[:40]}")

try:
    req = urllib.request.Request(
        f"https://inference.generativeai.{region}.oci.oraclecloud.com/openai/v1/models",
        headers={"Authorization": f"Bearer {key}"}, method="PUT")
    urllib.request.urlopen(req, timeout=30)
    record("refused: PUT on the allowed host", False, "PUT succeeded")
except urllib.error.HTTPError as e:
    record("refused: PUT on the allowed host", e.code == 403, f"HTTP {e.code} (method not in the rules)")
except Exception as e:
    record("refused: PUT on the allowed host", True, repr(e)[:80])

for name, ok, detail in results:
    print(f"{'PASS' if ok else 'FAIL'}  {name:<40} {detail}")
print(f"\n{'PROBE OK' if all(ok for _, ok, _ in results) else 'PROBE FAILED'} ({sum(ok for _, ok, _ in results)}/{len(results)})")
PY

openshell sandbox upload "$SB" "$WORK/probe.py" /sandbox </dev/null >/dev/null
openshell sandbox exec --name "$SB" -- /usr/local/bin/python3.12 /sandbox/probe.py \
  "$(cfg genai_region)" "$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('worker_model','google.gemini-2.5-flash'))" "$CONFIG")" \
  "$(cfg db_host)" "$(cfg db_port)" </dev/null | tee "$WORK/report.txt"
echo
sleep 4
echo "gateway decisions for this sandbox:"
openshell logs "$SB" -n 400 --source sandbox </dev/null 2>/dev/null | grep -E "NET:OPEN|HTTP:(POST|PUT)" | sed -E 's/^\[[0-9.]+\] //' | cut -c1-170
grep -q "PROBE OK" "$WORK/report.txt"
