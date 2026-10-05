# Evidence

Every number in the README and the deck comes from a file in this folder.
Identifiers that would locate the database (its service name) or any account
never appear; the database host is Oracle's public regional endpoint.

| File | What it is |
|---|---|
| `run-X.jsonl`, `run-Y.jsonl`, `run-Z.jsonl` | the agent's event stream for each published run: plan, delegations, every tool call and result preview, the gate's verdicts, the brief, the totals |
| `console-X.log`, `console-Y.log`, `console-Z.log` | the sandbox console for the same runs: OpenShell commands and the gateway's log, every `NET:OPEN` and `HTTP:POST` decision |
| `briefs/brief-*.md` | the three briefs as the runner accepted them |
| `brief-verify-2026-10-05.log` | `scripts/verify.py` on each brief: structure, grounding, every cited id resolved in the database as the patient's own user |
| `rls-verify-2026-10-05.log` | `scripts/verify.py --rls-only`: 14 checks on row-level security, write refusal and the synthetic-only constraints |
| `safety-probe-2026-10-05.log` | `scripts/safety_probe.sh`: 7 probes from inside a sandbox, with the gateway's decisions |

Runs: OpenShell 0.1.2 (Docker driver), langchain-oci 0.3.2, deepagents 0.7.21,
python-oracledb 3.4.2, Oracle AI Database 26ai (Always Free),
`openai.gpt-5.5` and `google.gemini-2.5-flash` on OCI Generative AI, 2026-10-05.
