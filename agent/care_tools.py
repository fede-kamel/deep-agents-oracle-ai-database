"""The care coordinator's tools: propose, never execute.

Three narrow, typed tools insert one row each into DA_OWNER.care_action as the
patient's own database user. The database does the rest: a trigger forces the
status to `proposed` and stamps the proposer, row-level security refuses a
proposal for any other patient, and the user holds no UPDATE or EXECUTE grant.
Approval and execution happen later, in the web application, as the clinician.

There is no free-form SQL on the write path: the tools bind values into one
fixed INSERT.
"""

from __future__ import annotations

import json
import os
from typing import Literal

from langchain_core.tools import tool

INSERT = (
    "INSERT INTO DA_OWNER.care_action (patient_id, run_id, kind, title, rationale, citations, payload) "
    "VALUES (:patient_id, :run_id, :kind, :title, :rationale, :citations, JSON(:payload)) RETURNING id INTO :new_id"
)


MAX_PER_RUN = 5


def build_care_tools(dsn: str, user: str, password: str, patient_id: str):
    import oracledb

    run_id = os.environ.get("DA_RUN_ID", "local")

    @tool
    def list_care_actions() -> str:
        """List every care action ever proposed for this patient, newest first:
        id, kind, status (proposed, approved, executed, rejected), title, and
        what execution produced. Call this first: never propose again what is
        already executed, approved, pending, or was rejected."""
        with oracledb.connect(user=user, password=password, dsn=dsn) as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, kind, status, title, NVL(result_summary, '-'), run_id "
                        "FROM DA_OWNER.care_action ORDER BY created_at DESC FETCH FIRST 40 ROWS ONLY")
            rows = cur.fetchall()
        if not rows:
            return "No care actions yet for this patient."
        return "\n".join(f"#{i} {k} [{st}] {t} | result: {r} | run {run}" for i, k, st, t, r, run in rows)

    def propose(kind: str, title: str, rationale: str, citations: str, payload: dict) -> str:
        try:
            with oracledb.connect(user=user, password=password, dsn=dsn) as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*), SUM(CASE WHEN kind = :k AND title = :t THEN 1 ELSE 0 END) "
                            "FROM DA_OWNER.care_action WHERE run_id = :r", k=kind, t=title[:250], r=run_id)
                count, same = cur.fetchone()
                if count >= MAX_PER_RUN:
                    return f"Refused: {MAX_PER_RUN} actions already proposed in this run. Prioritise; do not propose more."
                if same:
                    return "Refused: the same action is already proposed in this run."
                new_id = cur.var(oracledb.NUMBER)
                cur.execute(INSERT, patient_id=patient_id, run_id=run_id, kind=kind, title=title[:250],
                            rationale=rationale[:1990], citations=citations[:990],
                            payload=json.dumps(payload), new_id=new_id)
                conn.commit()
                action_id = int(new_id.getvalue()[0])
        except oracledb.DatabaseError as exc:
            return f"Refused by the database: {str(exc).splitlines()[0][:300]}"
        return (f"Proposed care action {action_id} ({kind}) for {patient_id}. Status: proposed. "
                "It runs only if the clinician approves it in the web application.")

    @tool
    def propose_lab_request(tests: list[str], urgency: Literal["routine", "soon", "urgent"], reason: str, citations: str) -> str:
        """Propose a lab request for this patient, for the clinician to approve.

        tests: the specific tests, e.g. ["UACR", "basic metabolic panel"].
        urgency: routine, soon (before the visit), or urgent.
        reason: one or two sentences grounded in the chart.
        citations: the ids behind the reason, e.g. "[SQL:lab_result] [SYN-X-NOTE-0006]".
        """
        title = f"Lab request: {', '.join(tests)}"
        return propose("lab_request", title, reason, citations, {"tests": tests, "urgency": urgency, "before_visit": urgency != "routine"})

    @tool
    def draft_patient_message(subject: str, body: str, reason: str, citations: str) -> str:
        """Draft a portal message to the patient, for the clinician to approve.

        Write to the patient in plain, warm language at a sixth-grade reading
        level: why a follow-up visit is needed, what to bring or do before it,
        and when to seek care sooner. No diagnosis, no medication changes, no
        identifiers other than the first name. reason and citations explain the
        message to the clinician.
        """
        return propose("patient_message", f"Message: {subject}", reason, citations,
                       {"subject": subject, "body": body, "to": "the patient (portal, simulated)"})

    @tool
    def propose_follow_up(within_days: int, visit_type: str, reason: str, citations: str) -> str:
        """Propose a follow-up appointment within a number of days, for the clinician to approve.

        within_days: 1 to 90. visit_type: e.g. "Heart failure clinic visit".
        reason and citations explain the timing to the clinician.
        """
        days = max(1, min(int(within_days), 90))
        return propose("follow_up", f"Follow-up: {visit_type} within {days} days", reason, citations,
                       {"within_days": days, "visit_type": visit_type})

    return [list_care_actions, propose_lab_request, draft_patient_message, propose_follow_up]
