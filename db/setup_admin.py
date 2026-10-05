"""One-time database setup, run by the operator as ADMIN.

Creates the schema that owns the demo's vector tables, one read-only agent
user per synthetic patient, private synonyms that let the langchain-oracle
vector datastores address the owner's tables by their plain names, and loads
the all-MiniLM-L12-v2 ONNX embedding model into the database so vectors are
computed inside Oracle AI Database.

The ADMIN password is read from DA_ADMIN_PASSWORD and never printed. Every
password this script creates goes straight into an owner-only file (common/config.py).

    DA_ADMIN_PASSWORD=... uv run python db/setup_admin.py
    uv run python db/setup_admin.py --drop     # remove everything it created
"""

from __future__ import annotations

import argparse
import os
import secrets
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import oracledb  # noqa: E402

from common.config import (  # noqa: E402
    EMBEDDING_MODEL,
    OWNER,
    PATIENT_KEYS,
    VECTOR_TABLES,
    agent_user,
    load_config,
    store_password,
)

ONNX_DIR_URI = (
    "https://adwc4pm.objectstorage.us-ashburn-1.oci.customer-oci.com/p/"
    "iPX9W0MZeRkwJKWdFmdJCemmN-iKAl_bFvNGYLW7YqIrw4kKsukL24J2q93Beb9S/"
    "n/adwc4pm/b/OML-ai-models/o/"
)
ONNX_FILE = "all_MiniLM_L12_v2.onnx"
CLINICIAN = "DA_CLINICIAN"  # approves care actions in the web application
DEMO_USERS = [OWNER, CLINICIAN] + [agent_user(k) for k in PATIENT_KEYS]


def new_password() -> str:
    """An ADB-compliant password: 24 chars, upper, lower, digit, no quotes."""
    alphabet = string.ascii_letters + string.digits
    while True:
        body = "".join(secrets.choice(alphabet) for _ in range(22))
        if any(c.isupper() for c in body) and any(c.islower() for c in body) and any(
            c.isdigit() for c in body
        ):
            return body + "#9"


def run(cur, sql: str, ignore: tuple[int, ...] = ()) -> None:
    try:
        cur.execute(sql)
    except oracledb.DatabaseError as exc:
        if exc.args[0].code in ignore:
            return
        raise


def user_exists(cur, name: str) -> bool:
    cur.execute("SELECT COUNT(*) FROM dba_users WHERE username = :u", u=name)
    return cur.fetchone()[0] > 0


def setup(cur) -> None:
    for user in DEMO_USERS:
        pw = new_password()
        if user_exists(cur, user):
            cur.execute(f'ALTER USER {user} IDENTIFIED BY "{pw}"')
            action = "password rotated"
        else:
            cur.execute(f'CREATE USER {user} IDENTIFIED BY "{pw}"')
            action = "created"
        store_password(user, pw)
        print(f"  {user:<12} {action}; password stored in the secrets directory")

    owner_grants = [
        f"GRANT CREATE SESSION, CREATE TABLE, CREATE SEQUENCE, CREATE PROCEDURE, CREATE MINING MODEL TO {OWNER}",
        f"GRANT DB_DEVELOPER_ROLE TO {OWNER}",
        f"GRANT EXECUTE ON DBMS_CLOUD TO {OWNER}",
        # Row-level security policies (Alembic revision 0004) are created by
        # the owner through DBMS_RLS.
        f"GRANT EXECUTE ON DBMS_RLS TO {OWNER}",
        f"GRANT READ, WRITE ON DIRECTORY DATA_PUMP_DIR TO {OWNER}",
        f"ALTER USER {OWNER} QUOTA 2G ON DATA",
    ]
    for sql in owner_grants:
        cur.execute(sql)

    for key in PATIENT_KEYS:
        user = agent_user(key)
        # The agent user reads the chart (SELECT grants from migration 0004),
        # proposes care actions (INSERT on care_action, migration 0006), and
        # keeps its own working state: LangGraph checkpoints and long-term
        # memory (langgraph-oracledb) in its own schema, under a small quota.
        # It can change nothing in DA_OWNER's schema.
        cur.execute(f"GRANT CREATE SESSION, CREATE TABLE TO {user}")
        cur.execute(f"ALTER USER {user} QUOTA 64M ON DATA")
        for table in VECTOR_TABLES:
            run(cur, f"DROP SYNONYM {user}.{table}", ignore=(1434,))
            cur.execute(f"CREATE SYNONYM {user}.{table} FOR {OWNER}.{table}")
    # The clinician may sign in and nothing more until migration 0006 grants
    # EXECUTE on DECIDE_CARE_ACTION and SELECT on the workflow tables.
    cur.execute(f"GRANT CREATE SESSION TO {CLINICIAN}")
    print("  grants and vector-table synonyms in place")


def load_model(owner_conn) -> None:
    cur = owner_conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM user_mining_models WHERE model_name = :m", m=EMBEDDING_MODEL
    )
    if cur.fetchone()[0]:
        print(f"  {OWNER}.{EMBEDDING_MODEL} already loaded")
        return
    print(f"  loading {ONNX_FILE} into {OWNER}.{EMBEDDING_MODEL} (133 MB, about a minute)")
    cur.execute(
        """
        BEGIN
          DBMS_CLOUD.GET_OBJECT(credential_name => NULL,
                                directory_name  => 'DATA_PUMP_DIR',
                                object_uri      => :uri);
          DBMS_VECTOR.LOAD_ONNX_MODEL(directory  => 'DATA_PUMP_DIR',
                                      file_name  => :f,
                                      model_name => :m);
        END;
        """,
        uri=ONNX_DIR_URI + ONNX_FILE,
        f=ONNX_FILE,
        m=EMBEDDING_MODEL,
    )
    cur.execute(
        f"SELECT VECTOR_DIMENSION_COUNT(VECTOR_EMBEDDING({EMBEDDING_MODEL} USING 'probe' AS data)) FROM dual"
    )
    print(f"  model loaded; embedding dimension {cur.fetchone()[0]}")


def drop(cur) -> None:
    for user in DEMO_USERS:
        if user_exists(cur, user):
            cur.execute(f"DROP USER {user} CASCADE")
            print(f"  {user} dropped")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--drop", action="store_true", help="drop every demo user and its objects")
    args = parser.parse_args()

    admin_pw = os.environ.get("DA_ADMIN_PASSWORD")
    if not admin_pw:
        raise SystemExit("ABORT: DA_ADMIN_PASSWORD is not set (operator step).")
    dsn = load_config()["dsn"]

    with oracledb.connect(user="ADMIN", password=admin_pw, dsn=dsn) as conn:
        cur = conn.cursor()
        if args.drop:
            drop(cur)
            return
        setup(cur)

    from common.config import password

    with oracledb.connect(user=OWNER, password=password(OWNER), dsn=dsn) as owner_conn:
        load_model(owner_conn)
    print("SETUP OK")


if __name__ == "__main__":
    main()
