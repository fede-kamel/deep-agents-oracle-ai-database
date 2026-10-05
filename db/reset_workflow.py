"""Reset the demo to a clean slate: care actions, their audit trail, the lab
orders, portal messages and appointment requests they produced, the agents'
escalations and the policy log, each
patient's long-term memory, and the agents' checkpoints. The chart itself, the
reference stores and every configuration are untouched.

Also called by the web application's "Reset demo" button.

    uv run python db/reset_workflow.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import oracledb
from langchain_oracledb.embeddings import OracleEmbeddings

from agent import memory
from common.config import (
    OWNER,
    PATIENT_KEYS,
    agent_user,
    load_config,
    password,
)

CHECKPOINT_TABLES = ("checkpoint_writes", "checkpoint_blobs", "checkpoints")


def reset(log=print) -> dict:
    dsn = load_config()["dsn"]
    counts: dict[str, int] = {}
    with oracledb.connect(user=OWNER, password=password(OWNER), dsn=dsn) as conn:
        cur = conn.cursor()
        for name, sql in (("patient messages", "DELETE FROM patient_message"),
                          ("lab orders", "DELETE FROM lab_order"),
                          ("appointment requests", "DELETE FROM appointment WHERE status = 'requested'"),
                          ("audit events", "DELETE FROM care_action_event"),
                          ("care actions", "DELETE FROM care_action"),
                          ("escalations", "DELETE FROM agent_escalation"),
                          ("policy events", "DELETE FROM policy_event"),
                          ("physician orders undone", "UPDATE medication SET status = 'active', order_note = NULL WHERE order_note LIKE 'physician order%'")):
            cur.execute(sql)
            counts[name] = cur.rowcount
            log(f"  {name:<22} {cur.rowcount} rows removed")
        conn.commit()
    counts["checkpoints"] = 0
    for key in PATIENT_KEYS:
        user = agent_user(key)
        with oracledb.connect(user=user, password=password(user), dsn=dsn) as conn:
            cur = conn.cursor()
            for table in CHECKPOINT_TABLES:
                try:
                    cur.execute(f"DELETE FROM {table}")
                    if table == "checkpoints":
                        counts["checkpoints"] += cur.rowcount
                except oracledb.DatabaseError:
                    pass  # no run yet for this patient: the tables do not exist
            conn.commit()
            emb = OracleEmbeddings(conn=conn, params={"provider": "database", "model": "DA_OWNER.MINILM_L12"})
            _, store, close = memory.open_state(dsn, user, password(user), emb)
            try:
                store.delete(memory.namespace(f"SYN-{key}"), memory.HISTORY)
            finally:
                close()
        log(f"  SYN-{key}: memory and checkpoints cleared")
    return counts


def main() -> None:
    reset()
    print("RESET OK")


if __name__ == "__main__":
    main()
