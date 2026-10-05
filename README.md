# Deep Agents on your own data

A LangChain Deep Agent, built with the open-source
[`langchain-oracle`](https://github.com/oracle/langchain-oracle) packages,
writes a pre-visit clinical brief from **Oracle AI Database 26ai**, inside an
**NVIDIA OpenShell** sandbox. A clinician picks a patient in the web app (or
Codex runs the spec); the agent plans, hands the work to three specialists,
queries the relational chart with SQL, searches notes, guidelines and PubMed
abstracts whose embeddings are computed inside the database, and returns a
brief in which every claim cites a row, a note or a source that exists.

Then it acts, within limits: a care coordinator agent proposes lab requests, a
message to the patient and a follow-up visit; the clinician approves or
rejects each one in the web application; the database executes what was
approved and audits every step. The agent remembers each patient across runs,
in Oracle, and every step of every run is checkpointed there.

Every patient is **synthetic**. The schema rejects anything else.

![Architecture](docs/figures/figure1-architecture.png)

## What makes it safe

Four layers, each measured, none of which asks the agent to behave
([Figure 4](docs/figures/figure4-safety-net.png)):

| Layer | What it enforces | Measured |
|---|---|---|
| OpenShell sandbox | egress to OCI Generative AI (`/openai/v1/**`) and the database listener, for `python3.12` only; the GenAI key is a placeholder the proxy swaps in transit | [`safety_probe.sh`](scripts/safety_probe.sh): 7/7 ([log](evidence/safety-probe-2026-10-05.log)) |
| Oracle AI Database | each agent user has `SELECT` only; a Virtual Private Database policy shows it one patient; `CHECK` constraints reject non-synthetic rows | [`verify.py --rls-only`](scripts/verify.py): 19/19 ([log](evidence/rls-verify-2026-10-05.log)) |
| Input guard | `PIIMiddleware` blocks SSN, phone, email, MRN, date-of-birth shapes and any other patient's id | [`agent/guards.py`](agent/guards.py) |
| Brief gate | the runner accepts a brief only with every section, enough citations of every kind, and every cited id found in the database as the patient's own user | [`agent/verify.py`](agent/verify.py), [Figure 7](docs/figures/figure7-grounding-gate.png) |

The gate earned its place on a real run: the lead cited `MEDQUAD-00001` for a
heart-failure fact that no search had returned. The runner sent the draft
back; the clinician never saw it.

## From brief to action

![Workflow](docs/figures/figure8-workflow.png)

| Step | Identity | Power |
|---|---|---|
| Propose | `DA_AGENT_<P>`, inside the sandbox | `INSERT` into `care_action` only; a trigger forces `proposed` and stamps the proposer; row-level security (`update_check`) refuses any other patient; at most five per run |
| Approve | `DA_CLINICIAN`, the web application | `EXECUTE` on `DECIDE_CARE_ACTION`, `SELECT` on the workflow tables; no table writes of its own |
| Execute | `DECIDE_CARE_ACTION` (definer rights) | creates the `lab_order`, queues the `patient_message` (a simulated portal outbox), or requests the `appointment`; one transaction; `care_action_event` keeps the audit trail |

## Memory and checkpoints on Oracle

![Memory](docs/figures/figure9-memory.png)

Following the persistence pattern in langchain-oracle's Deep Agents guide,
`create_deepagents_agent` gets `checkpointer=OracleSaver`,
`store=OracleStore` (IVF vector index over the in-database embeddings) and a
`StoreBackend` that mounts `/memories/` on that store, with
`memory=["/memories/patient-history.md"]` loaded into the system prompt.
Both live in the agent user's own schema. The agent reads its memory and
cannot write it (`permissions=`): the runner records each accepted brief and
the web application records each clinician decision, so the next brief knows
what was approved, executed, or rejected.

## Watch the agents work

The web application shows the work as it happens: the plan, each specialist's
SQL, searches and proposals, the reasoning the models share, and the full
**Agent trace** (every delegation, tool call with arguments and result, the
gate's verdicts). The **sandbox console** interleaves each agent's steps,
written from inside the sandbox, with the gateway's own network decisions, so
a SQL query sits next to the `NET:OPEN … :1521` it caused and a model call next
to its `HTTP:POST … /openai/v1/chat/completions`. Every panel goes full screen.

## Results

Four runs inside the sandbox, driven through the web application's API ([flow](evidence/flow.jsonl), [event logs and consoles](evidence/runs/), [briefs](evidence/briefs/)):

| Run | Memory loaded | Seconds | Tool calls | SQL | Searches | Actions proposed | Citations | Checkpoints | Gate | Denied |
|---|---|---|---|---|---|---|---|---|---|---|
| Patient X · first brief | 0 entries | 303 | 50 | 10 | 22 | 3 | 140 | 154 | passed | 0 |
| Patient Y · first brief | 0 entries | 238 | 38 | 3 | 20 | 3 | 155 | 130 | passed | 0 |
| Patient Z · first brief | 0 entries | 250 | 36 | 9 | 9 | 3 | 146 | 128 | passed | 0 |
| Patient Y · second brief, with memory | 4 entries | 227 | 32 | 3 | 13 | 3 | 168 | 115 | passed | 0 |

Between the first and second rounds the clinician approved the lab requests and follow-ups, approved two patient messages and rejected Y's; the database executed what was approved. Y's second brief, from memory, did not re-order the executed basic metabolic panel, asked for a BNP instead, escalated the follow-up beyond the one already requested, and drafted a different message. `scripts/verify.py` resolved every cited id again afterwards ([log](evidence/brief-verify-2026-10-05.log)); `--rls-only` passed 19/19 ([log](evidence/rls-verify-2026-10-05.log)).

| | |
|---|---|
| ![Patient](docs/screenshots/01-patient.png) | ![Agents at work](docs/screenshots/02-agents-at-work.png) |
| ![Brief](docs/screenshots/03-brief.png) | ![Actions](docs/screenshots/04-actions.png) |
| ![Memory](docs/screenshots/05-memory.png) | ![Trace](docs/screenshots/06-inspect-trace.png) |

## How it is built

| Piece | With |
|---|---|
| Deep Agent | `langchain_oci.create_deepagents_agent` (deepagents 0.7): a lead that plans with `write_todos`, delegates with `task`, and returns a structured `PreVisitBrief`; specialists `chart-analyst`, `guideline-researcher`, `evidence-researcher`, `care-coordinator`; `checkpointer=OracleSaver`, `store=OracleStore`, `backend=StoreBackend`, `memory=`, `permissions=` ([Figure 2](docs/figures/figure2-deep-agent.png)) |
| Retrieval | `langchain_oci.datastores.ADB` over `langchain_oracledb.OracleVS` tables; hybrid search (vector + Oracle Text); one store per specialist |
| Embeddings | `langchain_oracledb.OracleEmbeddings` with an ONNX all-MiniLM-L12-v2 model loaded into the database |
| Agent-to-SQL | read-only `query_chart` over SQLAlchemy's `oracle+oracledb` dialect; the database's row-level security decides the rows |
| Schema | Alembic migrations 0001-0006: clinical tables, vector tables, cohort benchmark, row-level security, citable note ids, care-action workflow ([Figure 3](docs/figures/figure3-data.png)) |
| Notes → vectors | `langchain_oracledb.OracleAutonomousDatabaseLoader` + `OracleTextSplitter`, in the database |
| Models | OCI Generative AI, OpenAI-compatible endpoint: `openai.gpt-5.5` leads, `google.gemini-2.5-flash` specialists |
| Sandbox | NVIDIA OpenShell 0.1.2, Docker driver, provider `deepagents-genai` |
| Web app | FastAPI (`ui/`) streaming the agent's events and the sandbox console over SSE; React + Tailwind (`web/`) |

## Run it with Codex

The specification [`codex/SPEC.md`](codex/SPEC.md) is written for a coding
agent; [`codex/PROMPT.md`](codex/PROMPT.md) drives it
([Figure 6](docs/figures/figure6-codex.png)). With Docker and an OpenShell
gateway running, and Codex signed in:

```shell
git clone https://github.com/fede-kamel/deep-agents-oracle-ai-database
cd deep-agents-oracle-ai-database
codex -c sandbox_workspace_write.network_access=true \
  --add-dir ~/.config/openshell --add-dir ~/.config/deepagents-oracle-health \
  "$(cat codex/PROMPT.md)"
```

Codex runs the preflight, hands you the two steps that involve a secret (the
database ADMIN password and the OCI Generative AI key, both typed with
`read -rs` in your own terminal), then migrates, seeds, embeds, probes the
sandbox, runs all three briefs, verifies them, and reports.

## Run it by hand

```shell
uv sync
docker build -t deepagents-oracle-health:0.1 sandbox/
cp config.example.json ~/.config/deepagents-oracle-health/config.json   # set the DSN and host
scripts/operator/db-admin.sh          # your terminal: ADMIN password, not echoed
scripts/operator/genai-provider.sh    # your terminal: GenAI key, into the gateway
scripts/setup-data.sh </dev/null      # Alembic, synthetic rows, in-database embeddings
scripts/preflight.sh </dev/null
scripts/safety_probe.sh </dev/null
scripts/sandbox.sh run X </dev/null > out/run-X.jsonl
```

The web app:

```shell
(cd web && npm ci && npm run build)
uv run uvicorn ui.server:app --host 127.0.0.1 --port 8765   # open http://127.0.0.1:8765
```

## Field notes

| Where | What we found |
|---|---|
| python-oracledb 26.x thin | `OracleEmbeddings` fails building `VECTOR_ARRAY_T` (`DPY-3013`). Pin `oracledb<4`. |
| langchain-oci 0.3.2 | the ADB datastore imports `DistanceStrategy` from `langchain-community`; `search` routes by meaning across every store and takes no store argument, so give each specialist its own tool set. |
| Gemini on the OpenAI-compatible endpoint | rejects `exclusiveMinimum` in tool schemas, and tool results must be JSON objects ([`GeminiChatOpenAI`](agent/brief_agent.py)). |
| deepagents 0.7 | the base stack has no to-do list; add `TodoListMiddleware` for a visible plan. |
| Middleware and recursion | each middleware adds graph nodes; eleven PII guards left six model turns under the recursion limit. Merge them. |
| OpenShell 0.1.2 | the first settings poll, about 10 s after start, closes open connections ([NVIDIA/OpenShell#3994](https://github.com/NVIDIA/OpenShell/issues/3994)); the run script waits for it. The Autonomous Database TLS listener needs `protocol: tcp` with `tls: skip`. |
| GPT-6 with an API key | Chat Completions refuses tools while reasoning is on, and `/openai/v1/responses` returned 404 for our key, so GPT-5.5 leads. |
| Ids from memory | a lead model will cite plausible ids it never retrieved, and an analyst reading notes over SQL numbered them itself. Give every row the id its vector carries (Alembic 0005, `note_ref`) and check every id against the database before accepting. |

## Layout

| Path | Purpose |
|---|---|
| `agent/` | prompts, SQL tools, guards, `PreVisitBrief`, verifier, runner |
| `migrations/` | Alembic: schema, vectors, benchmark, row-level security |
| `db/` | ADMIN setup (operator), seed, in-database embedding |
| `data/` | synthetic patients X, Y, Z; background cohort; public reference loaders |
| `sandbox/` | image, provider profile, sandbox policy |
| `scripts/` | preflight, setup, sandbox run, safety probe, verify, teardown, operator steps |
| `ui/`, `web/` | the web application |
| `docs/figures/` | seven figures, generated by `docs/figures-src/gen.py` |
| `evidence/` | event logs, consoles, briefs, probe and verify transcripts |
| `codex/` | the specification and the prompt |

---

Personal open-source work, built and tested with personal resources and
synthetic data only; not an Oracle publication or a statement of Oracle's
plans. The briefs are a demonstration, not medical advice.
