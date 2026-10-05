"""Seed the clinical schema with synthetic rows and compute the cohort benchmark.

Runs on the host as DA_OWNER after `alembic upgrade head`. Inserts Patients X,
Y and Z and the background cohort into the relational tables, then fills
COHORT_BENCHMARK with SQL aggregates (REGR_SLOPE for each patient's eGFR
trend, PERCENTILE_CONT across the cohort). Idempotent: it deletes the
synthetic rows it owns before inserting.

    uv run python db/seed.py
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import oracledb  # noqa: E402

from common.config import OWNER, load_config, password  # noqa: E402
from data.cohort import generate  # noqa: E402
from data.patients import PATIENTS  # noqa: E402

CHILD_TABLES = (
    "clinical_note", "appointment", "referral", "vital_sign", "lab_result",
    "encounter", "medication", "allergy", "condition",
)


NOTE_SEQ = [0]


def d(value: str | None):
    return date.fromisoformat(value) if value else None


def insert_patient(cur, p: dict) -> None:
    cur.execute(
        "INSERT INTO patient (patient_id, display_name, alias, birth_year, sex, situation, visit_reason) "
        "VALUES (:1, :2, :3, :4, :5, :6, :7)",
        [p["id"], p["display_name"], p["alias"], p["birth_year"], p["sex"],
         p.get("situation"), p.get("visit_reason")],
    )
    pid = p["id"]
    cur.executemany(
        "INSERT INTO condition (patient_id, description, onset_date, status) VALUES (:1, :2, :3, :4)",
        [(pid, desc, d(onset), status) for desc, onset, status in p.get("conditions", [])],
    )
    if p.get("allergies"):
        cur.executemany(
            "INSERT INTO allergy (patient_id, substance, reaction) VALUES (:1, :2, :3)",
            [(pid, s, r) for s, r in p["allergies"]],
        )
    cur.executemany(
        "INSERT INTO medication (patient_id, name, dose, frequency, source, started_on, status) "
        "VALUES (:1, :2, :3, :4, :5, :6, :7)",
        [(pid, n, dose, f, src, d(start), st) for n, dose, f, src, start, st in p.get("medications", [])],
    )
    if p.get("labs"):
        cur.executemany(
            "INSERT INTO lab_result (patient_id, collected_on, test, value, unit) VALUES (:1, :2, :3, :4, :5)",
            [(pid, d(on), t, v, u) for on, t, v, u in p["labs"]],
        )
    if p.get("vitals"):
        cur.executemany(
            "INSERT INTO vital_sign (patient_id, measured_on, kind, value, unit) VALUES (:1, :2, :3, :4, :5)",
            [(pid, d(on), k, v, u) for on, k, v, u in p["vitals"]],
        )
    for enc in p.get("encounters", []):
        on, kind, setting = enc[:3]
        enc_id = cur.var(oracledb.NUMBER)
        cur.execute(
            "INSERT INTO encounter (patient_id, encounter_date, kind, setting) VALUES (:1, :2, :3, :4) "
            "RETURNING id INTO :5",
            [pid, d(on), kind, setting, enc_id],
        )
        if len(enc) > 3:
            # Explicit, deterministic note ids: a re-seed reproduces the same
            # SYN-<P>-NOTE-nnnn ids, so published briefs keep resolving.
            NOTE_SEQ[0] += 1
            cur.execute(
                "INSERT INTO clinical_note (id, patient_id, encounter_id, note_date, kind, body) "
                "VALUES (:1, :2, :3, :4, :5, :6)",
                [NOTE_SEQ[0], pid, int(enc_id.getvalue()[0]), d(on), kind, enc[3]],
            )
    for kind, opened, status, detail in p.get("referrals", []):
        cur.execute(
            "INSERT INTO referral (patient_id, kind, opened_on, status, detail) VALUES (:1, :2, :3, :4, :5)",
            [pid, kind, d(opened), status, detail],
        )
    for on, kind, status in p.get("appointments", []):
        cur.execute(
            "INSERT INTO appointment (patient_id, scheduled_for, kind, status) VALUES (:1, :2, :3, :4)",
            [pid, d(on), kind, status],
        )


BENCHMARKS = [
    # eGFR trend per type 2 diabetes patient, as mL/min/1.73m2 per year.
    """
    INSERT INTO cohort_benchmark (cohort, metric, patients, p10, p50, p90, unit, description)
    SELECT 'Type 2 diabetes', 'eGFR change per year', COUNT(*),
           PERCENTILE_CONT(0.1) WITHIN GROUP (ORDER BY slope),
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY slope),
           PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY slope),
           'mL/min/1.73m2 per year',
           'Per-patient linear trend (REGR_SLOPE) of eGFR in the background diabetes cohort'
    FROM (SELECT l.patient_id, REGR_SLOPE(l.value, l.collected_on - DATE '2024-01-01') * 365 AS slope
          FROM lab_result l JOIN condition c ON c.patient_id = l.patient_id
          WHERE l.test = 'eGFR' AND c.description = 'Type 2 diabetes mellitus'
            AND l.patient_id LIKE 'SYN-C%'
          GROUP BY l.patient_id HAVING COUNT(*) >= 3)
    """,
    """
    INSERT INTO cohort_benchmark (cohort, metric, patients, p10, p50, p90, unit, description)
    SELECT 'Type 2 diabetes', 'Latest HbA1c', COUNT(*),
           PERCENTILE_CONT(0.1) WITHIN GROUP (ORDER BY v), PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY v),
           PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY v), '%', 'Most recent HbA1c per patient'
    FROM (SELECT patient_id, MAX(value) KEEP (DENSE_RANK LAST ORDER BY collected_on) v
          FROM lab_result WHERE test = 'HbA1c' AND patient_id LIKE 'SYN-C%' GROUP BY patient_id)
    """,
    """
    INSERT INTO cohort_benchmark (cohort, metric, patients, p10, p50, p90, unit, description)
    SELECT 'Type 2 diabetes', 'Latest UACR', COUNT(*),
           PERCENTILE_CONT(0.1) WITHIN GROUP (ORDER BY v), PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY v),
           PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY v), 'mg/g', 'Most recent urine albumin-to-creatinine ratio'
    FROM (SELECT patient_id, MAX(value) KEEP (DENSE_RANK LAST ORDER BY collected_on) v
          FROM lab_result WHERE test = 'UACR' AND patient_id LIKE 'SYN-C%' GROUP BY patient_id)
    """,
    """
    INSERT INTO cohort_benchmark (cohort, metric, patients, p10, p50, p90, unit, description)
    SELECT 'Heart failure (HFrEF)', 'Readmissions after index admission', COUNT(*),
           PERCENTILE_CONT(0.1) WITHIN GROUP (ORDER BY n), PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY n),
           PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY n), 'readmissions',
           'Readmissions within 90 days of the index admission; share readmitted at least once = '
           || TO_CHAR(ROUND(100 * AVG(CASE WHEN n > 0 THEN 1 ELSE 0 END))) || '%'
    FROM (SELECT p.patient_id, COUNT(e.id) n FROM patient p
          JOIN condition c ON c.patient_id = p.patient_id
          LEFT JOIN encounter e ON e.patient_id = p.patient_id AND e.kind = 'Hospital readmission'
          WHERE c.description LIKE 'Heart failure%' AND p.patient_id LIKE 'SYN-C%'
          GROUP BY p.patient_id)
    """,
    """
    INSERT INTO cohort_benchmark (cohort, metric, patients, p10, p50, p90, unit, description)
    SELECT 'Heart failure (HFrEF)', 'Latest potassium', COUNT(*),
           PERCENTILE_CONT(0.1) WITHIN GROUP (ORDER BY value), PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY value),
           PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY value), 'mmol/L', 'Most recent serum potassium'
    FROM lab_result WHERE test = 'Potassium' AND patient_id LIKE 'SYN-C%'
      AND patient_id IN (SELECT patient_id FROM condition WHERE description LIKE 'Heart failure%')
    """,
    """
    INSERT INTO cohort_benchmark (cohort, metric, patients, p10, p50, p90, unit, description)
    SELECT 'COPD, age 75 and over', 'Active medications', COUNT(*),
           PERCENTILE_CONT(0.1) WITHIN GROUP (ORDER BY n), PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY n),
           PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY n), 'medications', 'Count of active medications per patient'
    FROM (SELECT m.patient_id, COUNT(*) n FROM medication m
          JOIN condition c ON c.patient_id = m.patient_id
          JOIN patient p ON p.patient_id = m.patient_id
          WHERE c.description LIKE 'Chronic obstructive%' AND m.status = 'active'
            AND p.birth_year <= 1951 AND m.patient_id LIKE 'SYN-C%'
          GROUP BY m.patient_id)
    """,
]


def main() -> None:
    dsn = load_config()["dsn"]
    with oracledb.connect(user=OWNER, password=password(OWNER), dsn=dsn) as conn:
        cur = conn.cursor()
        for table in CHILD_TABLES:
            cur.execute(f"DELETE FROM {table} WHERE patient_id LIKE 'SYN-%'")
        cur.execute("DELETE FROM patient WHERE patient_id LIKE 'SYN-%'")
        cur.execute("DELETE FROM cohort_benchmark")

        NOTE_SEQ[0] = 0
        for p in PATIENTS.values():
            insert_patient(cur, p)
        cohort = generate()
        for p in cohort:
            insert_patient(cur, p)
        for sql in BENCHMARKS:
            cur.execute(sql)
        conn.commit()

        for table in ("patient", *CHILD_TABLES, "cohort_benchmark"):
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            print(f"  {table:<18} {cur.fetchone()[0]:>5} rows")
        cur.execute("SELECT cohort, metric, patients, p10, p50, p90, unit FROM cohort_benchmark ORDER BY 1, 2")
        for row in cur:
            print("  benchmark", row)
    print(f"SEED OK ({len(PATIENTS)} featured patients, {len(cohort)} background)")


if __name__ == "__main__":
    main()
