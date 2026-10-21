# Sample: a Deep Agent on Oracle AI Database, in an OpenShell sandbox

The pattern of the write-up in about 200 lines of Python and 150 of SQL.
A lead plans and delegates to three specialists; the database decides what each
may see and propose; OpenShell decides where anything can go; a gate checks
every cited id. Synthetic data only.

| File | What it is |
|---|---|
| `agent.py` | the agent: tools, gate, `create_deepagents_agent`, Oracle checkpoints |
| `sql/01_users.sql` | operator, as ADMIN: the schema owner and the agent user |
| `sql/02_schema.sql` | the chart, care actions, the agent policy, row-level security, two synthetic patients |
| `sandbox/` | the image, the sandbox policy, the OCI Generative AI provider profile |
| `operator/` | the two scripts that read a secret, run by a person |
| `run_in_sandbox.sh` | one run in a fresh sandbox, deleted afterwards |
| `AGENTS.md`, `codex/` | the harness: rules, specification, prompt |

## With Codex

```shell
codex -s workspace-write -c sandbox_workspace_write.network_access=true \
  --add-dir ~/.config/openshell --add-dir ~/.config/deep-agent-sample \
  "$(cat codex/PROMPT.md)"
```

## By hand

```shell
uv run --with langchain-oci==0.3.2 --with langchain-openai --with deepagents==0.7.21 \
  --with langgraph-oracledb==1.0.1 --with oracledb python agent.py --dry-run
docker build -t deep-agent-sample:0.1 sandbox/
sql admin@<connect string> @sql/01_users.sql               # your terminal
sql sample_owner@<connect string> @sql/02_schema.sql       # your terminal
operator/genai-provider.sh                                 # your terminal
operator/save-db-login.sh                                  # your terminal
SAMPLE_DB_HOST=<database host> ./run_in_sandbox.sh
```

Status: built and run end to end on 2026-10-20 against Oracle AI Database 26ai
Free (23.26.3), with OpenShell 0.1.2 and `openai.gpt-5.5`: the rules check passed
9 of 9, and two sandbox runs ended `BRIEF OK` with the medication change refused
for the care coordinator and proposed by the medication-safety agent. The
transcripts are in `../evidence/sample/`.

## No Autonomous Database? Run one locally

Oracle AI Database 26ai Free runs in a container. This is how the sample was
tested. On Free, `SYS AS SYSDBA` in the pluggable database stands in for ADMIN
(`SYSTEM` cannot grant `DBMS_RLS`), and the lite image's pluggable database
needs a `USERS` tablespace first:

```shell
read -rs ORACLE_PWD && export ORACLE_PWD        # the database's SYS password, unechoed
docker run -d --name sample-oracle-free -p 1521:1521 -e ORACLE_PWD \
  container-registry.oracle.com/database/free:latest-lite
docker logs -f sample-oracle-free                # wait for DATABASE IS READY TO USE!
sql "sys@localhost:1521/FREEPDB1 as sysdba"      # then, at the SQL prompt:
#   CREATE TABLESPACE users DATAFILE '/opt/oracle/oradata/FREE/FREEPDB1/users01.dbf' SIZE 200M AUTOEXTEND ON;
#   @sql/01_users.sql
sql sample_owner@localhost:1521/FREEPDB1 @sql/02_schema.sql
IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' sample-oracle-free)
operator/save-db-login.sh                        # DSN: ${IP//./-}.sslip.io:1521/FREEPDB1
SAMPLE_DB_HOST=${IP//./-}.sslip.io SAMPLE_DB_ALLOWED_IP=$IP ./run_in_sandbox.sh
```

OpenShell accepts only DNS names in a policy, and refuses private addresses
unless the policy also allows them by IP; `SAMPLE_DB_ALLOWED_IP` adds that one
address. Some home routers refuse to resolve a public name to a private
address (DNS rebinding protection): if the run fails with `Name or service not
known`, use a network or resolver that allows it, or an Autonomous Database. The SQL scripts prompt for passwords, so run them at a terminal: a
piped prompt reads the whole input as the first password.

To remove it: `DROP USER sample_agent_a CASCADE; DROP USER sample_owner CASCADE;`
as ADMIN (or `docker rm -f sample-oracle-free`), `openshell provider delete sample-genai`, and delete `~/.config/deep-agent-sample`.
