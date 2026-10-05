"""Reset the workflow state to a clean slate: care actions, their audit trail,
the lab orders, portal messages and appointment requests they produced, and
each patient's long-term memory. The chart itself is untouched.

    uv run python db/reset_workflow.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import oracledb  # noqa: E402
from langchain_oracledb.embeddings import OracleEmbeddings  # noqa: E402

from agent import memory  # noqa: E402
from common.config import OWNER, PATIENT_KEYS, agent_user, load_config, password  # noqa: E402


def main() -> None:
    dsn = load_config()["dsn"]
    with oracledb.connect(user=OWNER, password=password(OWNER), dsn=dsn) as conn:
        cur = conn.cursor()
        for sql in ("DELETE FROM patient_message", "DELETE FROM lab_order",
                    "DELETE FROM appointment WHERE status = 'requested'",
                    "DELETE FROM care_action_event", "DELETE FROM care_action"):
            cur.execute(sql)
            print(f"  {sql:<52} {cur.rowcount} rows")
        conn.commit()
    for key in PATIENT_KEYS:
        user = agent_user(key)
        with oracledb.connect(user=user, password=password(user), dsn=dsn) as conn:
            emb = OracleEmbeddings(conn=conn, params={"provider": "database", "model": "DA_OWNER.MINILM_L12"})
            _, store, close = memory.open_state(dsn, user, password(user), emb)
            try:
                store.delete(memory.namespace(f"SYN-{key}"), memory.HISTORY)
            finally:
                close()
        print(f"  memory of SYN-{key} cleared")
    print("RESET OK")


if __name__ == "__main__":
    main()
