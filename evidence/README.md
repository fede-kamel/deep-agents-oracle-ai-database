# Evidence

Every number in the README and the deck comes from a file in this folder.
Identifiers that would locate the database (its service name) or any account
never appear; the database host is Oracle's public regional endpoint.

| File | What it is |
|---|---|
| `flow.jsonl` | one line per run of `scripts/demo_e2e.py --evidence evidence` (DEMO E2E OK, 41/41): metrics, the CP-03 refusal, the escalation, and what happened to the medication change |
| `runs/run-<P>-<first\|second>.jsonl` | the agent's event stream for each run: plan, delegations, every tool call and result preview, policy refusals, escalations, the gate's verdicts, the brief, the totals |
| `runs/console-<P>-<first\|second>.log` | the sandbox console for the same runs: each agent's steps from inside the sandbox, OpenShell commands, and the gateway's `NET:OPEN` and `HTTP:POST` decisions |
| `briefs/brief-*.md` | the four briefs as the runner accepted them |
| `brief-verify-2026-10-05.log` | `scripts/verify.py` on each brief: structure, grounding, every cited id resolved in the database as the patient's own user |
| `rls-verify-2026-10-05.log` | `scripts/verify.py --rls-only`: 25 checks on row-level security, write refusal, the care-action workflow, policies CP-02 and CP-03, and the synthetic-only constraints |
| `safety-probe-2026-10-05.log` | `scripts/safety_probe.sh`: 7 probes from inside a sandbox, with the gateway's decisions |
| `codex/codex-run1..4-*` | four recorded Codex runs of `codex/SPEC.md`: one stopped on the database ACL, two full passes on the first version, one on the current code |

Runs: OpenShell 0.1.2 (Docker driver), langchain-oci 0.3.2, deepagents 0.7.21,
python-oracledb 3.4.2, Oracle AI Database 26ai (Always Free),
`openai.gpt-5.5` and `google.gemini-2.5-flash` on OCI Generative AI, 2026-10-05.
