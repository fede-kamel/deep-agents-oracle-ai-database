"""Web application backend: pick a synthetic patient, run the Deep Agent in an
OpenShell sandbox, watch the sandbox console, read and download the brief.

The backend runs exactly what Codex runs, `scripts/sandbox.sh run <patient>`,
and relays its two output channels to the browser over Server-Sent Events:
stdout carries the agent's JSON events, stderr carries the sandbox console
(the OpenShell commands and the gateway's live log, including every network
decision). It never holds the OCI Generative AI key: the gateway does.

It also serves the care-action workflow: the proposals, decided as the
clinician (DA_CLINICIAN) or the doctor (DA_PHYSICIAN) through the database's
DECIDE_CARE_ACTION; the escalations and policy log; each patient's memory;
and the demo reset, which stops any run first.

    uv run uvicorn ui.server:app --port 8765
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import re
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import oracledb  # noqa: E402
from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.responses import FileResponse, Response, StreamingResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from agent import memory as agent_memory  # noqa: E402
from common.config import agent_user, load_config, password  # noqa: E402
from data.patients import PATIENTS  # noqa: E402

app = FastAPI(title="Deep Agents on Oracle AI Database")
RUNS_DIR = ROOT / "out" / "runs"
ANSI = re.compile(r"\x1b\[[0-9;]*m")


# ---------------------------------------------------------------- patients --

CARD_SQL = {
    "labs": """
        SELECT test, value, unit, TO_CHAR(collected_on, 'YYYY-MM-DD') AS on_date
        FROM (SELECT l.*, ROW_NUMBER() OVER (PARTITION BY test ORDER BY collected_on DESC) rn
              FROM DA_OWNER.lab_result l)
        WHERE rn = 1 ORDER BY test""",
    "counts": """
        SELECT (SELECT COUNT(*) FROM DA_OWNER.medication WHERE status = 'active'),
               (SELECT COUNT(*) FROM DA_OWNER.encounter),
               (SELECT COUNT(*) FROM DA_OWNER.clinical_note),
               (SELECT COUNT(*) FROM DA_OWNER.patient)
        FROM dual""",
}


def patient_card(key: str) -> dict:
    """Read the card through the patient's own read-only user: the same
    row-level security the agent runs under decides what the card can show."""
    p = PATIENTS[key]
    card = {
        "key": key, "id": p["id"], "display_name": p["display_name"], "alias": p["alias"],
        "narrative": p.get("narrative", ""),
        "age": p["age"], "sex": p["sex"], "situation": p["situation"],
        "visit_reason": p["visit_reason"], "question": p["question"], "db_user": agent_user(key),
    }
    try:
        with oracledb.connect(user=agent_user(key), password=password(agent_user(key)),
                              dsn=load_config()["dsn"]) as conn:
            cur = conn.cursor()
            cur.execute(CARD_SQL["labs"])
            card["latest_labs"] = [
                {"test": t, "value": float(v), "unit": u, "date": d} for t, v, u, d in cur.fetchall()
            ]
            cur.execute(CARD_SQL["counts"])
            meds, encounters, notes, visible = cur.fetchone()
            card.update(active_medications=meds, encounters=encounters, notes=notes,
                        visible_patients=visible)
    except Exception as exc:  # noqa: BLE001
        card["error"] = str(exc).splitlines()[0][:200]
    return card


@app.get("/api/patients")
async def patients() -> list[dict]:
    return await asyncio.gather(*(asyncio.to_thread(patient_card, k) for k in PATIENTS))


CHART_SQL = {
    "medications": "SELECT name, dose, frequency, source, TO_CHAR(started_on, 'YYYY-MM-DD'), status "
                   "FROM DA_OWNER.medication ORDER BY status, name",
    "labs": "SELECT test, TO_CHAR(collected_on, 'YYYY-MM-DD'), value, unit FROM DA_OWNER.lab_result ORDER BY test, collected_on",
    "timeline": "SELECT TO_CHAR(e.encounter_date, 'YYYY-MM-DD'), e.kind, e.setting, n.note_ref "
                "FROM DA_OWNER.encounter e LEFT JOIN DA_OWNER.clinical_note n ON n.encounter_id = e.id ORDER BY e.encounter_date",
    "referrals": "SELECT kind, TO_CHAR(opened_on, 'YYYY-MM-DD'), status, detail FROM DA_OWNER.referral ORDER BY opened_on",
    "appointments": "SELECT TO_CHAR(scheduled_for, 'YYYY-MM-DD'), kind, status FROM DA_OWNER.appointment ORDER BY scheduled_for",
    "conditions": "SELECT description, TO_CHAR(onset_date, 'YYYY-MM-DD'), status FROM DA_OWNER.condition ORDER BY onset_date",
}


def patient_chart(key: str) -> dict:
    """The full chart, read through the patient's own read-only user."""
    out: dict = {"key": key}
    with oracledb.connect(user=agent_user(key), password=password(agent_user(key)), dsn=load_config()["dsn"]) as conn:
        cur = conn.cursor()
        for name, sql in CHART_SQL.items():
            cur.execute(sql)
            out[name] = [[float(v) if hasattr(v, "as_integer_ratio") and not isinstance(v, bool) else v for v in row]
                         for row in cur.fetchall()]
    series: dict[str, list] = {}
    for test, on, value, unit in out.pop("labs"):
        series.setdefault(test, []).append({"date": on, "value": value, "unit": unit})
    out["labs"] = series
    return out


@app.get("/api/patients/{key}/chart")
async def chart(key: str) -> dict:
    if key not in PATIENTS:
        raise HTTPException(404, "unknown patient")
    return await asyncio.to_thread(patient_chart, key)


# ------------------------------------------------------------ care actions --
# The web application acts as the clinician: DA_CLINICIAN can read the workflow
# tables and EXECUTE DECIDE_CARE_ACTION, nothing else. The agent never can.

CLINICIAN = "DA_CLINICIAN"
PHYSICIAN = "DA_PHYSICIAN"
ROLES = {"clinician": CLINICIAN, "physician": PHYSICIAN}


def clinician_conn(role: str = "clinician"):
    user = ROLES[role]
    return oracledb.connect(user=user, password=password(user), dsn=load_config()["dsn"])


def list_actions(key: str) -> list[dict]:
    pid = PATIENTS[key]["id"]
    with clinician_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, kind, status, title, rationale, citations, JSON_SERIALIZE(payload), proposed_by, "
            "TO_CHAR(created_at, 'YYYY-MM-DD\"T\"HH24:MI:SS'), result_table, result_id, result_summary, run_id, "
            "policy_code, required_role, proposed_agent, escalation_id "
            "FROM DA_OWNER.care_action WHERE patient_id = :p ORDER BY created_at DESC FETCH FIRST 30 ROWS ONLY", p=pid)
        rows = cur.fetchall()
        out = []
        for (aid, kind, status, title, rationale, cites, payload, by, at, rtab, rid, rsum, run_id, pcode, prole, pagent, esc) in rows:
            cur.execute("SELECT status, actor, TO_CHAR(at, 'YYYY-MM-DD\"T\"HH24:MI:SS'), note FROM DA_OWNER.care_action_event "
                        "WHERE action_id = :a ORDER BY id", a=aid)
            events = [{"status": s_, "actor": a_, "at": t_, "note": n_} for s_, a_, t_, n_ in cur.fetchall()]
            out.append({"id": aid, "kind": kind, "status": status, "title": title, "rationale": rationale,
                        "citations": cites or "", "payload": json.loads(payload or "{}"), "proposed_by": by,
                        "created_at": at, "run_id": run_id, "events": events,
                        "policy_code": pcode, "required_role": prole,
                        "proposed_agent": pagent, "escalation_id": esc,
                        "result": {"table": rtab, "id": rid, "summary": rsum} if rtab else None})
        return out


def decide(action_id: int, decision: str, payload: dict | None, note: str | None, role: str = "clinician") -> None:
    with clinician_conn(role) as conn:
        cur = conn.cursor()
        cur.callproc("DA_OWNER.DECIDE_CARE_ACTION",
                     [action_id, decision, json.dumps(payload) if payload else None, note])
        cur.execute("SELECT patient_id, title, result_summary FROM DA_OWNER.care_action WHERE id = :i", i=action_id)
        pid, title, result = cur.fetchone()
    # The decision becomes part of the agent's memory of this patient, so the
    # next brief knows what was approved, executed, or rejected.
    with_agent_store(pid[-1], lambda store: agent_memory.remember_decision(store, pid, action_id, title, decision, result, role))


def with_agent_store(key: str, fn):
    from langchain_oracledb.embeddings import OracleEmbeddings

    user, dsn = agent_user(key), load_config()["dsn"]
    with oracledb.connect(user=user, password=password(user), dsn=dsn) as conn:
        emb = OracleEmbeddings(conn=conn, params={"provider": "database", "model": "DA_OWNER.MINILM_L12"})
        _, store, close = agent_memory.open_state(dsn, user, password(user), emb)
        try:
            return fn(store)
        finally:
            close()


@app.get("/api/patients/{key}/memory")
async def patient_memory(key: str) -> dict:
    if key not in PATIENTS:
        raise HTTPException(404, "unknown patient")
    text = await asyncio.to_thread(with_agent_store, key, lambda store: agent_memory.read_history(store, PATIENTS[key]["id"]))
    return {"patient": PATIENTS[key]["id"], "text": text, "store": "OracleStore (langgraph-oracledb), IVF vector index"}


@app.get("/api/patients/{key}/actions")
async def actions(key: str) -> list[dict]:
    if key not in PATIENTS:
        raise HTTPException(404, "unknown patient")
    try:
        return await asyncio.to_thread(list_actions, key)
    except oracledb.DatabaseError as exc:
        raise HTTPException(503, str(exc).splitlines()[0][:200]) from exc


class Decision(BaseModel):
    payload: dict | None = None
    note: str | None = Field(default=None, max_length=500)
    role: str = Field(default="clinician", pattern="^(clinician|physician)$")


@app.post("/api/actions/{action_id}/{decision}")
async def decide_action(action_id: int, decision: str, body: Decision) -> dict:
    if decision not in ("approve", "reject"):
        raise HTTPException(400, "decision must be approve or reject")
    try:
        await asyncio.to_thread(decide, action_id, decision, body.payload, body.note, body.role)
    except oracledb.DatabaseError as exc:
        raise HTTPException(409, str(exc).splitlines()[0][:300]) from exc
    return {"id": action_id, "decision": decision}


@app.get("/api/policies")
async def policies() -> list[dict]:
    def read():
        with clinician_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT code, kind, required_role, allowed_proposer, rule_text FROM DA_OWNER.care_policy ORDER BY code")
            return [{"code": c, "kind": k, "required_role": r, "allowed_proposer": a, "rule": t}
                    for c, k, r, a, t in cur.fetchall()]
    return await asyncio.to_thread(read)


def policy_log(key: str) -> dict:
    pid = PATIENTS[key]["id"]
    with clinician_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, run_id, from_agent, to_agent, policy_code, subject, reason, citations, status, "
                    "resolution, action_id, TO_CHAR(created_at, 'YYYY-MM-DD\"T\"HH24:MI:SS') "
                    "FROM DA_OWNER.agent_escalation WHERE patient_id = :p ORDER BY id DESC FETCH FIRST 30 ROWS ONLY", p=pid)
        cols = ("id", "run_id", "from_agent", "to_agent", "policy_code", "subject", "reason", "citations", "status",
                "resolution", "action_id", "created_at")
        escalations = [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]
        cur.execute("SELECT id, run_id, agent, policy_code, decision, detail, TO_CHAR(at, 'YYYY-MM-DD\"T\"HH24:MI:SS') "
                    "FROM DA_OWNER.policy_event WHERE patient_id = :p ORDER BY id DESC FETCH FIRST 50 ROWS ONLY", p=pid)
        cols = ("id", "run_id", "agent", "policy_code", "decision", "detail", "at")
        events = [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]
    return {"escalations": escalations, "events": events}


@app.get("/api/patients/{key}/policy")
async def patient_policy(key: str) -> dict:
    """The agents' escalations and every policy decision about them, from the database."""
    if key not in PATIENTS:
        raise HTTPException(404, "unknown patient")
    return await asyncio.to_thread(policy_log, key)


async def _stop(run: Run) -> None:
    """Stop a run: SIGTERM lets scripts/sandbox.sh's trap delete its sandbox."""
    run.status = "cancelled"
    await _append(run, {"channel": "console", "line": "\x1b[1;33m# web app → reset: stopping this run and deleting its sandbox\x1b[0m"})
    if run.proc and run.proc.returncode is None:
        run.proc.terminate()
        try:
            await asyncio.wait_for(run.proc.wait(), timeout=30)
        except TimeoutError:
            run.proc.kill()
    await asyncio.wait_for(run.done.wait(), timeout=30)


@app.post("/api/demo/reset")
async def reset_demo() -> dict:
    """Clear everything and start the demo again: stop any run in progress
    (its sandbox is deleted), then clear every run, care action, outbox row,
    physician order, memory and checkpoint. The charts and reference stores stay."""
    stopped = 0
    for r in list(RUNS.values()):
        if r.status == "running":
            await _stop(r)
            stopped += 1
    from db.reset_workflow import reset

    counts = await asyncio.to_thread(reset, lambda *_: None)
    RUNS.clear()
    return {"reset": True, "runs stopped": stopped, **counts}


@app.get("/api/safety")
async def safety() -> dict:
    cfg = load_config()
    return {
        "sandbox_image": "deepagents-oracle-health:0.1",
        "provider": "deepagents-genai",
        "egress": [
            {"rule": "provider deepagents-genai", "target": f"inference.generativeai.{cfg.get('genai_region', 'us-chicago-1')}.oci.oraclecloud.com:443",
             "allow": "POST/GET/DELETE /openai/v1/**", "credential": "placeholder, swapped by the proxy"},
            {"rule": "oracle_ai_database", "target": f"{cfg['db_host']}:{cfg['db_port']}",
             "allow": "TCP (TLS relayed)", "credential": "read-only user, one patient (row-level security)"},
        ],
        "binary": "/usr/local/bin/python3.12",
        "everything_else": "no rule, so no connection opens",
        "chat_model": cfg.get("chat_model", "openai.gpt-5.5"),
        "worker_model": cfg.get("worker_model", "google.gemini-2.5-flash"),
    }


# -------------------------------------------------------------------- runs --

@dataclass
class Run:
    id: str
    patient: str
    question: str
    started: float = field(default_factory=time.time)
    status: str = "running"
    lines: list[dict] = field(default_factory=list)
    brief: str | None = None
    proc: asyncio.subprocess.Process | None = None
    done: asyncio.Event = field(default_factory=asyncio.Event)
    changed: asyncio.Condition = field(default_factory=asyncio.Condition)

    def summary(self) -> dict:
        return {"id": self.id, "patient": self.patient, "status": self.status,
                "started": self.started, "has_brief": self.brief is not None}


RUNS: dict[str, Run] = {}


class RunRequest(BaseModel):
    patient: str = Field(pattern="^[XYZ]$")
    question: str | None = Field(default=None, max_length=2000)


async def _append(run: Run, item: dict) -> None:
    run.lines.append(item)
    async with run.changed:
        run.changed.notify_all()


async def _pump(run: Run, stream: asyncio.StreamReader, channel: str, log) -> None:
    while line := await stream.readline():
        text = line.decode(errors="replace").rstrip("\n")
        log.write(text + "\n")
        if channel == "agent":
            try:
                event = json.loads(text)
            except ValueError:
                await _append(run, {"channel": "console", "line": text})
                continue
            if event.get("type") == "brief":
                run.brief = event.get("markdown", "")
            await _append(run, {"channel": "agent", "event": event})
        else:
            await _append(run, {"channel": "console", "line": text})


async def _execute(run: Run) -> None:
    run_dir = RUNS_DIR / run.id
    run_dir.mkdir(parents=True, exist_ok=True)
    cmd = [str(ROOT / "scripts" / "sandbox.sh"), "run", run.patient]
    if run.question:
        cmd.append(run.question)
    await _append(run, {"channel": "console", "line": f"\x1b[1;36m# web app → scripts/sandbox.sh run {run.patient}\x1b[0m"})
    proc = run.proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=ROOT, stdin=asyncio.subprocess.DEVNULL, env={**os.environ, "DA_RUN_ID": run.id},
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    with open(run_dir / "events.jsonl", "w") as ev, open(run_dir / "console.log", "w") as con:
        await asyncio.gather(_pump(run, proc.stdout, "agent", ev), _pump(run, proc.stderr, "console", con))
    code = await proc.wait()
    if run.status != "cancelled":
        run.status = "succeeded" if code == 0 and run.brief else ("blocked" if code == 2 else "failed")
    if run.brief:
        (run_dir / f"brief-{run.patient}.md").write_text(run.brief)
    await _append(run, {"channel": "status", "status": run.status, "exit_code": code})
    run.done.set()


@app.post("/api/runs")
async def start_run(req: RunRequest) -> dict:
    if any(r.status == "running" for r in RUNS.values()):
        raise HTTPException(409, "A run is already in progress; one sandbox at a time.")
    run = Run(id=time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6], patient=req.patient,
              question=(req.question or "").strip())
    RUNS[run.id] = run
    asyncio.create_task(_execute(run))
    return run.summary()


@app.get("/api/runs")
async def list_runs() -> list[dict]:
    return [r.summary() for r in sorted(RUNS.values(), key=lambda r: r.started, reverse=True)]


@app.get("/api/runs/{run_id}/stream")
async def stream(run_id: str):
    run = RUNS.get(run_id) or _missing()

    async def events():
        sent = 0
        while True:
            while sent < len(run.lines):
                yield f"data: {json.dumps(run.lines[sent], default=str)}\n\n"
                sent += 1
            if run.done.is_set() and sent >= len(run.lines):
                yield "event: end\ndata: {}\n\n"
                return
            async with run.changed:
                try:
                    await asyncio.wait_for(run.changed.wait(), timeout=15)
                except TimeoutError:
                    yield ": keep-alive\n\n"

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def _missing():
    raise HTTPException(404, "unknown run")


@app.get("/api/runs/{run_id}/brief.md")
async def brief_md(run_id: str):
    run = RUNS.get(run_id) or _missing()
    if not run.brief:
        raise HTTPException(404, "no brief yet")
    return Response(run.brief, media_type="text/markdown",
                    headers={"Content-Disposition": f'attachment; filename="pre-visit-brief-{run.patient}.md"'})


@app.get("/api/runs/{run_id}/brief.docx")
async def brief_docx(run_id: str):
    run = RUNS.get(run_id) or _missing()
    if not run.brief:
        raise HTTPException(404, "no brief yet")
    from ui.docx_export import markdown_to_docx

    buf = io.BytesIO()
    markdown_to_docx(run.brief, buf, footer=f"Run {run.id} · synthetic data · OpenShell sandbox · Oracle AI Database 26ai")
    return Response(buf.getvalue(),
                    media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f'attachment; filename="pre-visit-brief-{run.patient}.docx"'})


# ------------------------------------------------------------------ static --

DIST = ROOT / "web" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    async def spa(path: str):
        target = DIST / path
        return FileResponse(target if path and target.is_file() else DIST / "index.html")
