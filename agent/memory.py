"""Durable state for the Deep Agent, on Oracle, with langgraph-oracledb.

Two stores, both in the patient's own agent schema (DA_AGENT_<P>), where the
agent user may create tables under a small quota and nothing else:

- OracleSaver: LangGraph checkpoints. Every step of a run is persisted, so a
  repair turn resumes from the checkpoint and a run can be inspected afterwards.
- OracleStore: long-term memory with an IVF vector index over the in-database
  ONNX embeddings. The Deep Agent sees it as /memories/ through deepagents'
  StoreBackend, and loads /memories/patient-history.md into its system prompt
  at the start of every run (deepagents `memory=`).

The agent may read its memory but not write it (a FilesystemPermission denies
writes under /memories/). The runner records each accepted brief, and the web
application records each clinician decision, so the memory holds facts the
system can stand behind, not the model's own notes to itself.
"""

from __future__ import annotations

from datetime import UTC, datetime

HISTORY = "/patient-history.md"            # key inside the store namespace
MEMORY_PATH = "/memories/patient-history.md"  # the path the agent sees
HEADER = ("# Memory for this patient\n\nWritten by the system, not by the agent: one entry per accepted brief, "
          "and one per clinician decision on a proposed action. Newest last.\n")


def namespace(patient_id: str) -> tuple[str, ...]:
    return ("patient", patient_id)


def open_state(dsn: str, user: str, password: str, embeddings):
    """Return (checkpointer, store, close) for the agent user's own schema."""
    import oracledb
    from langgraph_oracledb.checkpoint.oracle import OracleSaver
    from langgraph_oracledb.store.oracle import OracleStore

    saver_conn = oracledb.connect(user=user, password=password, dsn=dsn)
    store_conn = oracledb.connect(user=user, password=password, dsn=dsn)
    saver = OracleSaver(saver_conn)
    saver.setup()  # idempotent
    store = OracleStore(
        store_conn,
        index={"dims": 384, "embed": embeddings, "fields": ["content"],
               "index_type": {"type": "ivf", "distance_metric": "COSINE"}},
    )
    store.setup()  # idempotent

    def close() -> None:
        for c in (saver_conn, store_conn):
            try:
                c.close()
            except Exception:  # noqa: BLE001
                pass

    return saver, store, close


def backend(patient_id: str, store):
    """The Deep Agent's filesystem: scratch files in graph state, /memories/ in Oracle."""
    from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

    return CompositeBackend(
        default=StateBackend(),
        routes={"/memories/": StoreBackend(namespace=lambda _rt: namespace(patient_id), store=store)},
    )


def read_history(store, patient_id: str) -> str:
    item = store.get(namespace(patient_id), HISTORY)
    if not item:
        return ""
    content = item.value.get("content", "")
    return "\n".join(content) if isinstance(content, list) else str(content)


def append(store, patient_id: str, entry: str) -> None:
    from deepagents.backends.utils import create_file_data

    current = read_history(store, patient_id) or HEADER
    stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    store.put(namespace(patient_id), HISTORY, create_file_data(f"{current.rstrip()}\n\n## {stamp}\n{entry.strip()}\n"))


def remember_brief(store, patient_id: str, run_id: str, brief) -> None:
    steps = "\n".join(f"- next step: {n.step}" for n in brief.next_steps[:6])
    actions = "\n".join(f"- proposed action #{a.action_id} ({a.kind}): {a.summary}" for a in brief.proposed_actions)
    append(store, patient_id, f"Brief accepted (run {run_id}).\n{steps}\n{actions}")


def remember_decision(store, patient_id: str, action_id: int, title: str, decision: str, result: str | None) -> None:
    outcome = f" Result: {result}." if result else ""
    verb = {"approve": "approved", "reject": "rejected"}.get(decision, decision)
    append(store, patient_id, f"Clinician {verb} action #{action_id}: {title}.{outcome}")
