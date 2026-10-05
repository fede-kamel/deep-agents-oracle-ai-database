This is personal work with synthetic data only.

I followed `codex/SPEC.md` and `AGENTS.md`. Per operator context, I skipped SPEC 4.3, 4.4, 4.5, and 4.7b. I ran patient Y only.

**Preflight**
```text
PASS uv
PASS openshell CLI 0.1.2
PASS gateway connected
PASS sandbox image present
PASS provider on gateway
PASS config file
PASS secrets directory 0700
PASS secret DA_OWNER present
PASS secret DA_AGENT_X present
PASS secret DA_AGENT_Y present
PASS secret DA_AGENT_Z present
PASS database schema at head: 0008 (head)
PASS row-level security: VERIFY OK (25/25)
PASS vector stores loaded: PATIENT_NOTE_VEC=19 CLINICAL_REFERENCE=344 RESEARCH_EVIDENCE=955

PREFLIGHT OK
```

**Safety Probe**
```text
PASS key in the sandbox is a placeholder
PASS OCI GenAI chat completion
PASS Oracle AI Database listener
PASS refused: unlisted host
PASS refused: OCI Object Storage API
PASS refused: package registry
PASS refused: PUT on the allowed host

PROBE OK (7/7)
```

**RLS**
`uv run python scripts/verify.py --rls-only </dev/null` passed: `VERIFY OK (25/25)`.

**Patient Y Sandbox Run**
Run: `out/run-Y.jsonl`; brief: `out/brief-Y.md`.

Metrics:
```text
seconds: 322
tool calls: 37
SQL query tool calls: 4
searches: 21
delegations: 5
citations: 145
verify: passed
standalone brief verify: VERIFY OK (2/2)
```

Requested console policy path:
```text
POLICY CP-03: the care-coordinator agent may not propose a medication_change; escalate it to the medication-safety agent
policy CP-03: care-coordinator refused -> escalate to medication-safety
Escalation 17 opened for the medication-safety agent (policy CP-03)
Proposed care action 134 (medication_change) on escalation 17
Status: needs_physician
```

Care actions proposed in the patient Y run:
```text
#131 follow_up: urgent follow-up for worsening HF symptoms and post-discharge congestion
#132 lab_request: urine albumin-to-creatinine ratio
#133 patient_message: logistics/access-focused appointment and support message
#134 medication_change: medication-safety proposes holding spironolactone; awaits doctor under CP-02
```

**Web Application Check**
```text
PASS front end served
PASS patient cards
PASS agent channel streamed: 321 events
PASS sandbox console streamed: 595 lines
PASS run succeeded
PASS brief verified by the gate: citations=172
PASS Word export

WEBAPP OK (7/7)
```

The webapp-driven Y run took 879 seconds, with 102 tool calls, 24 SQL query tool calls, 39 searches, 20 delegations, and final verify passed.

**Section 7**
No `ABORT:` occurred. The webapp run hit the expected verifier repair path once: the first draft failed on invalid PMID citations, the runner repaired it, and final verify passed. The care-action cap also refused extra proposals with `Refused: 5 actions already proposed in this run`; the agent reused pending actions and completed.

**Post-Conditions**
`openshell sandbox list </dev/null` returned `No sandboxes found.`

I did not see password or key material in outputs. A filename-only scan found no configured DSN service token in the repo. A secret-shaped scan found only a literal scan pattern recorded in an evidence log, not an actual identifier.