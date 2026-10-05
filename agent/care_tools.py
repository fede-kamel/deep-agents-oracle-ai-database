"""Care-action tools: agents propose, the database decides what is allowed.

Every tool inserts into DA_OWNER as the patient's own database user, through
one fixed statement with bound values; there is no free-form SQL on the write
path. Each session is stamped with the calling agent's name
(CLIENT_IDENTIFIER, set here by tool code, never by the model), and the
database enforces policy on it:

- row-level security refuses a row for any other patient;
- the proposal trigger forces the status and stamps the proposer;
- CP-03: only the medication-safety agent may propose a medication change. The
  care coordinator's attempt is refused (ORA-20014) and logged in
  policy_event, so it escalates to the medication-safety agent instead;
- CP-02: a medication change waits for a physician, whoever proposed it.

Approval and execution happen later, in the web application, as a person.
"""

from __future__ import annotations

import json
import os
from typing import Literal

from langchain_core.tools import tool

from agent import db

COORDINATOR = "care-coordinator"
MEDICATION_SAFETY = "medication-safety"
MAX_PER_RUN = 5

INSERT_ACTION = (
    "INSERT INTO DA_OWNER.care_action (patient_id, run_id, kind, title, rationale, citations, payload, escalation_id) "
    "VALUES (:patient_id, :run_id, :kind, :title, :rationale, :citations, JSON(:payload), :escalation_id) "
    "RETURNING id INTO :new_id"
)
INSERT_ESCALATION = (
    "INSERT INTO DA_OWNER.agent_escalation (patient_id, run_id, from_agent, to_agent, policy_code, subject, reason, citations) "
    "VALUES (:patient_id, :run_id, '-', :to_agent, 'CP-03', :subject, :reason, :citations) RETURNING id INTO :new_id"
)


def _first_line(exc: Exception) -> str:
    return str(exc).splitlines()[0][:300]


def _db_safe(fn):
    """A database hiccup becomes a tool answer the agent can act on, not a
    crash that ends the whole run."""
    import functools

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        import oracledb

        try:
            return fn(*args, **kwargs)
        except oracledb.Error as exc:
            return f"The database was unreachable for a moment ({_first_line(exc)[:120]}). Call this tool again."
    return wrapper


class _Care:
    """Shared connection and proposal logic for one agent in one run."""

    def __init__(self, dsn: str, user: str, password: str, patient_id: str, agent: str):
        self.dsn, self.user, self.password = dsn, user, password
        self.patient_id, self.agent = patient_id, agent
        self.run_id = os.environ.get("DA_RUN_ID", "local")

    def connect(self):
        conn = db.connect(user=self.user, password=self.password, dsn=self.dsn)
        conn.client_identifier = self.agent
        return conn

    def list_actions(self) -> str:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, kind, status, title, NVL(result_summary, '-'), run_id "
                        "FROM DA_OWNER.care_action ORDER BY created_at DESC FETCH FIRST 40 ROWS ONLY")
            rows = cur.fetchall()
        if not rows:
            return "No care actions yet for this patient."
        return "\n".join(f"#{i} {k} [{st}] {t} | result: {r} | run {run}" for i, k, st, t, r, run in rows)

    def propose(self, kind: str, title: str, rationale: str, citations: str, payload: dict,
                escalation_id: int | None = None) -> tuple[int | None, str]:
        import oracledb

        try:
            with self.connect() as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*), SUM(CASE WHEN kind = :k AND title = :t THEN 1 ELSE 0 END) "
                            "FROM DA_OWNER.care_action WHERE run_id = :r", k=kind, t=title[:250], r=self.run_id)
                count, same = cur.fetchone()
                if count >= MAX_PER_RUN:
                    return None, f"Refused: {MAX_PER_RUN} actions already proposed in this run. Prioritise; do not propose more."
                if same:
                    return None, "Refused: the same action is already proposed in this run."
                new_id = cur.var(oracledb.NUMBER)
                cur.execute(INSERT_ACTION, patient_id=self.patient_id, run_id=self.run_id, kind=kind,
                            title=title[:250], rationale=rationale[:1990], citations=citations[:990],
                            payload=json.dumps(payload), escalation_id=escalation_id, new_id=new_id)
                action_id = int(new_id.getvalue()[0])
                if escalation_id is not None:
                    cur.execute("UPDATE DA_OWNER.agent_escalation SET status = 'accepted', action_id = :a, "
                                "resolution = :r, resolved_at = SYSTIMESTAMP WHERE id = :e",
                                a=action_id, r=rationale[:1990], e=escalation_id)
                conn.commit()
        except oracledb.DatabaseError as exc:
            return None, f"Refused by the database: {_first_line(exc)}"
        return action_id, (f"Proposed care action {action_id} ({kind}) for {self.patient_id}. Status: proposed. "
                           "It runs only if an authorised person approves it in the web application.")


def _medication_title(change: str, medication: str) -> str:
    return f"Medication change: {change} {medication}"


def build_care_tools(dsn: str, user: str, password: str, patient_id: str):
    """The care coordinator's tools: lab requests, a patient message, a
    follow-up, and escalation. It also holds propose_medication_change, which
    policy CP-03 refuses for this agent: the refusal is the path to escalation."""
    care = _Care(dsn, user, password, patient_id, COORDINATOR)

    @tool
    @_db_safe
    def list_care_actions() -> str:
        """List every care action ever proposed for this patient, newest first:
        id, kind, status (proposed, needs_physician, approved, executed,
        rejected), title, and what execution produced. Call this first: never
        propose again what is already executed, approved, pending, or was rejected."""
        return care.list_actions()

    @tool
    @_db_safe
    def propose_lab_request(tests: list[str], urgency: Literal["routine", "soon", "urgent"], reason: str, citations: str) -> str:
        """Propose a lab request for this patient, for the clinician to approve.

        tests: the specific tests, e.g. ["UACR", "basic metabolic panel"].
        urgency: routine, soon (before the visit), or urgent.
        reason: one or two sentences grounded in the chart.
        citations: the ids behind the reason, e.g. "[SQL:lab_result] [SYN-X-NOTE-0006]".
        """
        return care.propose("lab_request", f"Lab request: {', '.join(tests)}", reason, citations,
                            {"tests": tests, "urgency": urgency, "before_visit": urgency != "routine"})[1]

    @tool
    @_db_safe
    def draft_patient_message(subject: str, body: str, reason: str, citations: str) -> str:
        """Draft a portal message to the patient, for the clinician to approve.

        Write to the patient in plain, warm language at a sixth-grade reading
        level: why a follow-up visit is needed, what to bring or do before it,
        and when to seek care sooner. No diagnosis, no medication changes, no
        identifiers other than the first name. reason and citations explain the
        message to the clinician.
        """
        return care.propose("patient_message", f"Message: {subject}", reason, citations,
                            {"subject": subject, "body": body, "to": "the patient (portal, simulated)"})[1]

    @tool
    @_db_safe
    def propose_follow_up(within_days: int, visit_type: str, reason: str, citations: str) -> str:
        """Propose a follow-up appointment within a number of days, for the clinician to approve.

        within_days: 1 to 90. visit_type: e.g. "Heart failure clinic visit".
        reason and citations explain the timing to the clinician.
        """
        days = max(1, min(int(within_days), 90))
        return care.propose("follow_up", f"Follow-up: {visit_type} within {days} days", reason, citations,
                            {"within_days": days, "visit_type": visit_type})[1]

    @tool
    @_db_safe
    def propose_medication_change(medication: str, change: Literal["hold", "stop", "reduce", "start"], reason: str, citations: str) -> str:
        """Propose a medication change (hold, stop, reduce, start) for the
        chart's most important medication-safety concern.

        medication: the name exactly as this patient's chart lists it.
        reason and citations explain it. The database applies the care
        policies; if it refuses, its answer says what to do next.
        """
        return care.propose("medication_change", _medication_title(change, medication), reason, citations,
                            {"medication": medication, "change": change})[1]

    @tool
    @_db_safe
    def escalate_to_agent(to_agent: Literal["medication-safety"], subject: str, reason: str, citations: str) -> str:
        """Hand an action the database refused you to the agent that may take it.

        Only after a refusal: an escalation carries a policy decision, so try
        the action first. to_agent: medication-safety. subject: one line in
        your own words: the change you proposed and the finding behind it,
        for this patient. reason: what the chart shows and what you proposed.
        citations: the ids behind it.
        """
        import oracledb

        try:
            with care.connect() as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM DA_OWNER.policy_event WHERE run_id = :r AND agent = :a "
                            "AND decision = 'refused'", r=care.run_id, a=COORDINATOR)
                if not cur.fetchone()[0]:
                    return ("Refused: nothing was refused to you in this run, so there is nothing to escalate. "
                            "Propose the action yourself; escalate only if the database refuses it.")
                cur.execute("SELECT MIN(id), MIN(action_id) FROM DA_OWNER.agent_escalation WHERE run_id = :r AND status = 'accepted'",
                            r=care.run_id)
                done_esc, done_action = cur.fetchone()
                if done_esc:
                    return (f"Refused: escalation {done_esc} in this run is already resolved by the medication-safety "
                            f"agent (care action {done_action}, waiting for the doctor). Report it; do not escalate again.")
                cur.execute("SELECT MIN(id) FROM DA_OWNER.agent_escalation WHERE run_id = :r AND status = 'open'", r=care.run_id)
                pending = cur.fetchone()[0]
                if pending:
                    return (f"Refused: escalation {pending} is still open. Report its id to the lead, who delegates "
                            "it to the medication-safety agent; do not escalate again.")
                new_id = cur.var(oracledb.NUMBER)
                cur.execute(INSERT_ESCALATION, patient_id=patient_id, run_id=care.run_id, to_agent=to_agent,
                            subject=subject[:250], reason=reason[:1990], citations=citations[:990], new_id=new_id)
                conn.commit()
                esc = int(new_id.getvalue()[0])
        except oracledb.DatabaseError as exc:
            return f"Refused by the database: {_first_line(exc)}"
        return (f"Escalation {esc} opened for the {to_agent} agent (policy CP-03). "
                "Report its id to the lead; the lead delegates it to that agent.")

    return [list_care_actions, propose_lab_request, draft_patient_message, propose_follow_up,
            propose_medication_change, escalate_to_agent]


def build_medication_safety_tools(dsn: str, user: str, password: str, patient_id: str):
    """The medication-safety agent's tools: read escalations, then accept one
    with a medication change (which CP-02 sends to a doctor) or decline it."""
    care = _Care(dsn, user, password, patient_id, MEDICATION_SAFETY)

    def open_escalation(conn, escalation_id: int):
        cur = conn.cursor()
        cur.execute("SELECT status FROM DA_OWNER.agent_escalation WHERE id = :e AND to_agent = :a",
                    e=escalation_id, a=MEDICATION_SAFETY)
        row = cur.fetchone()
        return row[0] if row else None

    @tool
    @_db_safe
    def list_escalations() -> str:
        """List the escalations addressed to you for this patient, newest first:
        id, status (open, accepted, declined), who raised it, subject, reason
        and citations. Work only on open ones."""
        with care.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, status, from_agent, subject, reason, NVL(citations, '-') "
                        "FROM DA_OWNER.agent_escalation WHERE to_agent = :a ORDER BY created_at DESC "
                        "FETCH FIRST 20 ROWS ONLY", a=MEDICATION_SAFETY)
            rows = cur.fetchall()
        if not rows:
            return "No escalations for this patient."
        return "\n".join(f"#{i} [{st}] from {f}: {s}\n  reason: {r}\n  citations: {c}" for i, st, f, s, r, c in rows)

    @tool
    @_db_safe
    def list_care_actions() -> str:
        """List every care action ever proposed for this patient, newest first,
        with its status. Never propose a change that is already pending,
        executed, or was rejected."""
        return care.list_actions()

    @tool
    @_db_safe
    def propose_medication_change(escalation_id: int, medication: str, change: Literal["hold", "stop", "reduce", "start"],
                                  reason: str, citations: str) -> str:
        """Accept an open escalation by proposing one medication change.

        escalation_id: the open escalation you are resolving.
        medication: the name exactly as this patient's chart lists it.
        reason and citations: your own review of the chart and the reference.
        Policy CP-02 stores it as needs_physician: only the doctor can approve.
        """
        with care.connect() as conn:
            status = open_escalation(conn, escalation_id)
        if status != "open":
            return f"Refused: escalation {escalation_id} is {status or 'not addressed to you'}, not open."
        action_id, text = care.propose("medication_change", _medication_title(change, medication), reason, citations,
                                       {"medication": medication, "change": change}, escalation_id=escalation_id)
        if action_id is None:
            return text
        return (f"Proposed care action {action_id} (medication_change) on escalation {escalation_id}. "
                "Status: needs_physician (policy CP-02): only the doctor can approve it.")

    @tool
    @_db_safe
    def decline_escalation(escalation_id: int, reason: str) -> str:
        """Close an open escalation without a change, when your review finds no
        safety concern the chart supports. reason: why, with citations."""
        with care.connect() as conn:
            if open_escalation(conn, escalation_id) != "open":
                return f"Refused: escalation {escalation_id} is not open."
            conn.cursor().execute("UPDATE DA_OWNER.agent_escalation SET status = 'declined', resolution = :r, "
                                  "resolved_at = SYSTIMESTAMP WHERE id = :e", r=reason[:1990], e=escalation_id)
            conn.commit()
        return f"Escalation {escalation_id} declined."

    return [list_escalations, list_care_actions, propose_medication_change, decline_escalation]
