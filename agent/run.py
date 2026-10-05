"""Run the pre-visit brief agent for one patient and stream its work as JSON lines.

Each line on stdout is one event: start, plan, delegate, tool, tool_result,
brief, done, or blocked/error. The UI relays the stream to the browser; the
evidence logs keep it verbatim.

    python -m agent.run --patient X
    python -m agent.run --patient Y --question "Focus on potassium."
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent import db as agent_db  # noqa: E402
from agent import memory as agent_memory
from agent import settings as settings_mod
from agent import verify
from agent.brief_agent import build_agent
from agent.brief_schema import PreVisitBrief, render
from agent.sql_tools import CHART_TABLES
from data.patients import PATIENTS

# Gemini tends to delegate straight away; the plan is what the clinician watches.
PLAN_FIRST = (
    "\n\nBefore anything else, call write_todos with your plan, and mark each "
    "item completed as you finish it. Finish with the PreVisitBrief."
)


MAX_REPAIRS = 2
REPAIR = (
    "You wrote the draft below, and the runner cannot accept it yet:\n{problems}\n\n"
    "Fix every problem. Keep what is right. Delegate to the specialists again for any "
    "fact whose source you need to re-establish (the chart analyst can SELECT note_ref "
    "from DA_OWNER.clinical_note for note ids). Then return the complete PreVisitBrief, "
    "with a citation on every factual sentence and only ids that a search or query returned.\n\n"
    "DRAFT\n{draft}"
)


def rendered(state: dict, profile: dict, cfg) -> str:
    """The brief as Markdown: from the structured answer, else from /brief.md."""
    s = state.get("structured")
    if s is not None:
        if isinstance(s, dict):
            s = PreVisitBrief.model_validate(s)
        return render(s, profile["display_name"], cfg.patient_id, verify.BANNER_LINE)
    text = brief_text(state["files"])
    return verify.stamp_header(text, profile["display_name"], cfg.patient_id) if text else ""


def brief_text(files: dict) -> str:
    brief = files.get("/brief.md")
    if not brief:
        return ""
    content = brief.get("content") if isinstance(brief, dict) else getattr(brief, "content", brief)
    return "\n".join(content) if isinstance(content, list) else str(content)


def message_text(msg) -> str:
    content = getattr(msg, "content", "")
    if isinstance(content, list):
        parts = []
        for p in content:
            if isinstance(p, dict) and p.get("type") in ("text", "reasoning"):
                parts.append(p.get("text") or p.get("reasoning") or "")
            elif isinstance(p, str):
                parts.append(p)
        content = "\n".join(x for x in parts if x)
    reasoning = (getattr(msg, "additional_kwargs", {}) or {}).get("reasoning_content")
    text = "\n\n".join(x for x in (reasoning, content) if x)
    return text.strip()


def narrate(kind: str, payload: dict) -> str | None:
    """One readable line per agent action, for the sandbox console (stderr).

    stdout carries the JSON events for the web app; this line goes to stderr,
    which OpenShell relays as the sandbox's console output, so the console
    shows what each agent does next to the network decision it causes."""
    who = payload.get("agent") or "runner"
    one = lambda v, n=160: " ".join(str(v).split())[:n]
    if kind == "start":
        return f"[agent:lead] run started as {payload.get('db_user')} · {payload.get('model')} lead, {payload.get('worker_model')} specialists"
    if kind == "plan":
        todos = payload.get("todos") or []
        done = sum(1 for t in todos if t.get("status") == "completed")
        now = next((t.get("content", "") for t in todos if t.get("status") == "in_progress"), "")
        return f"[agent:{who}] plan · {done}/{len(todos)} done" + (f" · ▸ {one(now, 110)}" if now else "")
    if kind == "delegate":
        return f"[agent:{who}] task → {payload.get('subagent')}: {one(payload.get('request', ''), 140)}"
    if kind == "tool":
        name, args = payload.get("name", ""), payload.get("args", "")
        try:
            parsed = json.loads(args) if isinstance(args, str) else args
        except ValueError:
            parsed = {}
        if name == "query_chart":
            return f"[agent:{who}] SQL  {one(parsed.get('sql', args), 170)}"
        if name.startswith("search"):
            return f"[agent:{who}] {name} \"{one(parsed.get('query', ''), 120)}\""
        if name == "escalate_to_agent":
            return f"[agent:{who}] escalate_to_agent → {parsed.get('to_agent')} · {one(parsed.get('subject', ''), 120)}"
        if name.startswith(("propose_", "draft_")):
            label = (parsed.get("subject") or ", ".join(parsed.get("tests", []) or []) or parsed.get("visit_type", "")
                     or f"{parsed.get('change', '')} {parsed.get('medication', '')}".strip())
            return f"[agent:{who}] {name} · {one(label, 120)}"
        if name in ("write_todos", "PreVisitBrief"):
            return None
        return f"[agent:{who}] {name}"
    if kind == "tool_result":
        name, preview = payload.get("name", ""), str(payload.get("preview", ""))
        if name == "task":
            return f"[agent:{who}] ← specialist reported back ({len(preview)} chars)"
        if "policy CP-" in preview and preview.startswith("Refused"):
            return f"[agent:{who}]   ✕ POLICY {one(preview.split('policy ', 1)[1], 150)}"
        if name.startswith(("propose_", "draft_", "escalate_", "decline_")):
            return f"[agent:{who}]   → {one(preview.split('. ')[0], 130)}"
        if name == "query_chart":
            rows = preview.count("\n") + 1 if preview.startswith("{") else 0
            return f"[agent:{who}]   → {rows} rows" if rows else f"[agent:{who}]   → {one(preview, 100)}"
        if name.startswith("search"):
            return f"[agent:{who}]   → {preview.count('[Doc ID:')} hits"
        return None
    if kind == "policy":
        return f"[agent:runner] policy {payload.get('code')}: {payload.get('agent')} {payload.get('decision')} → escalate to medication-safety"
    if kind == "escalation":
        return f"[agent:runner] escalation #{payload.get('id')}: {payload.get('agent')} → {payload.get('to')}"
    if kind == "thought":
        return f"[agent:{who}] thinking: {one(payload.get('text', ''), 150)}"
    if kind == "verify":
        if payload.get("passed"):
            return f"[agent:runner] gate: accepted · {payload.get('citations')} citations, every id found in the database"
        return f"[agent:runner] gate: sent back · {one('; '.join(payload.get('problems', [])), 150)}"
    if kind == "memory":
        return ("[agent:runner] memory: brief recorded in OracleStore" if payload.get("written")
                else f"[agent:runner] memory: {payload.get('entries', 0)} entries loaded from OracleStore")
    if kind == "checkpoints":
        return f"[agent:runner] {payload.get('count')} checkpoints persisted by OracleSaver"
    if kind == "done":
        return (f"[agent:runner] done in {payload.get('seconds')} s · {payload.get('tool_calls')} tool calls · "
                f"{payload.get('sql')} SQL · {payload.get('searches')} searches · {payload.get('actions', 0)} actions proposed")
    if kind in ("error", "blocked"):
        return f"[agent:runner] {kind}: {one(payload.get('message', ''), 160)}"
    return None


def emit(kind: str, **payload) -> None:
    print(json.dumps({"type": kind, "t": round(time.time(), 3), **payload}, default=str), flush=True)
    try:
        line = narrate(kind, payload)
    except Exception:  # noqa: BLE001 - narration must never break a run
        line = None
    if line:
        print(line, file=sys.stderr, flush=True)


def short(value, limit: int = 600) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return text if len(text) <= limit else text[:limit] + " ..."


def agent_label(namespace: tuple, task_names: dict[str, str]) -> str:
    """Name the graph an update came from: the lead, or the specialist it delegated to."""
    for part in namespace:
        if part.startswith("tools:"):
            return task_names.get(part.split(":", 1)[1], "specialist")
    return "lead"


def consume(agent, content: str, config: dict, state: dict) -> None:
    """Run one user turn and emit every plan, delegation and tool event."""
    counts, task_names, pending = state["counts"], state["task_names"], state["pending"]
    stream = agent.stream(
        {"messages": [{"role": "user", "content": content}]},
        stream_mode=["updates", "values"],
        subgraphs=True,
        config=config,
    )
    for namespace, mode, chunk in stream:
        if mode == "values":
            if not namespace and isinstance(chunk, dict):
                if chunk.get("files"):
                    state["files"] = chunk["files"]
                if chunk.get("structured_response") is not None:
                    state["structured"] = chunk["structured_response"]
            continue
        who = agent_label(namespace, task_names)
        for _node, update in (chunk or {}).items():
            if not isinstance(update, dict):
                continue
            messages = update.get("messages") or []
            if hasattr(messages, "value"):
                messages = messages.value
            for msg in messages if isinstance(messages, list) else [messages]:
                # The agent's own words between tool calls: its reasoning, as
                # far as the model shares it, and a specialist's final report.
                if getattr(msg, "type", "") == "ai":
                    said = message_text(msg)
                    if said:
                        emit("thought", agent=who, text=short(said, 6000))
                for call in getattr(msg, "tool_calls", None) or []:
                    counts["tool_calls"] += 1
                    name, call_args = call["name"], call.get("args", {})
                    if name == "write_todos":
                        emit("plan", agent=who, todos=call_args.get("todos", []))
                    elif name == "task":
                        counts["delegations"] += 1
                        sub = call_args.get("subagent_type", "specialist")
                        pending.append((call["id"], sub))
                        emit("delegate", agent=who, subagent=sub, request=short(call_args.get("description", ""), 1200))
                    else:
                        if name == "query_chart":
                            counts["sql"] += 1
                        if name.startswith(("search", "keyword_search")):
                            counts["searches"] += 1
                        if name.startswith(("propose_", "draft_")):
                            counts["actions"] = counts.get("actions", 0) + 1
                        emit("tool", agent=who, name=name, args=short(call_args, 4000))
                if getattr(msg, "type", "") == "tool":
                    name, text = getattr(msg, "name", ""), str(msg.content)
                    emit("tool_result", agent=who, name=name, preview=short(text, 8000 if name == "task" else 3000))
                    policy_events(who, name, text)
        # Subgraph namespaces carry the task node's id; map them in order.
        for part in namespace:
            if part.startswith("tools:"):
                ns_id = part.split(":", 1)[1]
                if ns_id not in task_names and pending:
                    task_names[ns_id] = pending.pop(0)[1]


ESCALATION = re.compile(r"Escalation (\d+) opened for the ([\w-]+) agent")


def policy_events(who: str, name: str, text: str) -> None:
    """Surface what the database's policy decided, as its own event."""
    if text.startswith("Refused by the database") and "policy CP-03" in text:
        emit("policy", agent=who, code="CP-03", decision="refused", detail=short(text, 300))
    elif name == "escalate_to_agent" and (m := ESCALATION.search(text)):
        emit("escalation", agent=who, id=int(m.group(1)), to=m.group(2))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--patient", required=True, choices=["X", "Y", "Z"])
    parser.add_argument("--question", help="the clinician's request; defaults to the patient's scenario")
    parser.add_argument("--out", type=Path, help="also write the brief here")
    args = parser.parse_args()

    profile = PATIENTS[args.patient]
    question = args.question or profile["question"]
    cfg = settings_mod.load(args.patient)
    emit("start", patient=cfg.patient_id, display_name=profile["display_name"],
         model=cfg.chat_model, worker_model=cfg.worker_model, db_user=cfg.db_user, question=question)

    agent, agent_state, cleanup = build_agent(cfg, display_name=profile["display_name"],
                                              first_name=profile["alias"].split()[0])
    run_id = os.environ.get("DA_RUN_ID", "cli")
    prior = agent_memory.read_history(agent_state["store"], cfg.patient_id)
    emit("memory", agent="runner", entries=prior.count("\n## "), text=short(prior, 4000),
         store="OracleStore (langgraph-oracledb)", checkpointer="OracleSaver (langgraph-oracledb)")
    started = time.time()
    state = {"task_names": {}, "pending": [], "files": {}, "structured": None,
             "counts": {"tool_calls": 0, "delegations": 0, "sql": 0, "searches": 0}}

    db = agent_db.connect(user=cfg.db_user, password=cfg.db_password, dsn=cfg.dsn)
    config = {"recursion_limit": 400, "configurable": {"thread_id": f"brief-{cfg.patient_key}-{run_id}"}}
    try:
        consume(agent, question + PLAN_FIRST, config, state)
        # The runner accepts the brief only when it passes the structural and
        # grounding checks; otherwise it hands the problems back, twice at most.
        attempt = 0
        for _ in range(MAX_REPAIRS + 1):
            text = rendered(state, profile, cfg)
            issues = verify.problems(text, cfg.patient_id) if text else ["No PreVisitBrief was returned."]
            if text:
                issues += verify.action_problems(db, run_id)
                missing = verify.unresolved(db, verify.citations(text), CHART_TABLES)
                if missing:
                    issues.append(
                        "These cited ids do not exist in the database: " + ", ".join(missing)
                        + ". Cite only ids that a specialist's search or query returned; drop or re-source those claims."
                    )
            emit("verify", agent="runner", passed=not issues, problems=issues,
                 citations=len(verify.citations(text)) if text else 0, final=not issues)
            if not issues or _ == MAX_REPAIRS:
                break
            # A fresh thread: continuing after a structured answer leaves an
            # unpaired tool call that the OpenAI-compatible endpoint rejects.
            attempt += 1
            state["structured"] = None
            repair_cfg = {**config, "configurable": {"thread_id": f"{config['configurable']['thread_id']}-repair{attempt}"}}
            consume(agent, REPAIR.format(problems="\n".join(f"- {i}" for i in issues), draft=text or "(none)"), repair_cfg, state)
    except Exception as exc:  # noqa: BLE001
        kind = "blocked" if exc.__class__.__name__ == "PIIDetectionError" else "error"
        emit(kind, message=str(exc)[:600], error=exc.__class__.__name__)
        cleanup()
        return 2 if kind == "blocked" else 1
    counts = state["counts"]

    text = rendered(state, profile, cfg)
    structured = state.get("structured")
    if text and structured is not None and not verify.problems(text, cfg.patient_id):
        if isinstance(structured, dict):
            structured = PreVisitBrief.model_validate(structured)
        agent_memory.remember_brief(agent_state["store"], cfg.patient_id, run_id, structured)
        emit("memory", agent="runner", written=True, text="brief recorded in /memories/patient-history.md")
    checkpoints = sum(1 for _ in agent_state["checkpointer"].list(config))
    emit("checkpoints", agent="runner", thread_id=config["configurable"]["thread_id"], count=checkpoints)
    db.close()
    cleanup()
    if not text:
        emit("error", message="The agent finished without writing /brief.md.")
        return 1
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    emit("brief", patient=cfg.patient_id, markdown=text)
    emit("done", seconds=round(time.time() - started, 1), **counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
