# Specification: the sample Deep Agent, built and run

Written for a coding agent (OpenAI Codex) and followable by hand. Each step has
a checkpoint; do not continue past a failed one. Obey `../AGENTS.md`.

## 0. Done means

1. `python agent.py --dry-run` ends with `DRY RUN OK`.
2. The schema exists and an agent user sees one patient (step 4 checkpoint).
3. `./run_in_sandbox.sh` ends with `BRIEF OK`.
4. `openshell sandbox list` shows no `sample-*` sandbox.

## 1. Inputs

| Input | How the agent gets it |
|---|---|
| An Oracle Autonomous Database 26ai with TLS, and its host name (or Oracle AI Database 26ai Free in a container: see the README) | ask the operator for the host name only, and for its IP if it is a private address |
| The ADMIN password | never: the operator runs `sql/01_users.sql` |
| The SAMPLE_OWNER password | never: the operator runs `sql/02_schema.sql` as SAMPLE_OWNER |
| The OCI Generative AI API key | never: the operator runs `operator/genai-provider.sh` |
| The agent's database login | never: the operator runs `operator/save-db-login.sh` |

## 2. Prerequisites

| Check | Passes when |
|---|---|
| `docker info --format '{{.ServerVersion}}'` | prints a version |
| `openshell status </dev/null` | `Status: Connected` |
| `uv --version` | prints a version |

## 3. Steps

1. **Dry run.** `uv run --with langchain-oci==0.3.2 --with langchain-openai --with deepagents==0.7.21 --with langgraph-oracledb==1.0.1 --with oracledb python agent.py --dry-run </dev/null`.
   Checkpoint: `DRY RUN OK`.
2. **Image.** `docker build -t deep-agent-sample:0.1 sandbox/`.
   Checkpoint: `docker image inspect deep-agent-sample:0.1` succeeds.
3. **Users (operator).** Hand the operator `sql admin@<connect string> @sql/01_users.sql`. Wait for `done`.
4. **Schema (operator).** Hand the operator `sql sample_owner@<connect string> @sql/02_schema.sql`. Wait for `done`.
5. **Provider and login (operator).** Hand the operator `operator/genai-provider.sh`, then
   `operator/save-db-login.sh`. Wait for `done` after each.
   Checkpoint: `openshell provider get sample-genai </dev/null` succeeds, and
   `test -f ~/.config/deep-agent-sample/db.env` succeeds (do not read the file).
6. **Run.** `SAMPLE_DB_HOST=<host> ./run_in_sandbox.sh </dev/null`.
   Checkpoint: ends with `BRIEF OK`; the output shows a medication change refused for
   `care-coordinator` and proposed by `medication-safety`.

## 4. Known behaviour

| Symptom | Cause | Action |
|---|---|---|
| `ORA-20014: policy: the care-coordinator agent may not propose ...` | the agent policy | expected; the lead delegates to medication-safety |
| `BRIEF REJECTED` with missing ids | the model cited an id no tool returned | expected once; the run repairs once; re-run if it persists |
| `DPY-6000 ... ORA-12506` | the database access list does not admit this machine | ask the operator to add it |
| `Permission denied` right after start | OpenShell 0.1.2 first settings poll | the script waits for it; re-run |
| `must use a DNS hostname, not an IP literal` | the policy names the database by IP | ask the operator for a DNS name (for a local container, `<ip-with-dashes>.sslip.io`) |
| `DPY-6005 ... [Errno 13] Permission denied` on every run, for a database on a private address | OpenShell refuses private addresses unless allowed by IP | re-run with `SAMPLE_DB_ALLOWED_IP=<the database's IP>` |
| `socket.gaierror ... Name or service not known` for a `*.sslip.io` host | the local resolver refuses private-address answers | tell the operator; a different network or an Autonomous Database |
| `ORA-41900: missing ... privilege` | an agent tried to update or delete | expected; agents only read and propose |
| `No such image: sha256:...` when the sandbox starts | the container engine restarted under a running gateway | ask the operator to restart the OpenShell gateway |
| `ORA-01031` on `GRANT EXECUTE ON DBMS_RLS` | Oracle Database Free, connected as `SYSTEM` | ask the operator to run step 3 as `SYS AS SYSDBA` in the pluggable database |

## 5. Report

The checkpoint of each step, the brief's last three lines, and confirmation of
section 0 item 4. Never include a password, key, or connect string.
