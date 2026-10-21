-- As SAMPLE_OWNER:  sql sample_owner@<connect string> @sql/02_schema.sql
-- A tiny chart, one care-action table, and the three rules the agents cannot
-- argue with: synthetic ids only, one patient per agent login, and only the
-- medication-safety agent may propose a medication change.

-- 1. The chart. Synthetic only: the CHECK rejects any id without SYN-.
CREATE TABLE patient (
  patient_id VARCHAR2(16) PRIMARY KEY CHECK (patient_id LIKE 'SYN-%'),
  name       VARCHAR2(80) NOT NULL,
  summary    VARCHAR2(400)
);
CREATE TABLE medication (
  med_id     VARCHAR2(20) PRIMARY KEY,               -- cited as [MED-A-001]
  patient_id VARCHAR2(16) NOT NULL REFERENCES patient,
  name       VARCHAR2(60) NOT NULL,
  dose       VARCHAR2(60) NOT NULL
);
CREATE TABLE lab_result (
  lab_id     VARCHAR2(20) PRIMARY KEY,               -- cited as [LAB-A-001]
  patient_id VARCHAR2(16) NOT NULL REFERENCES patient,
  test       VARCHAR2(40) NOT NULL,
  value      NUMBER       NOT NULL,
  unit       VARCHAR2(16),
  taken_on   DATE         NOT NULL
);

-- 2. Care actions: agents propose, people decide.
CREATE TABLE care_action (
  id             NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  patient_id     VARCHAR2(16)  NOT NULL REFERENCES patient,
  kind           VARCHAR2(30)  NOT NULL CHECK (kind IN ('lab_request', 'follow_up', 'medication_change')),
  title          VARCHAR2(250) NOT NULL,
  rationale      VARCHAR2(2000),
  citations      VARCHAR2(1000),
  status         VARCHAR2(20)  DEFAULT 'proposed' NOT NULL,
  proposed_agent VARCHAR2(64),
  proposed_by    VARCHAR2(128),
  created_at     TIMESTAMP DEFAULT SYSTIMESTAMP
);
CREATE TABLE policy_event (
  id         NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  patient_id VARCHAR2(16),
  agent      VARCHAR2(64),
  decision   VARCHAR2(20),
  detail     VARCHAR2(400),
  created_at TIMESTAMP DEFAULT SYSTIMESTAMP
);

-- A refusal is recorded even though the refused insert rolls back.
CREATE OR REPLACE PROCEDURE log_policy_event(p_patient VARCHAR2, p_agent VARCHAR2,
                                             p_decision VARCHAR2, p_detail VARCHAR2) AS
  PRAGMA AUTONOMOUS_TRANSACTION;
BEGIN
  INSERT INTO policy_event (patient_id, agent, decision, detail)
  VALUES (p_patient, p_agent, p_decision, SUBSTR(p_detail, 1, 400));
  COMMIT;
END;
/

-- 3. The agent policy. The tool code stamps each connection with the calling
-- agent's name (CLIENT_IDENTIFIER); the model never sets it.
CREATE OR REPLACE TRIGGER trg_care_action_propose
BEFORE INSERT ON care_action FOR EACH ROW
DECLARE
  v_agent VARCHAR2(64) := NVL(SYS_CONTEXT('USERENV', 'CLIENT_IDENTIFIER'), 'unknown');
BEGIN
  IF :NEW.kind = 'medication_change' AND v_agent <> 'medication-safety' THEN
    -- the refusal is logged in its own transaction, so it survives the rollback
    log_policy_event(:NEW.patient_id, v_agent, 'refused', :NEW.title);
    RAISE_APPLICATION_ERROR(-20014, 'policy: the ' || v_agent
      || ' agent may not propose a medication change;'
      || ' report this to the lead so it can ask the medication-safety agent');
  END IF;
  -- Whatever the agent asked for, a proposal starts as a proposal; a
  -- medication change waits for a physician.
  :NEW.status := CASE WHEN :NEW.kind = 'medication_change'
                      THEN 'needs_physician' ELSE 'proposed' END;
  :NEW.proposed_agent := v_agent;
  :NEW.proposed_by := SYS_CONTEXT('USERENV', 'SESSION_USER');
  :NEW.created_at := SYSTIMESTAMP;
END;
/

-- 4. Row-level security: SAMPLE_AGENT_A sees and proposes for SYN-A only.
CREATE OR REPLACE FUNCTION patient_scope(p_schema IN VARCHAR2, p_object IN VARCHAR2)
RETURN VARCHAR2 AS
  v_user VARCHAR2(128) := SYS_CONTEXT('USERENV', 'SESSION_USER');
BEGIN
  IF v_user = 'SAMPLE_OWNER' THEN
    RETURN '1=1';
  ELSIF REGEXP_LIKE(v_user, '^SAMPLE_AGENT_[A-Z]$') THEN
    RETURN 'patient_id = ''SYN-' || SUBSTR(v_user, -1) || '''';
  END IF;
  RETURN '1=0';
END;
/
BEGIN
  FOR t IN (SELECT column_value AS name
              FROM TABLE(sys.odcivarchar2list('PATIENT', 'MEDICATION', 'LAB_RESULT', 'CARE_ACTION'))) LOOP
    DBMS_RLS.ADD_POLICY(object_schema   => 'SAMPLE_OWNER', object_name => t.name,
                        policy_name     => 'SCOPE_' || t.name,
                        function_schema => 'SAMPLE_OWNER', policy_function => 'PATIENT_SCOPE',
                        statement_types => 'SELECT,INSERT,UPDATE,DELETE', update_check => TRUE);
  END LOOP;
END;
/

-- 5. The agent reads the chart and may only INSERT proposals.
GRANT SELECT ON patient TO sample_agent_a;
GRANT SELECT ON medication TO sample_agent_a;
GRANT SELECT ON lab_result TO sample_agent_a;
GRANT SELECT, INSERT ON care_action TO sample_agent_a;

-- 6. Two invented patients. The agent for A never sees B.
INSERT INTO patient VALUES ('SYN-A', 'Patient A', 'Type 2 diabetes; kidney function declining; reports low sugar spells in the afternoon.');
INSERT INTO patient VALUES ('SYN-B', 'Patient B', 'Heart failure; stable.');
INSERT INTO medication VALUES ('MED-A-001', 'SYN-A', 'metformin', '1000 mg twice daily');
INSERT INTO medication VALUES ('MED-A-002', 'SYN-A', 'glipizide', '10 mg twice daily');
INSERT INTO medication VALUES ('MED-A-003', 'SYN-A', 'ibuprofen', '400 mg as needed, most days');
INSERT INTO medication VALUES ('MED-B-001', 'SYN-B', 'furosemide', '40 mg daily');
INSERT INTO lab_result VALUES ('LAB-A-001', 'SYN-A', 'eGFR', 68, 'mL/min/1.73m2', DATE '2025-03-10');
INSERT INTO lab_result VALUES ('LAB-A-002', 'SYN-A', 'eGFR', 55, 'mL/min/1.73m2', DATE '2025-11-02');
INSERT INTO lab_result VALUES ('LAB-A-003', 'SYN-A', 'eGFR', 47, 'mL/min/1.73m2', DATE '2026-08-20');
INSERT INTO lab_result VALUES ('LAB-A-004', 'SYN-A', 'glucose', 62, 'mg/dL', DATE '2026-08-20');
INSERT INTO lab_result VALUES ('LAB-A-005', 'SYN-A', 'HbA1c', 8.4, '%', DATE '2026-08-20');
INSERT INTO lab_result VALUES ('LAB-B-001', 'SYN-B', 'potassium', 4.2, 'mmol/L', DATE '2026-09-01');
COMMIT;
