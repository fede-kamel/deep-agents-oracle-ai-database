"""Care policies: some actions need a doctor.

A policy table maps each kind of care action to the role that may approve it.
Lab requests, patient messages and follow-ups need a clinician (DA_CLINICIAN);
a medication change needs a physician (DA_PHYSICIAN). The proposal trigger now
looks the policy up: a proposal whose policy requires a physician is stored as
`needs_physician`, with an audit entry naming the policy, instead of
`proposed`. DECIDE_CARE_ACTION refuses to approve an action unless the
session's role is the one the policy requires, and executes an approved
medication change by recording a physician order on the medication row.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-05
"""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

PHYSICIAN = "DA_PHYSICIAN"
CLINICIAN = "DA_CLINICIAN"

DDL = [
    """CREATE TABLE care_policy (
         code VARCHAR2(16) PRIMARY KEY,
         kind VARCHAR2(32) NOT NULL UNIQUE,
         required_role VARCHAR2(32) NOT NULL CHECK (required_role IN ('clinician', 'physician')),
         rule_text VARCHAR2(400) NOT NULL)""",
    "INSERT INTO care_policy VALUES ('CP-01a', 'lab_request', 'clinician', 'Lab requests may be approved by the care team clinician.')",
    "INSERT INTO care_policy VALUES ('CP-01b', 'patient_message', 'clinician', 'Patient portal messages may be approved by the care team clinician.')",
    "INSERT INTO care_policy VALUES ('CP-01c', 'follow_up', 'clinician', 'Follow-up appointment requests may be approved by the care team clinician.')",
    "INSERT INTO care_policy VALUES ('CP-02', 'medication_change', 'physician', 'Medication changes (hold, stop, reduce, start) require a physician''s approval; the care coordinator cannot approve them and a clinician cannot either.')",
    "ALTER TABLE care_action DROP CONSTRAINT " + "{kind_check}",
    "ALTER TABLE care_action ADD CONSTRAINT ck_care_action_kind CHECK (kind IN ('lab_request', 'patient_message', 'follow_up', 'medication_change'))",
    "ALTER TABLE care_action DROP CONSTRAINT " + "{status_check}",
    "ALTER TABLE care_action ADD CONSTRAINT ck_care_action_status CHECK (status IN ('proposed', 'needs_physician', 'approved', 'executed', 'rejected'))",
    "ALTER TABLE care_action ADD (policy_code VARCHAR2(16), required_role VARCHAR2(32))",
    "ALTER TABLE medication ADD (order_note VARCHAR2(400))",
]

TRIGGER_PROPOSE = """
CREATE OR REPLACE TRIGGER trg_care_action_propose
BEFORE INSERT ON care_action FOR EACH ROW
DECLARE
  v_code care_policy.code%TYPE;
  v_role care_policy.required_role%TYPE;
BEGIN
  SELECT code, required_role INTO v_code, v_role FROM care_policy WHERE kind = :NEW.kind;
  :NEW.policy_code := v_code;
  :NEW.required_role := v_role;
  :NEW.status := CASE WHEN v_role = 'physician' THEN 'needs_physician' ELSE 'proposed' END;
  :NEW.proposed_by := SYS_CONTEXT('USERENV', 'SESSION_USER');
  :NEW.created_at := SYSTIMESTAMP;
  :NEW.decided_by := NULL; :NEW.decided_at := NULL;
  :NEW.result_table := NULL; :NEW.result_id := NULL; :NEW.result_summary := NULL;
END;
"""
TRIGGER_AUDIT = """
CREATE OR REPLACE TRIGGER trg_care_action_audit
AFTER INSERT ON care_action FOR EACH ROW
BEGIN
  INSERT INTO care_action_event (action_id, patient_id, status, actor, note)
  VALUES (:NEW.id, :NEW.patient_id, 'proposed', :NEW.proposed_by, 'drafted by the care coordinator agent');
  IF :NEW.status = 'needs_physician' THEN
    INSERT INTO care_action_event (action_id, patient_id, status, actor, note)
    VALUES (:NEW.id, :NEW.patient_id, 'needs_physician', 'policy ' || :NEW.policy_code,
            'policy ' || :NEW.policy_code || ': medication changes require a physician; escalated for doctor approval');
  END IF;
END;
"""

PROCEDURE = """
CREATE OR REPLACE PROCEDURE decide_care_action(
  p_id IN NUMBER, p_decision IN VARCHAR2, p_payload IN CLOB DEFAULT NULL, p_note IN VARCHAR2 DEFAULT NULL)
AUTHID DEFINER AS
  v_actor   VARCHAR2(128) := SYS_CONTEXT('USERENV', 'SESSION_USER');
  v_role    VARCHAR2(32)  := CASE SYS_CONTEXT('USERENV', 'SESSION_USER')
                                WHEN 'DA_PHYSICIAN' THEN 'physician'
                                WHEN 'DA_CLINICIAN' THEN 'clinician' ELSE 'none' END;
  v_row     care_action%ROWTYPE;
  v_new_id  NUMBER;
  v_summary VARCHAR2(400);
  v_med     VARCHAR2(128);
BEGIN
  SELECT * INTO v_row FROM care_action WHERE id = p_id FOR UPDATE;
  IF v_row.status NOT IN ('proposed', 'needs_physician') THEN
    RAISE_APPLICATION_ERROR(-20010, 'care action ' || p_id || ' is ' || v_row.status || ', not awaiting a decision');
  END IF;
  -- A physician may decide anything a clinician may; a clinician may not
  -- decide what the policy reserves for a physician.
  IF v_role = 'none' OR (v_row.required_role = 'physician' AND v_role <> 'physician') THEN
    INSERT INTO care_action_event (action_id, patient_id, status, actor, note)
    VALUES (p_id, v_row.patient_id, 'refused', v_actor,
            'policy ' || v_row.policy_code || ': only a physician may decide this action');
    COMMIT;
    RAISE_APPLICATION_ERROR(-20012, 'policy ' || v_row.policy_code || ': ' || v_actor || ' may not decide this action; a physician must');
  END IF;

  IF p_decision = 'reject' THEN
    UPDATE care_action SET status = 'rejected', decided_by = v_actor, decided_at = SYSTIMESTAMP WHERE id = p_id;
    INSERT INTO care_action_event (action_id, patient_id, status, actor, note)
    VALUES (p_id, v_row.patient_id, 'rejected', v_actor, p_note);
    COMMIT;
    RETURN;
  ELSIF p_decision <> 'approve' THEN
    RAISE_APPLICATION_ERROR(-20011, 'decision must be approve or reject');
  END IF;

  IF p_payload IS NOT NULL THEN
    UPDATE care_action SET payload = JSON(p_payload) WHERE id = p_id;
    v_row.payload := JSON(p_payload);
  END IF;
  UPDATE care_action SET status = 'approved', decided_by = v_actor, decided_at = SYSTIMESTAMP WHERE id = p_id;
  INSERT INTO care_action_event (action_id, patient_id, status, actor, note)
  VALUES (p_id, v_row.patient_id, 'approved', v_actor, NVL(p_note, 'approved in the web application'));

  IF v_row.kind = 'lab_request' THEN
    INSERT INTO lab_order (patient_id, action_id, tests, urgency, reason, ordered_by)
    VALUES (v_row.patient_id, p_id, JSON_QUERY(v_row.payload, '$.tests' RETURNING CLOB),
            JSON_VALUE(v_row.payload, '$.urgency'), v_row.rationale, v_actor)
    RETURNING id INTO v_new_id;
    v_summary := 'lab_order ' || v_new_id || ' ordered: '
                 || JSON_QUERY(v_row.payload, '$.tests' RETURNING VARCHAR2(300));
    UPDATE care_action SET result_table = 'LAB_ORDER', result_id = v_new_id, result_summary = v_summary WHERE id = p_id;
  ELSIF v_row.kind = 'patient_message' THEN
    INSERT INTO patient_message (patient_id, action_id, subject, body)
    VALUES (v_row.patient_id, p_id, JSON_VALUE(v_row.payload, '$.subject'),
            JSON_VALUE(v_row.payload, '$.body' RETURNING VARCHAR2(4000)))
    RETURNING id INTO v_new_id;
    v_summary := 'patient_message ' || v_new_id || ' queued to the portal outbox (simulated)';
    UPDATE care_action SET result_table = 'PATIENT_MESSAGE', result_id = v_new_id, result_summary = v_summary WHERE id = p_id;
  ELSIF v_row.kind = 'medication_change' THEN
    v_med := JSON_VALUE(v_row.payload, '$.medication');
    UPDATE medication
       SET status = CASE JSON_VALUE(v_row.payload, '$.change') WHEN 'stop' THEN 'stopped' WHEN 'hold' THEN 'held' ELSE status END,
           order_note = 'physician order ' || TO_CHAR(SYSDATE, 'YYYY-MM-DD') || ': ' || JSON_VALUE(v_row.payload, '$.change')
                        || ' (care action ' || p_id || ', ' || v_actor || ')'
     WHERE patient_id = v_row.patient_id AND UPPER(name) = UPPER(v_med) AND status = 'active'
    RETURNING id INTO v_new_id;
    IF v_new_id IS NULL THEN
      RAISE_APPLICATION_ERROR(-20013, 'no active medication named ' || v_med || ' for this patient');
    END IF;
    v_summary := 'medication ' || v_new_id || ' (' || v_med || '): ' || JSON_VALUE(v_row.payload, '$.change') || ' by physician order';
    UPDATE care_action SET result_table = 'MEDICATION', result_id = v_new_id, result_summary = v_summary WHERE id = p_id;
  ELSE
    INSERT INTO appointment (patient_id, scheduled_for, kind, status)
    VALUES (v_row.patient_id,
            TRUNC(SYSDATE) + NVL(TO_NUMBER(JSON_VALUE(v_row.payload, '$.within_days')), 14),
            NVL(JSON_VALUE(v_row.payload, '$.visit_type'), 'Follow-up visit'), 'requested')
    RETURNING id INTO v_new_id;
    v_summary := 'appointment ' || v_new_id || ' requested within '
                 || NVL(JSON_VALUE(v_row.payload, '$.within_days'), '14') || ' days';
    UPDATE care_action SET result_table = 'APPOINTMENT', result_id = v_new_id, result_summary = v_summary WHERE id = p_id;
  END IF;

  UPDATE care_action SET status = 'executed' WHERE id = p_id;
  INSERT INTO care_action_event (action_id, patient_id, status, actor, note)
  VALUES (p_id, v_row.patient_id, 'executed', 'database: DECIDE_CARE_ACTION', v_summary);
  COMMIT;
END;
"""

SCOPE = """
CREATE OR REPLACE FUNCTION DA_PATIENT_SCOPE(p_schema IN VARCHAR2, p_object IN VARCHAR2)
RETURN VARCHAR2 AS
  v_user VARCHAR2(128) := SYS_CONTEXT('USERENV', 'SESSION_USER');
  v_col  VARCHAR2(64)  := CASE WHEN p_object = 'PATIENT_NOTE_VEC'
                               THEN 'JSON_VALUE(metadata, ''$.patient_id'')'
                               ELSE 'patient_id' END;
BEGIN
  IF v_user IN ('DA_OWNER', 'DA_CLINICIAN', 'DA_PHYSICIAN') THEN
    RETURN '1=1';
  ELSIF REGEXP_LIKE(v_user, '^DA_AGENT_[A-Z]$') THEN
    RETURN v_col || ' = ''SYN-' || SUBSTR(v_user, -1) || '''';
  END IF;
  RETURN '1=0';
END;
"""


def _raw(sql: str) -> None:
    op.get_bind().exec_driver_sql(sql)


def _check_name(column: str) -> str:
    """The system-generated name of the inline CHECK on care_action.<column>."""
    rows = op.get_bind().exec_driver_sql(
        "SELECT constraint_name, search_condition_vc FROM user_constraints "
        "WHERE table_name = 'CARE_ACTION' AND constraint_type = 'C'"
    ).fetchall()
    for name, cond in rows:
        if cond and cond.strip().upper().startswith(column.upper() + " IN"):
            return name
    raise RuntimeError(f"no CHECK constraint on care_action.{column}")


def upgrade() -> None:
    names = {"kind_check": _check_name("kind"), "status_check": _check_name("status")}
    for sql in DDL:
        _raw(sql.format(**names))
    _raw(TRIGGER_PROPOSE)
    _raw(TRIGGER_AUDIT)
    _raw(PROCEDURE)
    _raw(SCOPE)
    for table in ("CARE_ACTION", "CARE_ACTION_EVENT", "LAB_ORDER", "PATIENT_MESSAGE", "PATIENT", "APPOINTMENT", "MEDICATION", "CARE_POLICY"):
        _raw(f"GRANT SELECT ON {table} TO {PHYSICIAN}")
    _raw(f"GRANT SELECT ON care_policy TO {CLINICIAN}")
    _raw("GRANT SELECT ON care_policy TO DA_AGENT_X")
    _raw("GRANT SELECT ON care_policy TO DA_AGENT_Y")
    _raw("GRANT SELECT ON care_policy TO DA_AGENT_Z")
    _raw(f"GRANT EXECUTE ON decide_care_action TO {PHYSICIAN}")


def downgrade() -> None:
    _raw("ALTER TABLE medication DROP COLUMN order_note")
    _raw("ALTER TABLE care_action DROP (policy_code, required_role)")
    _raw("DROP TABLE care_policy PURGE")
