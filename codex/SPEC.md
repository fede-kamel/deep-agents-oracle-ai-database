# Specification: Deep Agents on your own data, safely

Version 1, 2026-10-05. Written for an AI coding agent (OpenAI Codex) that
executes in the operator's environment, and complete enough for a person to
follow by hand. The prompt that drives an agent through it is
[`PROMPT.md`](PROMPT.md). Where this file and a script differ, the script
wins, and the difference is a bug to report.

## 0. What is being built, and what "done" means

A LangChain Deep Agent, built with the open-source `langchain-oracle`
packages, prepares a pre-visit clinical brief for one of three **synthetic**
patients. Their charts live in Oracle AI Database 26ai as relational rows
(Alembic migrations) and as vector stores whose embeddings are computed inside
the database. The agent runs inside an NVIDIA OpenShell sandbox; the operator
starts it from this conversation or from the web application, and watches the
sandbox console live.

Done means all of the following are true:

1. `scripts/preflight.sh </dev/null` ends with `PREFLIGHT OK`.
2. `scripts/safety_probe.sh </dev/null` ends with `PROBE OK (7/7)`.
3. For each patient X, Y and Z, `scripts/sandbox.sh run <P> </dev/null` exits 0,
   its last `verify` event says `"passed": true`, and
   `uv run python scripts/verify.py <brief>` ends with `VERIFY OK`.
4. `uv run python scripts/verify.py --rls-only` ends with `VERIFY OK (19/19)`:
   row-level security, write refusal, synthetic-only constraints, and the care
   action workflow (an agent proposes for its own patient only, cannot approve
   or execute; the clinician's approval executes and is audited).
5. `scripts/webapp-check.sh Y </dev/null` ends with `WEBAPP OK (7/7)`: the web
   application builds, serves, and runs a verified brief through its API with
   both stream channels (agent events and the sandbox console).
6. Post-conditions hold (section 5.2), and the operator has the report in section 9.

Out of scope: real patient data of any kind, production hardening, and
clusters other than a local OpenShell gateway with the Docker driver.

## 1. Inputs the operator supplies

| Input | Needed when | How the agent gets it |
|---|---|---|
| An Oracle Autonomous Database 26ai (an Always Free one works) with TLS (no wallet) and an ACL that admits this machine | always | ask for its TLS connect string (DSN) and host; write them to the config file (section 4.2) |
| The ADMIN password | once, for section 4.3 | **never through the agent**: the operator runs `scripts/operator/db-admin.sh` in their own terminal |
| An OCI Generative AI API key, region `us-chicago-1` | once, for section 4.4 | **never through the agent**: the operator runs `scripts/operator/genai-provider.sh` in their own terminal |
| Chat models | optional | defaults `google.gemini-2.5-pro` (lead) and `google.gemini-2.5-flash` (specialists) |

The secret rule. The agent never asks for, receives, prints, logs, or stores
a password or a key. The two operator scripts read them with `read -rs`. The
database passwords they generate go into owner-only files
(`~/.config/deepagents-oracle-health/secrets/`, directory 0700, files 0600);
scripts read them by name and never print them. The GenAI key goes into the
OpenShell gateway; sandboxes see a placeholder. When you hand the operator one
of these steps, tell them to reply `done` and not to paste the output.

The data rule. Every patient is invented. The schema enforces it
(`CHECK (is_synthetic = 'Y')`, `CHECK (patient_id LIKE 'SYN-%')`), and the
agent's input guard blocks real-looking identifiers. Never add, import, or
paste real patient data, and stop if asked to.

## 2. Prerequisites and preflight

| Requirement | Check | Passes when | If it fails |
|---|---|---|---|
| macOS on Apple Silicon or Linux | `uname -sm` | `Darwin arm64`, `Linux x86_64`, `Linux aarch64` | ask |
| uv | `uv --version` | prints a version | fix: install uv |
| Docker visible to Codex | `docker info --format '{{.ServerVersion}}'` (Rancher Desktop: `~/.rd/bin/docker`) | prints a version | ask the operator to start Docker |
| OpenShell CLI 0.1.2 and a connected gateway | `openshell status </dev/null` | `Status: Connected`, `Version: 0.1.2` | ask: install OpenShell and start the gateway |
| Node 20+ | `node --version` | v20 or later | fix: install Node |

`scripts/preflight.sh` runs these and the data checks in one pass; it changes
nothing. Show the operator its table before continuing.

## 3. Architecture

| Piece | Name | Defined in |
|---|---|---|
| Schema owner | `DA_OWNER` (tables, model, policies) | `db/setup_admin.py` |
| Agent users | `DA_AGENT_X`, `DA_AGENT_Y`, `DA_AGENT_Z`: SELECT on the chart, INSERT on `care_action` (proposals), and their own schema for checkpoints and memory (64 MB quota) | `db/setup_admin.py`, migrations 0004-0006 |
| Clinician | `DA_CLINICIAN`: EXECUTE on `DECIDE_CARE_ACTION`, SELECT on the workflow tables; used by the web app to approve or reject | `db/setup_admin.py`, migration 0006 |
| Care actions | `care_action` (proposed/approved/executed/rejected), `care_action_event` (audit), `lab_order`, `patient_message` (simulated portal outbox), `appointment` requests | migration 0006 |
| Agent state | `OracleSaver` checkpoints and `OracleStore` memory (IVF vector index) in each agent user's schema; `/memories/patient-history.md` via `StoreBackend` | `agent/memory.py` |
| Clinical schema | `patient`, `condition`, `allergy`, `medication`, `encounter`, `clinical_note`, `lab_result`, `vital_sign`, `referral`, `appointment` | migration 0001 |
| Vector stores | `PATIENT_NOTE_VEC`, `CLINICAL_REFERENCE` (MedQuAD), `RESEARCH_EVIDENCE` (PubMedQA), shaped like `OracleVS` tables | migration 0002 |
| Cohort benchmark | `cohort_benchmark`: aggregates of 300 background synthetic patients, no ids | migration 0003, `db/seed.py` |
| Row-level security | Virtual Private Database policy `DA_PATIENT_SCOPE` on every patient table and the note vectors | migrations 0004-0005 |
| Embedding model | `DA_OWNER.MINILM_L12` (all-MiniLM-L12-v2 ONNX, 384 dimensions) | `db/setup_admin.py` |
| Deep Agent | `langchain_oci.create_deepagents_agent`: lead + `chart-analyst`, `guideline-researcher`, `evidence-researcher`, `care-coordinator`; structured `PreVisitBrief` output; `checkpointer`, `store`, `backend`, `memory`, `permissions` from langgraph-oracledb and deepagents | `agent/brief_agent.py` |
| Sandbox image | `deepagents-oracle-health:0.1` | `sandbox/Dockerfile` |
| Provider | `deepagents-genai`, type `oci-genai-python` | `sandbox/profile/oci-genai-python.yaml` |
| Sandbox policy | provider endpoint (OCI GenAI `/openai/v1/**`) plus `oracle_ai_database` (TCP to the listener) for `/usr/local/bin/python3.12` only | `sandbox/policy.template.yaml` |
| Sandboxes | `brief-<x|y|z>-HHMMSS` (one per run), `probe-HHMMSS` | `scripts/sandbox.sh`, `scripts/safety_probe.sh` |

What the sandbox holds, and why each is safe: the GenAI key is a placeholder;
the database login is one patient's read-only user, uploaded as a 0600 file
and deleted after the agent reads it; the only egress is the two endpoints
above, for one binary.

## 4. Build steps

Run every command from the repository root, in the foreground, with
`</dev/null`. Each step has a checkpoint; do not continue past a failed one
without resolving it (section 7).

### 4.1 Python and the sandbox image

```shell
uv sync
docker build -t deepagents-oracle-health:0.1 sandbox/
```

Checkpoint: `docker image inspect deepagents-oracle-health:0.1` succeeds.

### 4.2 Config file

Write `~/.config/deepagents-oracle-health/config.json` (mode 0600) from
`config.example.json` with the operator's DSN and host. It holds no secret.

Checkpoint: `python3 -m json.tool ~/.config/deepagents-oracle-health/config.json` succeeds.

### 4.3 Database users and model (operator step)

Hand the operator: `scripts/operator/db-admin.sh` in their own terminal. It
asks for the ADMIN password without echoing it, creates or updates the four
demo users and `DA_CLINICIAN`, and rotates their passwords. Wait for `done`.
Re-run it after pulling a version that changes grants.

Checkpoint: `scripts/preflight.sh` shows the four `secret ... present` lines as PASS.

### 4.4 GenAI provider (operator step)

Hand the operator: create the IAM policy first, then the key (the profile's
header explains the order), then `scripts/operator/genai-provider.sh` in their
own terminal. Wait for `done`. If `openshell provider get deepagents-genai`
already succeeds, skip this step.

Checkpoint: `openshell provider get deepagents-genai </dev/null` succeeds.

### 4.5 Data layer

```shell
scripts/setup-data.sh </dev/null
```

Migrations, the synthetic rows, then in-database chunking and embedding.
About four minutes on an Always Free database.

Checkpoint: ends with `SETUP-DATA OK`; `uv run alembic current` shows `0006 (head)`.

To start the workflow from a clean slate (no care actions, no memory):
`uv run python db/reset_workflow.py`.

### 4.6 Preflight and the safety probe

```shell
scripts/preflight.sh </dev/null
scripts/safety_probe.sh </dev/null
```

Checkpoint: `PREFLIGHT OK`, then `PROBE OK (7/7)`.

### 4.7 Briefs

```shell
scripts/sandbox.sh run X </dev/null > out/run-X.jsonl
uv run python scripts/verify.py out/runs/... # or extract the brief event, see below
```

stdout carries JSON events; stderr carries the sandbox console. The `brief`
event holds the Markdown; save it to `out/brief-<P>.md` and verify it. Repeat
for Y and Z. One run takes two to five minutes.

Checkpoint: each run exits 0 with a passing final `verify` event, and
`scripts/verify.py out/brief-<P>.md` ends with `VERIFY OK`.

### 4.8 The web application

```shell
scripts/webapp-check.sh Y </dev/null
```

Builds `web/` (React + Tailwind), starts `ui/server.py` on port 8766, and
drives one brief through the API exactly as the browser does: the patient
cards (each read through its own database user), `POST /api/runs`, the
Server-Sent Events stream to the end, and the Word export. The backend runs the
same `scripts/sandbox.sh`, so the run is a real sandboxed run. The script stops
the server it started.

Checkpoint: ends with `WEBAPP OK (7/7)`.

To leave the application running for the operator afterwards:

```shell
uv run uvicorn ui.server:app --host 127.0.0.1 --port 8765   # then open http://127.0.0.1:8765
```

Tell the operator the URL; do not run it in the foreground of your own session.

## 5. Acceptance

### 5.1 The checks

The five conditions in section 0.

### 5.2 Post-conditions

- `openshell sandbox list` shows no `brief-*` or `probe-*` sandbox.
- No password or key appears in any output, log, or in this conversation.
- No file under the repository contains a DSN service name, OCID, or key.

## 6. Rules for the agent

- Never handle a secret (section 1). Anything that looks like a key or a
  password in an output is a stop condition, not something to repeat.
- Never touch database objects the demo did not create, gateway resources
  other than `deepagents-genai` and the demo's sandboxes, or other Docker
  containers. Do not run `setup_admin.py` yourself: it needs ADMIN.
- Do not edit `agent/`, `db/`, `migrations/`, `sandbox/` or `scripts/` to make
  a check pass. If a change seems necessary, explain why and stop.
- Every `openshell sandbox exec` needs `</dev/null` (0.1.2 reads piped stdin to EOF).
- One sandbox run at a time.

## 7. Known behaviour and troubleshooting

| Symptom | Cause | Action |
|---|---|---|
| `DPY-6005 ... [Errno 13] Permission denied` right after a sandbox starts | OpenShell 0.1.2: the first settings poll (~10 s) bumps the policy generation and closes open connections (NVIDIA/OpenShell#3994) | `scripts/sandbox.sh` waits for the reload; if you see this, re-run |
| `DPY-6000 ... ORA-12506` | the database ACL does not admit this machine's egress IP | ask the operator to add it |
| `DPY-3013: unsupported Python type str for database type DB_TYPE_CLOB` | python-oracledb 4.x/26.x thin mode with `OracleEmbeddings` | keep `oracledb<4` |
| HTTP 400 `Unknown name "exclusiveMinimum"` or `function_response.response` | Gemini on the OpenAI-compatible endpoint | handled by `GeminiChatOpenAI`; do not swap the class |
| `verify` event with problems, then a repair turn | the runner sent the draft back | expected; it retries twice |
| HTTP 401 from OCI GenAI | the key was minted before its policy | mint a new key after the policy (operator) |
| `Refused: 5 actions already proposed in this run` in a tool result | the care coordinator hit its cap | expected; the brief lists what it proposed |
| `ORA-28115` when a tool proposes an action | row-level security refused a proposal for another patient | expected; that is the boundary |
| `PermissionError` on the Hugging Face cache during setup | a sandboxed coding agent cannot write `~/.cache` | `setup-data.sh` sets `HF_HOME` inside the repository; keep it |

## 8. Teardown

```shell
scripts/teardown.sh </dev/null          # leftover sandboxes
scripts/teardown.sh --data </dev/null   # also drop the demo tables
```

The operator removes the users and model with `scripts/operator/db-admin.sh
--drop` and the provider with `openshell provider delete deepagents-genai`.

## 9. Report

End with: the preflight table; the probe table; the web application check; for each patient the run's
seconds, tool calls, SQL queries, searches, delegations, citation count, and
the verify result; the row-level-security result; any section-7 symptom met
and what was done; the care actions each run proposed; and confirmation of section 5.2.
