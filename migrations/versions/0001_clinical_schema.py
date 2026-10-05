"""Clinical schema: the transactional chart.

One row per patient, and the facts a chart is made of hang off it: conditions,
allergies, medications, encounters with their notes, lab results, vital signs,
referrals and appointments. Every table carries PATIENT_ID so a single
row-level security policy (revision 0004) can scope all of them.

Revision ID: 0001
Revises:
Create Date: 2026-10-05
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

PID = sa.String(16)


def _child(name: str, *columns: sa.Column) -> None:
    op.create_table(
        name,
        sa.Column("id", sa.Integer, sa.Identity(), primary_key=True),
        sa.Column("patient_id", PID, sa.ForeignKey("patient.patient_id"), nullable=False),
        *columns,
    )
    op.create_index(f"ix_{name}_patient", name, ["patient_id"])


def upgrade() -> None:
    op.create_table(
        "patient",
        sa.Column("patient_id", PID, primary_key=True),
        sa.Column("display_name", sa.String(64), nullable=False),
        sa.Column("alias", sa.String(128), nullable=False),
        sa.Column("birth_year", sa.Integer, nullable=False),
        sa.Column("sex", sa.String(16), nullable=False),
        sa.Column("situation", sa.String(256)),
        sa.Column("visit_reason", sa.String(256)),
        # Every row in this schema is invented. The constraint makes that a
        # property of the database, not a promise in a README.
        sa.Column("is_synthetic", sa.String(1), nullable=False, server_default="Y"),
        sa.CheckConstraint("is_synthetic = 'Y'", name="ck_patient_synthetic"),
        sa.CheckConstraint("patient_id LIKE 'SYN-%'", name="ck_patient_syn_prefix"),
    )
    _child(
        "condition",
        sa.Column("description", sa.String(256), nullable=False),
        sa.Column("onset_date", sa.Date),
        sa.Column("status", sa.String(32), nullable=False),
    )
    _child(
        "allergy",
        sa.Column("substance", sa.String(128), nullable=False),
        sa.Column("reaction", sa.String(128)),
    )
    _child(
        "medication",
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("dose", sa.String(64)),
        sa.Column("frequency", sa.String(64)),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("started_on", sa.Date),
        sa.Column("status", sa.String(32), nullable=False),
    )
    _child(
        "encounter",
        sa.Column("encounter_date", sa.Date, nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("setting", sa.String(32), nullable=False),
    )
    _child(
        "clinical_note",
        sa.Column("encounter_id", sa.Integer, sa.ForeignKey("encounter.id"), nullable=False),
        sa.Column("note_date", sa.Date, nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
    )
    _child(
        "lab_result",
        sa.Column("collected_on", sa.Date, nullable=False),
        sa.Column("test", sa.String(64), nullable=False),
        sa.Column("value", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit", sa.String(32)),
    )
    op.create_index("ix_lab_result_test", "lab_result", ["test", "collected_on"])
    _child(
        "vital_sign",
        sa.Column("measured_on", sa.Date, nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("value", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit", sa.String(32)),
    )
    _child(
        "referral",
        sa.Column("kind", sa.String(128), nullable=False),
        sa.Column("opened_on", sa.Date, nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("detail", sa.String(256)),
    )
    _child(
        "appointment",
        sa.Column("scheduled_for", sa.Date, nullable=False),
        sa.Column("kind", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
    )


def downgrade() -> None:
    for name in (
        "appointment", "referral", "vital_sign", "lab_result", "clinical_note",
        "encounter", "medication", "allergy", "condition", "patient",
    ):
        op.drop_table(name)
