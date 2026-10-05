# Agent instructions

This repository is a runnable demo: a LangChain Deep Agent, built with
`langchain-oracle`, writes a pre-visit clinical brief for a synthetic patient
from Oracle AI Database 26ai, inside an NVIDIA OpenShell sandbox. The
specification for building and running it is `codex/SPEC.md`; the prompt that
drives an agent through it is `codex/PROMPT.md`. Read the specification before
running anything.

## Hard rules

- Secrets. Never ask for, echo, log, or store a password or an API key. The
  operator runs `scripts/operator/*.sh` in their own terminal for the two steps
  that need one. Anything that looks like a key or a password in an output is
  a stop condition. The placeholder `openshell:resolve:env:…` is not a secret.
- Synthetic data only. Never add, import, or paste real patient data. The
  schema rejects patient ids without the `SYN-` prefix; do not work around it.
- Scope. Touch only what the demo created: the `DA_*` users and their objects,
  the `deepagents-genai` provider, `brief-*` and `probe-*` sandboxes, and the
  `deepagents-oracle-health` image. Never run `db/setup_admin.py` (ADMIN).
- Care actions. Never approve or reject a care action yourself; that is the
  clinician's or the doctor's decision in the web application (only
  `scripts/demo_e2e.py` decides, and only when the operator runs it). You may run `db/reset_workflow.py`
  only when the operator asks for a clean slate.
- Integrity. Do not modify `agent/`, `db/`, `migrations/`, `sandbox/` or
  `scripts/` to make a check pass. Explain and stop instead.
- Scripts run from the repository root, in the foreground, with `</dev/null`.
  Every `openshell sandbox exec` needs `</dev/null` on OpenShell 0.1.2.

## Where things are

| Path | Purpose |
|---|---|
| `agent/` | the Deep Agent: prompts, SQL and care-action tools, guards, memory, structured brief, runner |
| `migrations/` | Alembic: clinical schema, vector tables, cohort benchmark, row-level security, citable note ids, care actions, care and agent policies |
| `db/` | ADMIN setup (operator), seed, in-database embedding, stats |
| `data/` | synthetic patients X, Y, Z; background cohort; public reference corpus loaders |
| `sandbox/` | image, provider profile, sandbox policy |
| `scripts/` | `preflight.sh`, `setup-data.sh`, `sandbox.sh`, `safety_probe.sh`, `verify.py`, `teardown.sh`, `operator/` |
| `ui/`, `web/` | the web application: FastAPI backend, React front end |
| `evidence/` | transcripts behind every claim, identifiers redacted |
| `codex/` | the specification and the prompt |

## Verifying

- `scripts/preflight.sh </dev/null` ends with `PREFLIGHT OK`.
- `scripts/safety_probe.sh </dev/null` ends with `PROBE OK (7/7)`.
- `scripts/sandbox.sh run X </dev/null` exits 0; its final `verify` event passes.
- `uv run python scripts/verify.py <brief>` and `--rls-only` end with `VERIFY OK` (`--rls-only`: 25/25).
- With the web app on 8765, `uv run python scripts/demo_e2e.py` ends with `DEMO E2E OK`.
- `scripts/webapp-check.sh Y </dev/null` ends with `WEBAPP OK (7/7)`.
- With the web app on 8765, `cd web && node scripts/ui-e2e.mjs Y` ends with `UI E2E OK`.

## Writing

Active voice, short sentences, commands in `shell` fences, no filler. Keep the
disclaimer that this is personal work with synthetic data. Never mention
accounts, tenancy or compartment OCIDs, DSN service names, or key values.
