"""Vector stores: the chart notes and two public reference corpora.

The tables use exactly the shape `langchain_oracledb.OracleVS` creates (RAW
id, CLOB text, JSON metadata, VECTOR(384, FLOAT32)), so the langchain-oracle
datastores attach to them unchanged. 384 is the dimension of the in-database
all-MiniLM-L12-v2 model that `db/setup_admin.py` loads.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-05
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

VECTOR_TABLES = ("PATIENT_NOTE_VEC", "CLINICAL_REFERENCE", "RESEARCH_EVIDENCE")
DDL = (
    "CREATE TABLE {name} ("
    "id RAW(16) DEFAULT SYS_GUID() PRIMARY KEY, "
    "text CLOB, metadata JSON, embedding VECTOR(384, FLOAT32))"
)


def upgrade() -> None:
    for name in VECTOR_TABLES:
        op.execute(DDL.format(name=name))
        # The name langchain-oci's ADB datastore looks for, so it finds the index.
        op.execute(f"CREATE INDEX {f'IDX_{name}_MID'[:30]} ON {name} (JSON_VALUE(metadata, '$.id'))")


def downgrade() -> None:
    for name in VECTOR_TABLES:
        op.execute(f"DROP TABLE {name} PURGE")
