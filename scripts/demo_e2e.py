"""End-to-end demo test, through the web application's API, the way a demo runs.

    uv run uvicorn ui.server:app --port 8765 &   # the web application
    uv run python scripts/demo_e2e.py            # ends with DEMO E2E OK
    uv run python scripts/demo_e2e.py --evidence evidence   # also publish the runs

1. Reset the demo (care actions, outbox, memory, checkpoints).
2. A brief for X, Y and Z in the sandbox: each passes the gate and proposes at
   least two care actions. The care coordinator's medication change is refused
   by the database (policy CP-03) and escalated to the medication-safety
   agent, which proposes it; policy CP-02 sends that to the doctor.
3. Decide every action: the clinician approves the rest; the clinician's
   approval of the medication change is refused by the database; the doctor's
   approval executes it.
4. A second brief for Y, from memory: passes, proposes, and does not repeat an
   executed action.
Writes one JSON line per check to stdout; exits non-zero on any failure.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8765"
results: list[tuple[str, bool, str]] = []
summaries: list[dict] = []
# Published logs keep what the demo shows and drop what identifies an account.
REDACT = [(re.compile(r"ocid1\.[a-z0-9._-]+"), "<ocid>"),
          (re.compile(r"\b[a-z0-9]+_(low|medium|high|tp|tpurgent)\b"), "<service>")]


def call(method: str, path: str, body: dict | None = None):
    req = urllib.request.Request(BASE + path, data=json.dumps(body or {}).encode() if method == "POST" else None,
                                 headers={"Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


def check(name: str, ok: bool, detail: str) -> None:
    results.append((name, ok, detail))
    print(json.dumps({"check": name, "ok": ok, "detail": detail}), flush=True)


def run(patient: str, label: str) -> dict:
    _, started = call("POST", "/api/runs", {"patient": patient})
    rid, summary = started["id"], {"patient": patient, "label": label}
    with urllib.request.urlopen(f"{BASE}/api/runs/{rid}/stream", timeout=1800) as stream:
        for raw in stream:
            line = raw.decode().strip()
            if line.startswith("event: end"):
                break
            if not line.startswith("data: "):
                continue
            item = json.loads(line[6:])
            if item.get("channel") == "agent":
                e = item["event"]
                if e["type"] == "verify" and e.get("final"):
                    summary.update(passed=e.get("passed"), citations=e.get("citations"), problems=e.get("problems"))
                if e["type"] == "done":
                    summary.update({k: e.get(k) for k in ("seconds", "tool_calls", "sql", "searches", "actions")})
                if e["type"] == "memory" and not e.get("written"):
                    summary["memory_entries"] = e.get("entries")
            elif item.get("channel") == "console":
                summary["denied"] = summary.get("denied", 0) + ("DENIED" in item["line"])
                summary["agent_lines"] = summary.get("agent_lines", 0) + item["line"].startswith("[agent:")
            elif item.get("channel") == "status":
                summary["status"] = item["status"]
    summary["run"] = rid
    summaries.append(summary)
    print(json.dumps({"run": summary}), flush=True)
    return summary


def actions(patient: str, run_id: str | None = None) -> list[dict]:
    _, rows = call("GET", f"/api/patients/{patient}/actions")
    return [a for a in rows if run_id is None or a.get("run_id") == run_id]


def publish(out: Path) -> None:
    """Write evidence/flow.jsonl (one line per run, with the policy chain) and
    copy each run's event log and sandbox console, redacted, into evidence/runs/."""
    runs = out / "runs"
    for old in runs.glob("*"):
        old.unlink()
    runs.mkdir(parents=True, exist_ok=True)
    lines = []
    for s in summaries:
        p, rid, tag = s["patient"], s["run"], "second" if "second" in s["label"] else "first"
        _, log = call("GET", f"/api/patients/{p}/policy")
        mine = [a for a in actions(p, rid) if a["kind"] == "medication_change"]
        esc = [e for e in log["escalations"] if e["run_id"] == rid]
        s.update(refused=sum(e["run_id"] == rid and e["decision"] == "refused" for e in log["events"]),
                 escalation=", ".join(f"#{e['id']} {e['status']}" for e in esc) or "none",
                 doctor=", ".join(a["status"] for a in mine) or "none")
        lines.append(json.dumps(s))
        src = ROOT / "out" / "runs" / rid
        for name, dest in (("events.jsonl", f"run-{p}-{tag}.jsonl"), ("console.log", f"console-{p}-{tag}.log")):
            text = (src / name).read_text()
            for pattern, repl in REDACT:
                text = pattern.sub(repl, text)
            (runs / dest).write_text(text)
    (out / "flow.jsonl").write_text("\n".join(lines) + "\n")
    print(f"evidence written to {out}", flush=True)


def main(evidence: str | None = None) -> int:
    status, body = call("POST", "/api/demo/reset")
    check("demo reset", status == 200 and body.get("reset"), json.dumps(body))

    first: dict[str, dict] = {}
    for p in "XYZ":
        s = run(p, "first brief")
        first[p] = s
        mine = actions(p, s["run"])
        kinds = sorted(a["kind"] for a in mine)
        check(f"{p}: brief passed the gate", bool(s.get("passed")) and s.get("status") == "succeeded",
              f"citations={s.get('citations')} problems={s.get('problems')}")
        check(f"{p}: actions proposed", len(mine) >= 2, ", ".join(kinds))
        _, log = call("GET", f"/api/patients/{p}/policy")
        refused = [e for e in log["events"] if e["run_id"] == s["run"] and e["policy_code"] == "CP-03" and e["decision"] == "refused"]
        check(f"{p}: CP-03 refused the care coordinator's medication change",
              any(e["agent"] == "care-coordinator" for e in refused), "; ".join(e["detail"] for e in refused)[:160] or "none")
        escalations = [e for e in log["escalations"] if e["run_id"] == s["run"]]
        check(f"{p}: escalated to medication-safety, which resolved it",
              bool(escalations) and all(e["from_agent"] == "care-coordinator" and e["status"] != "open" for e in escalations),
              "; ".join(f"#{e['id']} {e['status']}: {e['subject']}" for e in escalations)[:160] or "none")
        med = [a for a in mine if a["kind"] == "medication_change"]
        check(f"{p}: medication-safety's change waits for the doctor (CP-02)",
              bool(med) and all(a["status"] == "needs_physician" and a["policy_code"] == "CP-02"
                                and a["proposed_agent"] == "medication-safety" and a["escalation_id"] for a in med),
              "; ".join(f"{a['title']} (escalation #{a['escalation_id']})" for a in med) or "none")
        check(f"{p}: sandbox console shows the agents, nothing denied",
              s.get("agent_lines", 0) > 10 and not s.get("denied"), f"{s.get('agent_lines')} agent lines, {s.get('denied', 0)} denied")

        for a in mine:
            if a["kind"] == "medication_change":
                st, b = call("POST", f"/api/actions/{a['id']}/approve", {"role": "clinician"})
                check(f"{p}: clinician refused on #{a['id']} (CP-02)", st == 409 and "CP-02" in str(b.get("detail")), str(b.get("detail"))[:120])
                st, b = call("POST", f"/api/actions/{a['id']}/approve", {"role": "physician"})
                check(f"{p}: doctor approves #{a['id']}", st == 200, json.dumps(b))
            else:
                decision = "reject" if (p == "Y" and a["kind"] == "patient_message") else "approve"
                st, b = call("POST", f"/api/actions/{a['id']}/{decision}", {"role": "clinician"})
                check(f"{p}: clinician {decision}s #{a['id']} ({a['kind']})", st == 200, json.dumps(b))
        after = actions(p, s["run"])
        bad = [a for a in after if a["status"] not in ("executed", "rejected")]
        trails = [" > ".join(e["status"] for e in a["events"]) for a in after if a["kind"] == "medication_change"]
        check(f"{p}: every action executed or rejected, audited", not bad, " | ".join(trails))

    second = run("Y", "second brief, with memory")
    mine = actions("Y", second["run"])
    executed_titles = {a["title"] for a in actions("Y", first["Y"]["run"]) if a["status"] == "executed"}
    check("Y again: memory loaded", (second.get("memory_entries") or 0) >= 3, f"{second.get('memory_entries')} entries")
    check("Y again: brief passed the gate", bool(second.get("passed")), f"citations={second.get('citations')}")
    check("Y again: actions proposed", len(mine) >= 2, ", ".join(sorted(a["kind"] for a in mine)))
    check("Y again: nothing executed is proposed again", not ({a["title"] for a in mine} & executed_titles),
          "; ".join(a["title"] for a in mine))

    if evidence:
        publish(Path(evidence))
    passed = sum(ok for _, ok, _ in results)
    print(f"\n{'DEMO E2E OK' if passed == len(results) else 'DEMO E2E FAILED'} ({passed}/{len(results)})")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("base", nargs="?", default=BASE, help="the web application's URL")
    ap.add_argument("--evidence", help="write flow.jsonl and redacted run logs to this directory")
    args = ap.parse_args()
    BASE = args.base
    sys.exit(main(args.evidence))
