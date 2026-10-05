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
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent import settings as settings_mod  # noqa: E402
from agent.brief_agent import build_agent  # noqa: E402
from data.patients import PATIENTS  # noqa: E402


def emit(kind: str, **payload) -> None:
    print(json.dumps({"type": kind, "t": round(time.time(), 3), **payload}, default=str), flush=True)


def short(value, limit: int = 600) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return text if len(text) <= limit else text[:limit] + " ..."


def agent_label(namespace: tuple, task_names: dict[str, str]) -> str:
    """Name the graph an update came from: the lead, or the specialist it delegated to."""
    for part in namespace:
        if part.startswith("tools:"):
            return task_names.get(part.split(":", 1)[1], "specialist")
    return "lead"


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

    agent, cleanup = build_agent(cfg, display_name=profile["display_name"])
    started = time.time()
    task_names: dict[str, str] = {}
    pending_tasks: list[tuple[str, str]] = []
    counts = {"tool_calls": 0, "delegations": 0, "sql": 0, "searches": 0}
    files: dict = {}
    try:
        stream = agent.stream(
            {"messages": [{"role": "user", "content": question}]},
            stream_mode=["updates", "values"],
            subgraphs=True,
            config={"recursion_limit": 150},
        )
        for namespace, mode, chunk in stream:
            if mode == "values":
                if not namespace and isinstance(chunk, dict) and chunk.get("files"):
                    files = chunk["files"]
                continue
            who = agent_label(namespace, task_names)
            for _node, update in (chunk or {}).items():
                if not isinstance(update, dict):
                    continue
                messages = update.get("messages") or []
                if hasattr(messages, "value"):
                    messages = messages.value
                for msg in messages if isinstance(messages, list) else [messages]:
                    for call in getattr(msg, "tool_calls", None) or []:
                        counts["tool_calls"] += 1
                        name, call_args = call["name"], call.get("args", {})
                        if name == "write_todos":
                            emit("plan", agent=who, todos=call_args.get("todos", []))
                        elif name == "task":
                            counts["delegations"] += 1
                            sub = call_args.get("subagent_type", "specialist")
                            pending_tasks.append((call["id"], sub))
                            emit("delegate", agent=who, subagent=sub, request=short(call_args.get("description", ""), 1200))
                        else:
                            if name == "query_chart":
                                counts["sql"] += 1
                            if name.startswith(("search", "keyword_search")):
                                counts["searches"] += 1
                            emit("tool", agent=who, name=name, args=short(call_args, 800))
                    if getattr(msg, "type", "") == "tool":
                        emit("tool_result", agent=who, name=getattr(msg, "name", ""), preview=short(str(msg.content), 700))
            # Subgraph namespaces carry the task node's id; map them in order.
            for part in namespace:
                if part.startswith("tools:"):
                    ns_id = part.split(":", 1)[1]
                    if ns_id not in task_names and pending_tasks:
                        task_names[ns_id] = pending_tasks.pop(0)[1]
    except Exception as exc:  # noqa: BLE001
        kind = "blocked" if exc.__class__.__name__ == "PIIDetectionError" else "error"
        emit(kind, message=str(exc)[:600], error=exc.__class__.__name__)
        cleanup()
        return 2 if kind == "blocked" else 1

    cleanup()
    brief = files.get("/brief.md")
    text = ""
    if brief:
        content = brief.get("content") if isinstance(brief, dict) else getattr(brief, "content", brief)
        text = "\n".join(content) if isinstance(content, list) else str(content)
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
