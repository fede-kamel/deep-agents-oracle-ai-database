"""Read-only SQL tools over the relational chart.

The tools let the agent discover the schema and run SELECT statements as its
patient's read-only database user. Three layers stand behind every query, and
the tool is the weakest of them on purpose:

1. this tool accepts one SELECT (or WITH) statement and caps the rows;
2. the database user holds SELECT grants and nothing else, so a write is
   refused by Oracle whatever the tool lets through;
3. the row-level security policy filters every table to the one patient, so
   a SELECT over another patient's rows returns nothing.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal

from langchain_community.utilities import SQLDatabase
from langchain_core.tools import tool
from sqlalchemy import create_engine, text

CHART_TABLES = [
    "patient", "condition", "allergy", "medication", "encounter", "clinical_note",
    "lab_result", "vital_sign", "referral", "appointment", "cohort_benchmark",
]
MAX_ROWS = 200
_SELECT = re.compile(r"^\s*(select|with)\b", re.I | re.S)


def _cell(value):
    if isinstance(value, datetime):
        return value.date().isoformat() if value.time() == datetime.min.time() else value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def build_sql_tools(dsn: str, user: str, password: str):
    engine = create_engine(
        "oracle+oracledb://",
        connect_args={"user": user, "password": password, "dsn": dsn},
        pool_pre_ping=True,
    )
    db = SQLDatabase(engine, schema="DA_OWNER", include_tables=CHART_TABLES, sample_rows_in_table_info=2)

    @tool
    def describe_chart_tables(tables: str = "") -> str:
        """Show the CREATE TABLE definition and two sample rows for chart tables.

        Pass a comma-separated list of table names, or leave empty for all of:
        patient, condition, allergy, medication, encounter, clinical_note,
        lab_result, vital_sign, referral, appointment, cohort_benchmark.
        Tables live in schema DA_OWNER; dates are DATE columns.
        """
        names = [t.strip().lower() for t in tables.split(",") if t.strip()] or CHART_TABLES
        unknown = [n for n in names if n not in CHART_TABLES]
        if unknown:
            return f"Unknown tables: {unknown}. Available: {CHART_TABLES}"
        return db.get_table_info(names)

    @tool
    def query_chart(sql: str) -> str:
        """Run one read-only Oracle SQL SELECT against the patient's chart.

        Use Oracle syntax (FETCH FIRST n ROWS ONLY, TO_CHAR, MONTHS_BETWEEN,
        REGR_SLOPE). Qualify tables as DA_OWNER.<table>. Only the selected
        patient's rows are visible; cohort_benchmark holds population
        percentiles for comparison. Returns at most 200 rows as JSON-like lines.
        """
        statement = sql.strip().rstrip(";")
        if not _SELECT.match(statement) or ";" in statement:
            return "Refused: query_chart accepts exactly one SELECT or WITH statement."
        try:
            with engine.connect() as conn:
                result = conn.execute(text(statement))
                cols = list(result.keys())
                rows = result.fetchmany(MAX_ROWS + 1)
        except Exception as exc:  # the database's own answer is the useful part
            return f"Oracle error: {str(exc).splitlines()[0][:400]}"
        lines = [str({c: _cell(v) for c, v in zip(cols, row, strict=True)}) for row in rows[:MAX_ROWS]]
        if len(rows) > MAX_ROWS:
            lines.append(f"... truncated at {MAX_ROWS} rows")
        return "\n".join(lines) if lines else "No rows."

    return [describe_chart_tables, query_chart], engine
