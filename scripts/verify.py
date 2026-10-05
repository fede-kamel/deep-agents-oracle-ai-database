"""Verify a brief against the database, and verify the database's own guarantees.

    uv run python scripts/verify.py out/runs/<run>/brief-X.md   # check one brief
    uv run python scripts/verify.py --rls-only                  # row-level security only

For a brief: the structural checks the runner applies (agent/verify.py), then
every cited note id must exist for that patient, every MEDQUAD and PMID id
must exist in its store, and every [SQL:<table>] must name a chart table.
The lookups run as the patient's own read-only user, so a note id that
belongs to another patient fails just like one that does not exist.

For row-level security: each agent user sees exactly one patient, sees none
of another patient's rows, and is refused every write.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import oracledb

from agent import verify
from agent.sql_tools import CHART_TABLES
from common.config import (
    OWNER,
    PATIENT_KEYS,
    agent_user,
    load_config,
    password,
)


def connect(key: str):
    return oracledb.connect(user=agent_user(key), password=password(agent_user(key)), dsn=load_config()["dsn"])


def rls_checks() -> list[tuple[str, bool, str]]:
    results = []
    for key in PATIENT_KEYS:
        with connect(key) as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*), MIN(patient_id) FROM DA_OWNER.patient")
            n, pid = cur.fetchone()
            results.append((f"{agent_user(key)} sees one patient", n == 1 and pid == f"SYN-{key}", f"{n} visible ({pid})"))
            other = next(k for k in PATIENT_KEYS if k != key)
            cur.execute("SELECT COUNT(*) FROM DA_OWNER.lab_result WHERE patient_id = :p", p=f"SYN-{other}")
            hidden = cur.fetchone()[0]
            results.append((f"{agent_user(key)} cannot read SYN-{other}", hidden == 0, f"{hidden} rows"))
            cur.execute("SELECT COUNT(DISTINCT JSON_VALUE(metadata, '$.patient_id')) FROM PATIENT_NOTE_VEC")
            vec = cur.fetchone()[0]
            results.append((f"{agent_user(key)} vector notes scoped", vec == 1, f"{vec} patient in PATIENT_NOTE_VEC"))
            try:
                cur.execute("UPDATE DA_OWNER.medication SET dose = dose")
                conn.rollback()
                results.append((f"{agent_user(key)} write refused", False, "UPDATE succeeded"))
            except oracledb.DatabaseError as exc:
                results.append((f"{agent_user(key)} write refused", True, str(exc).split(":")[0]))
    # Care actions: an agent proposes for its own patient only, cannot approve,
    # cannot execute; the clinician's approval executes and is audited.
    with connect("X") as conn:
        cur = conn.cursor()
        new_id = cur.var(oracledb.NUMBER)
        cur.execute("INSERT INTO DA_OWNER.care_action (patient_id, run_id, kind, status, title, rationale, payload) "
                    "VALUES ('SYN-X', 'verify', 'lab_request', 'executed', 'verify probe', 'verify probe', JSON('{\"tests\": [\"UACR\"], \"urgency\": \"soon\"}')) "
                    "RETURNING id INTO :i", i=new_id)
        conn.commit()
        probe_id = int(new_id.getvalue()[0])
        cur.execute("SELECT status, proposed_by FROM DA_OWNER.care_action WHERE id = :i", i=probe_id)
        st, by = cur.fetchone()
        results.append(("agent proposal is forced to proposed", st == "proposed" and by == "DA_AGENT_X", f"asked for 'executed', stored {st} by {by}"))
        for label, sql in (
            ("agent cannot propose for SYN-Y", "INSERT INTO DA_OWNER.care_action (patient_id, kind, title, rationale, payload) VALUES ('SYN-Y', 'lab_request', 'x', 'x', JSON('{}'))"),
            ("agent cannot approve (UPDATE)", f"UPDATE DA_OWNER.care_action SET status = 'approved' WHERE id = {probe_id}"),
            ("agent cannot execute", f"BEGIN DA_OWNER.DECIDE_CARE_ACTION({probe_id}, 'approve'); END;"),
        ):
            try:
                cur.execute(sql)
                conn.rollback()
                results.append((label, False, "statement succeeded"))
            except oracledb.DatabaseError as exc:
                conn.rollback()
                results.append((label, True, str(exc).split(":")[0]))
    with oracledb.connect(user="DA_CLINICIAN", password=password("DA_CLINICIAN"), dsn=load_config()["dsn"]) as conn:
        cur = conn.cursor()
        cur.callproc("DA_OWNER.DECIDE_CARE_ACTION", [probe_id, "approve", None, "verify.py probe"])
        cur.execute("SELECT status, result_table FROM DA_OWNER.care_action WHERE id = :i", i=probe_id)
        st, tab = cur.fetchone()
        cur.execute("SELECT LISTAGG(status, '>') WITHIN GROUP (ORDER BY id) FROM DA_OWNER.care_action_event WHERE action_id = :i", i=probe_id)
        trail = cur.fetchone()[0]
        results.append(("clinician approval executes and audits", st == "executed" and tab == "LAB_ORDER" and trail == "proposed>approved>executed", f"{st} → {tab}; {trail}"))
    # Policy CP-03: only the medication-safety agent may propose a medication
    # change. The care coordinator is refused and the refusal is logged; its
    # escalation is stamped with its own name, whatever the row claims.
    # The probe holds one of Y's active medications and restores it afterwards,
    # so it does not depend on what the demo has already executed.
    with oracledb.connect(user=OWNER, password=password(OWNER), dsn=load_config()["dsn"]) as conn:
        cur = conn.cursor()
        cur.execute("SELECT name FROM DA_OWNER.medication WHERE patient_id = 'SYN-Y' AND status = 'active' ORDER BY id FETCH FIRST 1 ROW ONLY")
        probe_med = cur.fetchone()[0]
    med_insert = ("INSERT INTO DA_OWNER.care_action (patient_id, run_id, kind, title, rationale, payload) "
                  "VALUES ('SYN-Y', 'verify', 'medication_change', 'verify probe', 'verify probe', "
                  "JSON(:payload)) RETURNING id INTO :i")
    med_payload = json.dumps({"medication": probe_med, "change": "hold"})
    with connect("Y") as conn:
        conn.client_identifier = "care-coordinator"
        cur = conn.cursor()
        try:
            cur.execute(med_insert, payload=med_payload, i=cur.var(oracledb.NUMBER))
            conn.rollback()
            results.append(("care coordinator cannot propose a medication change (CP-03)", False, "insert succeeded"))
        except oracledb.DatabaseError as exc:
            conn.rollback()
            results.append(("care coordinator cannot propose a medication change (CP-03)", "ORA-20014" in str(exc), str(exc).split(":")[0]))
        cur.execute("SELECT COUNT(*) FROM DA_OWNER.policy_event WHERE run_id = 'verify' AND policy_code = 'CP-03' "
                    "AND decision = 'refused' AND agent = 'care-coordinator'")
        logged = cur.fetchone()[0]
        results.append(("the refusal is logged despite the rollback", logged >= 1, f"{logged} policy_event rows"))
        esc = cur.var(oracledb.NUMBER)
        cur.execute("INSERT INTO DA_OWNER.agent_escalation (patient_id, run_id, from_agent, to_agent, policy_code, subject, reason) "
                    "VALUES ('SYN-Y', 'verify', 'medication-safety', 'medication-safety', 'CP-03', 'verify probe', 'verify probe') "
                    "RETURNING id INTO :i", i=esc)
        conn.commit()
        cur.execute("SELECT from_agent, status FROM DA_OWNER.agent_escalation WHERE id = :i", i=int(esc.getvalue()[0]))
        frm, est = cur.fetchone()
        results.append(("escalation is stamped with the real sender", frm == "care-coordinator" and est == "open", f"claimed medication-safety, stored {frm} ({est})"))
    # Policy CP-02: the medication-safety agent's change waits for a physician;
    # the clinician is refused, the physician's approval executes it.
    with connect("Y") as conn:
        conn.client_identifier = "medication-safety"
        cur = conn.cursor()
        med_id = cur.var(oracledb.NUMBER)
        cur.execute(med_insert, payload=med_payload, i=med_id)
        conn.commit()
        med_probe = int(med_id.getvalue()[0])
        cur.execute("SELECT status, policy_code, proposed_agent FROM DA_OWNER.care_action WHERE id = :i", i=med_probe)
        st, code, agent = cur.fetchone()
        results.append(("medication-safety's change goes to the doctor (CP-02)", st == "needs_physician" and code == "CP-02" and agent == "medication-safety",
                        f"stored {st} under {code} by {agent}"))
    with oracledb.connect(user="DA_CLINICIAN", password=password("DA_CLINICIAN"), dsn=load_config()["dsn"]) as conn:
        try:
            conn.cursor().callproc("DA_OWNER.DECIDE_CARE_ACTION", [med_probe, "approve", None, "verify.py probe"])
            results.append(("clinician cannot approve it (CP-02)", False, "approval succeeded"))
        except oracledb.DatabaseError as exc:
            results.append(("clinician cannot approve it (CP-02)", "-20012" in str(exc) or "ORA-20012" in str(exc), str(exc).split(":")[0]))
    with oracledb.connect(user="DA_PHYSICIAN", password=password("DA_PHYSICIAN"), dsn=load_config()["dsn"]) as conn:
        cur = conn.cursor()
        cur.callproc("DA_OWNER.DECIDE_CARE_ACTION", [med_probe, "approve", None, "verify.py probe"])
        cur.execute("SELECT status, result_table FROM DA_OWNER.care_action WHERE id = :i", i=med_probe)
        st, tab = cur.fetchone()
        cur.execute("SELECT status FROM DA_OWNER.medication WHERE patient_id = 'SYN-Y' AND name = :n", n=probe_med)
        med_status = cur.fetchone()[0]
        results.append(("physician approval executes it", st == "executed" and tab == "MEDICATION" and med_status == "held", f"{st}; {probe_med} now {med_status}"))
    with oracledb.connect(user=OWNER, password=password(OWNER), dsn=load_config()["dsn"]) as conn:
        cur = conn.cursor()
        cur.execute("UPDATE DA_OWNER.medication SET status = 'active', order_note = NULL WHERE patient_id = 'SYN-Y' AND name = :n", n=probe_med)
        cur.execute("DELETE FROM DA_OWNER.care_action_event WHERE action_id = :i", i=med_probe)
        cur.execute("DELETE FROM DA_OWNER.care_action WHERE id = :i", i=med_probe)
        cur.execute("DELETE FROM DA_OWNER.agent_escalation WHERE run_id = 'verify'")
        cur.execute("DELETE FROM DA_OWNER.policy_event WHERE run_id = 'verify'")
        conn.commit()

    with oracledb.connect(user=OWNER, password=password(OWNER), dsn=load_config()["dsn"]) as conn:
        cur = conn.cursor()
        for t in ("lab_order", "care_action_event"):
            cur.execute(f"DELETE FROM DA_OWNER.{t} WHERE action_id = :i", i=probe_id)
        cur.execute("DELETE FROM DA_OWNER.care_action WHERE id = :i", i=probe_id)
        conn.commit()

    # The schema itself refuses anything that is not marked synthetic.
    with oracledb.connect(user=OWNER, password=password(OWNER), dsn=load_config()["dsn"]) as conn:
        cur = conn.cursor()
        for pid, flag, label in (("REAL-0001", "Y", "id without SYN-"), ("SYN-T", "N", "is_synthetic = 'N'")):
            try:
                cur.execute("INSERT INTO DA_OWNER.patient (patient_id, display_name, alias, birth_year, sex, is_synthetic) "
                            "VALUES (:1, 'probe', 'probe', 1970, 'n/a', :2)", [pid, flag])
                conn.rollback()
                results.append((f"schema rejects {label}", False, "insert succeeded"))
            except oracledb.DatabaseError as exc:
                conn.rollback()
                results.append((f"schema rejects {label}", True, str(exc).split(":")[0]))
    return results


def brief_checks(path: Path) -> list[tuple[str, bool, str]]:
    text = path.read_text()
    m = re.search(r"\((SYN-([XYZ]))\)", text)
    if not m:
        return [("brief names its patient", False, "no (SYN-X|Y|Z) in the title")]
    pid, key = m.group(1), m.group(2)
    results = [("structure and grounding", not (p := verify.problems(text, pid)), "; ".join(p) or "all sections, citations of every kind")]
    ids = sorted(set(verify.citations(text)))
    with connect(key) as conn:
        cur = conn.cursor()

        def exists(table: str, doc_id: str) -> bool:
            cur.execute(f"SELECT COUNT(*) FROM {table} WHERE JSON_VALUE(metadata, '$.id') = :i", i=doc_id)
            return cur.fetchone()[0] > 0

        bad: list[str] = []
        for cid in ids:
            base = cid.split("#")[0]
            if base.startswith("SQL:"):
                ok = base[4:].lower() in CHART_TABLES
            elif base.startswith("SYN-"):
                ok = exists("PATIENT_NOTE_VEC", base)
            elif base.startswith("MEDQUAD-"):
                ok = exists("CLINICAL_REFERENCE", base)
            elif base.startswith("PMID-"):
                ok = exists("RESEARCH_EVIDENCE", base)
            else:
                ok = False
            if not ok:
                bad.append(cid)
    results.append((f"{len(ids)} cited ids resolve in the database", not bad, ", ".join(bad) or "every id found, as the patient's own user"))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("brief", nargs="?", type=Path)
    parser.add_argument("--rls-only", action="store_true")
    args = parser.parse_args()
    results = rls_checks() if args.rls_only or not args.brief else []
    if args.brief:
        results += brief_checks(args.brief)
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name:<42} {detail}")
    passed = all(ok for _, ok, _ in results)
    print(f"\n{'VERIFY OK' if passed else 'VERIFY FAILED'} ({sum(ok for _, ok, _ in results)}/{len(results)})")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
