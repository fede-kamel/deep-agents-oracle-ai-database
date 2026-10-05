"""Cohort benchmark: aggregates only, no patient identifiers.

The seed step fills the clinical tables with a few hundred background
synthetic patients and computes this table from them. Row-level security keeps
an agent user from reading any other patient's rows; this table is how it can
still compare its patient with the population, because it holds nothing but
counts and percentiles.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-05
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cohort_benchmark",
        sa.Column("cohort", sa.String(64), primary_key=True),
        sa.Column("metric", sa.String(64), primary_key=True),
        sa.Column("patients", sa.Integer, nullable=False),
        sa.Column("p10", sa.Numeric(10, 2)),
        sa.Column("p50", sa.Numeric(10, 2)),
        sa.Column("p90", sa.Numeric(10, 2)),
        sa.Column("unit", sa.String(32)),
        sa.Column("description", sa.String(256)),
    )


def downgrade() -> None:
    op.drop_table("cohort_benchmark")
