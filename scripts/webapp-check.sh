#!/usr/bin/env bash
# Build the web application, start it, and drive one brief through its API the
# way the browser does: POST /api/runs, then read the Server-Sent Events stream
# to the end. Passes when the stream carried agent events and sandbox console
# lines, the run succeeded, the brief was verified, and the Word export works.
# Stops the server it started.
#
#   scripts/webapp-check.sh [X|Y|Z]        default Y; ends with WEBAPP OK
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PATIENT="${1:-Y}"
PORT="${DA_WEB_PORT:-8766}"
cd "$ROOT"

echo "$ (cd web && npm ci && npm run build)"
(cd web && npm ci --no-audit --no-fund >/dev/null 2>&1 && npm run build >/dev/null 2>&1) || { echo "ABORT: web build failed"; exit 1; }
test -f web/dist/index.html || { echo "ABORT: web/dist/index.html missing"; exit 1; }

echo "$ uvicorn ui.server:app --port $PORT"
uv run --quiet uvicorn ui.server:app --host 127.0.0.1 --port "$PORT" >out/webapp-check-server.log 2>&1 &
SERVER=$!
trap 'kill "$SERVER" 2>/dev/null || true' EXIT
for _ in $(seq 1 30); do curl -sf "http://127.0.0.1:$PORT/api/safety" >/dev/null && break; sleep 1; done

uv run --quiet python - "$PORT" "$PATIENT" <<'PY'
import json, sys, urllib.request

port, patient = sys.argv[1], sys.argv[2]
base = f"http://127.0.0.1:{port}"
checks = []

def check(name, ok, detail):
    checks.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name:<34} {detail}")

page = urllib.request.urlopen(base + "/").read().decode()
check("front end served", "<div id=\"root\">" in page, "index.html from web/dist")

cards = json.load(urllib.request.urlopen(base + "/api/patients"))
scoped = all(c.get("visible_patients") == 1 for c in cards)
check("patient cards (own DB user each)", len(cards) == 3 and scoped, ", ".join(f"{c['id']} sees {c.get('visible_patients')}" for c in cards))

req = urllib.request.Request(base + "/api/runs", data=json.dumps({"patient": patient}).encode(),
                             headers={"Content-Type": "application/json"}, method="POST")
run = json.load(urllib.request.urlopen(req))
counts = {"agent": 0, "console": 0, "allowed": 0, "denied": 0}
status, verified, kinds = None, None, set()
with urllib.request.urlopen(f"{base}/api/runs/{run['id']}/stream", timeout=900) as stream:
    for raw in stream:
        line = raw.decode().strip()
        if line.startswith("event: end"):
            break
        if not line.startswith("data: "):
            continue
        item = json.loads(line[6:])
        ch = item.get("channel")
        if ch == "agent":
            counts["agent"] += 1
            e = item["event"]
            kinds.add(e["type"])
            if e["type"] == "verify" and e.get("final"):
                verified = (e.get("passed"), e.get("citations"))
        elif ch == "console":
            counts["console"] += 1
            counts["allowed"] += "ALLOWED" in item["line"]
            counts["denied"] += "DENIED" in item["line"]
        elif ch == "status":
            status = item["status"]

check("agent channel streamed", {"start", "plan", "delegate", "tool", "brief", "done"} <= kinds, f"{counts['agent']} events: {', '.join(sorted(kinds))}")
check("sandbox console streamed", counts["console"] > 0 and counts["allowed"] > 0, f"{counts['console']} lines, {counts['allowed']} ALLOWED, {counts['denied']} DENIED")
check("run succeeded", status == "succeeded", f"status={status}")
check("brief verified by the gate", bool(verified and verified[0]), f"citations={verified[1] if verified else None}")
docx = urllib.request.urlopen(f"{base}/api/runs/{run['id']}/brief.docx").read()
check("Word export", docx[:2] == b"PK" and len(docx) > 10000, f"{len(docx)} bytes")
print(f"\n{'WEBAPP OK' if all(checks) else 'WEBAPP FAILED'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
PY
