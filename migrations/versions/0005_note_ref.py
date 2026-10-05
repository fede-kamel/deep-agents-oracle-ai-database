"""Citable note ids in SQL results.

A chart note is embedded under the id `<patient_id>-NOTE-<id, 4 digits>`; SQL
over `clinical_note` returned only the numeric key, so an agent reading notes
through SQL had nothing to cite and numbered them itself. This virtual column
gives every row the same id the vector store uses.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-05
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE clinical_note ADD (note_ref VARCHAR2(96) GENERATED ALWAYS AS "
        "(patient_id || '-NOTE-' || LPAD(TO_CHAR(id), 4, '0')) VIRTUAL)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE clinical_note DROP COLUMN note_ref")
