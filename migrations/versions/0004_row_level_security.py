"""Row-level security: each agent user sees one patient, enforced by the database.

An Oracle Virtual Private Database policy on every patient-bearing table adds
a predicate to whatever SQL the session runs. For DA_AGENT_X the predicate is
`patient_id = 'SYN-X'`; for the schema owner it is `1=1`; for anyone else it
is `1=0`. The agent can write any SELECT it likes; it cannot read a row that
belongs to another patient, because the rows are filtered before it sees them.
The vector table is covered the same way through its JSON metadata.

Agent users get SELECT and nothing else.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-05
"""

from alembic import op

from common.config import EMBEDDING_MODEL, PATIENT_KEYS, agent_user

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

RELATIONAL = (
    "PATIENT", "CONDITION", "ALLERGY", "MEDICATION", "ENCOUNTER",
    "CLINICAL_NOTE", "LAB_RESULT", "VITAL_SIGN", "REFERRAL", "APPOINTMENT",
)
SHARED = ("COHORT_BENCHMARK", "CLINICAL_REFERENCE", "RESEARCH_EVIDENCE")

FUNCTION = """
CREATE OR REPLACE FUNCTION DA_PATIENT_SCOPE(p_schema IN VARCHAR2, p_object IN VARCHAR2)
RETURN VARCHAR2 AS
  v_user VARCHAR2(128) := SYS_CONTEXT('USERENV', 'SESSION_USER');
  v_col  VARCHAR2(64)  := CASE WHEN p_object = 'PATIENT_NOTE_VEC'
                               THEN 'JSON_VALUE(metadata, ''$.patient_id'')'
                               ELSE 'patient_id' END;
BEGIN
  IF v_user = 'DA_OWNER' THEN
    RETURN '1=1';
  ELSIF REGEXP_LIKE(v_user, '^DA_AGENT_[A-Z]$') THEN
    RETURN v_col || ' = ''SYN-' || SUBSTR(v_user, -1) || '''';
  END IF;
  RETURN '1=0';
END;
"""


def _policy(table: str) -> str:
    return f"""
BEGIN
  DBMS_RLS.ADD_POLICY(
    object_schema   => 'DA_OWNER',
    object_name     => '{table}',
    policy_name     => 'DA_SCOPE_{table}',
    function_schema => 'DA_OWNER',
    policy_function => 'DA_PATIENT_SCOPE',
    statement_types => 'SELECT,INSERT,UPDATE,DELETE',
    update_check    => TRUE);
END;
"""


def upgrade() -> None:
    op.execute(FUNCTION)
    for table in (*RELATIONAL, "PATIENT_NOTE_VEC"):
        op.execute(_policy(table))
    for key in PATIENT_KEYS:
        user = agent_user(key)
        for table in (*RELATIONAL, "PATIENT_NOTE_VEC", *SHARED):
            op.execute(f"GRANT SELECT ON {table} TO {user}")
        op.execute(f"GRANT SELECT ON MINING MODEL {EMBEDDING_MODEL} TO {user}")


def downgrade() -> None:
    for table in (*RELATIONAL, "PATIENT_NOTE_VEC"):
        op.execute(
            f"BEGIN DBMS_RLS.DROP_POLICY('DA_OWNER', '{table}', 'DA_SCOPE_{table}'); END;"
        )
    op.execute("DROP FUNCTION DA_PATIENT_SCOPE")
