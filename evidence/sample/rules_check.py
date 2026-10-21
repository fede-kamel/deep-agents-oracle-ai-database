"""Check the sample's database rules as SAMPLE_AGENT_A, without a model."""
import sys, oracledb
pw = open(sys.argv[1]).read().strip()
ok = 0; total = 0
def check(name, cond, detail=""):
    global ok, total
    total += 1; ok += bool(cond)
    print(("PASS " if cond else "FAIL ") + name + (f"  ({detail})" if detail else ""))
def conn(agent):
    c = oracledb.connect(user="SAMPLE_AGENT_A", password=pw, dsn="localhost:1521/FREEPDB1")
    c.client_identifier = agent
    return c
def err(fn):
    try:
        fn(); return None
    except oracledb.DatabaseError as e:
        return str(e).splitlines()[0]
with conn("chart-analyst") as c:
    cur = c.cursor()
    cur.execute("SELECT patient_id FROM SAMPLE_OWNER.patient"); rows = cur.fetchall()
    check("agent A sees only SYN-A", rows == [("SYN-A",)], str(rows))
    cur.execute("SELECT COUNT(*) FROM SAMPLE_OWNER.lab_result"); n = cur.fetchone()[0]
    check("agent A sees 5 labs (not B's)", n == 5, str(n))
    cur.execute("SELECT COUNT(*) FROM SAMPLE_OWNER.medication WHERE med_id = 'MED-B-001'")
    check("another patient's id is invisible", cur.fetchone()[0] == 0)
    e = err(lambda: cur.execute("UPDATE SAMPLE_OWNER.lab_result SET value = 1"))
    check("agent cannot update the chart", e and ("ORA-01031" in e or "ORA-41900" in e), e)
    e = err(lambda: cur.execute("DELETE FROM SAMPLE_OWNER.care_action"))
    check("agent cannot delete proposals", e and ("ORA-01031" in e or "ORA-41900" in e), e)
ins = ("INSERT INTO SAMPLE_OWNER.care_action (patient_id, kind, title, status) "
       "VALUES (:p, :k, 'rules check', 'approved')")
with conn("care-coordinator") as c:
    cur = c.cursor()
    e = err(lambda: cur.execute(ins, p="SYN-A", k="medication_change"))
    check("care-coordinator medication change refused", e and "ORA-20014" in e, e)
    c.rollback()
    e = err(lambda: cur.execute(ins, p="SYN-B", k="lab_request"))
    check("proposal for another patient refused", e and "ORA-28115" in e, e)
    c.rollback()
    cur.execute(ins, p="SYN-A", k="lab_request")
    cur.execute("SELECT status, proposed_agent FROM SAMPLE_OWNER.care_action WHERE title = 'rules check'")
    r = cur.fetchone()
    check("lab request starts as 'proposed' whatever the agent asked", r == ("proposed", "care-coordinator"), str(r))
    c.rollback()
with conn("medication-safety") as c:
    cur = c.cursor()
    cur.execute(ins, p="SYN-A", k="medication_change")
    cur.execute("SELECT status FROM SAMPLE_OWNER.care_action WHERE title = 'rules check'")
    r = cur.fetchone()
    check("medication-safety change waits for a physician", r == ("needs_physician",), str(r))
    c.rollback()
print(f"\nRULES {'OK' if ok == total else 'FAILED'} ({ok}/{total})")
