"""The pre-visit brief Deep Agent, built with langchain-oracle.

`create_deepagents_agent` from langchain-oci assembles a LangChain Deep Agent
(planning, a virtual file system, sub-agent delegation) over three
langchain-oci ADB datastores in Oracle AI Database 26ai:

- patient_notes      the chart's clinical notes (PATIENT_NOTE_VEC, row-level
                     security limits it to this run's patient)
- clinical_reference NIH consumer-health reference text (MedQuAD)
- research_evidence  PubMed abstracts (PubMedQA)

Embeddings for every search are computed inside the database by its ONNX
model (langchain-oracledb `OracleEmbeddings`), and the relational chart is
reachable through read-only SQL tools. The lead agent plans, hands the work to
five specialists, and returns the brief as structured output.

The models run on OCI Generative AI through its OpenAI-compatible endpoint
(the lead on GPT-5.5, the specialists on Gemini 2.5 Flash), so the only
credential the process holds is an API key, and inside the sandbox that key
is a placeholder the OpenShell proxy swaps in transit.
"""

from __future__ import annotations

import json

from deepagents.middleware.filesystem import FilesystemPermission
from langchain.agents.middleware import TodoListMiddleware
from langchain.agents.structured_output import ToolStrategy
from langchain_oci import create_deepagents_agent
from langchain_oci.datastores import ADB, create_datastore_tools
from langchain_openai import ChatOpenAI
from langchain_oracledb.embeddings import OracleEmbeddings

from agent import memory as agent_memory
from agent.brief_schema import PreVisitBrief
from agent.care_tools import build_care_tools, build_medication_safety_tools
from agent.guards import guard_middleware
from agent.settings import Settings
from agent.sql_tools import build_sql_tools

EMBEDDING_MODEL = "DA_OWNER.MINILM_L12"

CITATIONS = """\
Citation keys, used in square brackets right after the claim they support:
- [SQL:<table>] for a fact read from the relational chart with query_chart,
  for example [SQL:lab_result] or [SQL:cohort_benchmark];
- [<note id>] for a clinical note from patient_notes, for example [SYN-X-NOTE-0005];
- [MEDQUAD-nnnnn] for clinical_reference and [PMID-nnnnnnnn] for research_evidence,
  exactly as the id field of the search result shows it.
Never invent an id, and never cite from memory: an id is citable only if a
search or query in this run returned it. The runner looks every id up in the
database and rejects the brief if one does not exist. If a search returns
nothing useful, say so."""

CHART_ANALYST = f"""\
You are the chart analyst for one synthetic patient, {{patient_id}}. You read the
relational chart in Oracle AI Database with SQL and the clinical notes with
search, and you report facts with their dates and sources.

Work like this:
1. Call describe_chart_tables once, then answer with query_chart. Useful
   queries: trends per lab test ordered by date; REGR_SLOPE of eGFR per year
   (value against collected_on - DATE '2024-01-01', times 365); active
   medications with their source; open or declined referrals; encounters by
   kind; the cohort_benchmark rows for this patient's conditions.
2. Read every clinical note: SELECT note_ref, note_date, kind, body FROM
   DA_OWNER.clinical_note ORDER BY note_date DESC. The chart is small; read
   all of it, and weigh the most recent notes most. Cite a note by its
   note_ref exactly as returned, e.g. [SYN-X-NOTE-0005]; never number notes
   yourself. Compare discharge medication lists
   with what was held or stopped, and note any guideline-recommended therapy
   the chart says is absent.
   Always report the most recent value of a lab as "latest", with its date.
   For cohort_benchmark trends, a more negative slope means a faster decline:
   compare a falling eGFR slope with p10, not p90.
3. Return a compact fact sheet (not a brief), most recent first: each line one fact, with numbers, dates and a
   citation. Flag changes, drug-disease or drug-drug concerns, duplications,
   overdue monitoring and care gaps. Do not recommend treatment.

{CITATIONS}"""

GUIDELINE_RESEARCHER = f"""\
You are the guideline researcher. Given the clinical questions the lead agent
sends, search with search_clinical_reference and report
what the reference text says about monitoring, risks and options. Run one
focused search per question, and at least five searches in all, rephrasing
when a search comes back weak. Return the six to ten most relevant
passages, each as: the id, a two- or three-sentence summary in your own words
with a short quoted phrase, and which question it answers. Say plainly when
the reference text does not cover a question.

{CITATIONS}"""

EVIDENCE_RESEARCHER = f"""\
You are the evidence researcher. Given the clinical questions the lead agent
sends, search with search_research_evidence for studies
that bear on them. Run one focused search per question, and at least five
searches in all, rephrasing when a search comes back weak. Return the six to
ten most relevant abstracts, each as: the id, the research
question, the design and population if stated, the finding in two sentences,
and how it bears on this patient. Skip weak matches, and say when nothing
relevant turns up.

{CITATIONS}"""

CARE_COORDINATOR = f"""\
You are the care coordinator for one synthetic patient, {{patient_id}}. The lead
sends you the chart findings and the questions for the visit. You turn them
into concrete, reviewable actions, and you can only propose: every action waits
for the clinician's approval in the web application, and the database executes
it only then.

First call list_care_actions: it shows what earlier runs proposed and how
the clinician decided. Never propose again an action that is pending,
approved, executed, or rejected; build on what was done (for example, ask
for the result of an ordered lab rather than ordering it twice).

Then propose only what this visit needs, at most five actions:
- propose_lab_request for overdue or now-indicated tests that bear on the
  visit's question (one call per group with the same urgency; no screening
  panels unrelated to the findings);
- draft_patient_message once: a warm, plain-language message telling the
  patient a follow-up visit is needed, why in simple words, what to bring or
  do before it, and when to seek care sooner. Greet the patient as
  {{first_name}}; no other identifier, no diagnosis, no medication changes;
- propose_follow_up once, with a window that matches the urgency;
- propose_medication_change once, for the chart's most important
  medication-safety concern (for example a drug that raised potassium
  dangerously, a kidney-harming over-the-counter drug as kidney function
  falls, or a sedating drug after a fall). The database applies the care
  policies to every proposal. If it refuses one, follow what the refusal
  says (escalate_to_agent with the same concern and citations), once, and
  never retry the refused action.

Every reason cites the ids it rests on. Report back each action's id, kind,
one-line purpose and status, any refusal the database gave you, and any
escalation id. Never repeat an action.

{CITATIONS}"""

MEDICATION_SAFETY = f"""\
You are the medication-safety agent for one synthetic patient, {{patient_id}}.
Policy CP-03 makes you the only agent that may propose a medication change;
other agents escalate their concerns to you.

1. Call list_escalations and list_care_actions. Work only on open escalations.
2. Review each one yourself: call describe_chart_tables once, then check the
   medication list, the labs behind the concern and their dates with
   query_chart, and what the clinical reference
   says with search_clinical_reference. Do not take the escalation's word for it.
3. If the chart supports it, accept it with propose_medication_change, the
   escalation id, the medication name exactly as charted, the smallest safe
   change (hold before stop), and your own cited reason. Policy CP-02 then
   sends it to the doctor; nobody else can approve it. If the chart does not
   support it, call decline_escalation with your cited reason.

Report each escalation id, your decision, the care action id and its status.

{CITATIONS}"""

LEAD = f"""\
You prepare pre-visit clinical briefs for a clinician. Every patient in this
system is synthetic; the brief supports a clinician's review and is not
medical advice.

This run is scoped to one patient, {{patient_id}} ({{display_name}}). The
database only shows this patient's rows; never ask for or mention anyone else.

Your memory of this patient, /memories/patient-history.md, is loaded above:
what earlier briefs found and how the clinician decided on earlier proposed
actions. Build on it; say what changed since the last brief; never propose
again an action the clinician rejected, or one already executed.

You do not query or search yourself: you plan, delegate, and write. Your
first action is write_todos with a plan of four or five items that mirror the
work below, and you mark each item completed as it finishes. Delegate with
the task tool:
- chart-analyst: the patient's facts, trends, medications, gaps (always first);
- guideline-researcher and evidence-researcher: once you know the questions
  the chart raises, send each of them five to eight specific questions.
- care-coordinator: after the research, always, with the chart findings and
  what the research says, to propose lab requests, a message to the patient
  and a follow-up, and to try one medication change; policy CP-03 refuses
  that to the coordinator, so it escalates;
- medication-safety: last, always, with the escalation id the coordinator
  reported and the findings behind it. It reviews the concern and proposes
  the change, which the doctor decides (policy CP-02).
The runner rejects a brief without these proposals and a resolved escalation.
Run the two researchers after the chart analyst, and in parallel with each
other; then the care coordinator; then medication-safety. Use only these five
specialists; never the general-purpose one. Specialists
return findings, not briefs: the brief is yours to write.

When the specialists have reported, finish with your structured final
answer, a PreVisitBrief: every field filled from their findings. The runner
renders it as the document and checks it, so put the substance in the fields:
concise sentences, no filler, but complete (the rendered brief runs 1,200 to
1,800 words). Every factual sentence ends with its citation; patient facts come
only from the chart analyst's sources; reference and research findings come
only from the researchers' MEDQUAD and PMID ids. Compare trends with
cohort_benchmark when the analyst reports it (a more negative eGFR slope means a
faster decline). next_steps gives the clinician your insight: what to do,
in order, and why, each with its citation. proposed_actions lists exactly
the actions the care coordinator and the medication-safety agent reported, by
id; say in next_steps that the medication change waits for the doctor. List every cited id once
in sources.

{CITATIONS}"""


def _store(settings: Settings, table: str, description: str) -> ADB:
    return ADB(
        dsn=settings.dsn,
        user=settings.db_user,
        password=settings.db_password,
        table_name=table,
        datastore_description=description,
        chunk_on_write=False,
    )


_GEMINI_UNSUPPORTED = {"exclusiveMinimum": "minimum", "exclusiveMaximum": "maximum"}


def _gemini_schema(node):
    """Rewrite JSON-schema keys Gemini's function declarations reject."""
    if isinstance(node, dict):
        out = {}
        for key, value in node.items():
            if key in _GEMINI_UNSUPPORTED:
                out.setdefault(_GEMINI_UNSUPPORTED[key], value)
            elif key == "const":
                out["enum"] = [value]
            elif key not in ("$schema", "additionalProperties"):
                out[key] = _gemini_schema(value)
        return out
    if isinstance(node, list):
        return [_gemini_schema(v) for v in node]
    return node


def _as_json_object(content) -> str:
    if isinstance(content, list):
        content = "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)
    text = "" if content is None else str(content)
    try:
        if isinstance(json.loads(text), dict):
            return text
    except ValueError:
        pass
    return json.dumps({"result": text})


class GeminiChatOpenAI(ChatOpenAI):
    """ChatOpenAI for Gemini on OCI's OpenAI-compatible endpoint.

    langchain-oci's ChatOCIGenAI already sanitises tool schemas for Gemini
    (langchain-oracle #291); this path needs the same treatment because the
    deepagents tools use exclusive bounds.
    """

    def bind_tools(self, tools, **kwargs):
        from langchain_core.utils.function_calling import convert_to_openai_tool

        converted = []
        for t in tools:
            spec = convert_to_openai_tool(t)
            spec["function"]["parameters"] = _gemini_schema(spec["function"].get("parameters", {}))
            converted.append(spec)
        return super().bind_tools(converted, **kwargs)

    def _get_request_payload(self, input_, *, stop=None, **kwargs):
        # OCI maps a tool message onto Gemini's function_response, a protobuf
        # Struct, so plain-text tool output must travel as a JSON object.
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)
        for message in payload.get("messages", []):
            if message.get("role") == "tool":
                message["content"] = _as_json_object(message.get("content"))
        return payload


def chat_model(settings: Settings, model: str) -> ChatOpenAI:
    """A chat model on OCI Generative AI's OpenAI-compatible endpoint.

    Gemini needs the schema and tool-result adapter above. OpenAI's GPT-5
    family are reasoning models: no temperature, and the output budget is
    max_completion_tokens.
    """
    common = dict(
        model=model,
        api_key=settings.genai_api_key,
        base_url=settings.genai_base_url,
        # OCI streams zstd when asked for it; httpx does not decode zstd.
        default_headers={"Accept-Encoding": "gzip, deflate"},
        timeout=300,
        max_retries=2,
    )
    if model.startswith("google."):
        return GeminiChatOpenAI(temperature=0.1, max_tokens=16000, **common)
    if model.startswith("openai.gpt-5") or model.startswith("openai.o"):
        return ChatOpenAI(model_kwargs={"max_completion_tokens": 16000}, **common)
    return ChatOpenAI(temperature=0.1, max_tokens=16000, **common)


def build_agent(settings: Settings, *, display_name: str | None = None, first_name: str | None = None):
    """Build the Deep Agent for one patient. Returns (agent, state, cleanup).

    state holds the OracleSaver checkpointer and the OracleStore memory, both
    in the agent user's own schema (agent/memory.py)."""
    import oracledb

    pid = settings.patient_id
    display = display_name or f"Patient {settings.patient_key}"
    conn = oracledb.connect(user=settings.db_user, password=settings.db_password, dsn=settings.dsn)
    embeddings = OracleEmbeddings(conn=conn, params={"provider": "database", "model": EMBEDDING_MODEL})
    stores_to_close: list[ADB] = []
    checkpointer, store, close_state = agent_memory.open_state(settings.dsn, settings.db_user, settings.db_password, embeddings)

    datastores = {
        "patient_notes": _store(
            settings, "PATIENT_NOTE_VEC",
            f"clinical notes from the chart of synthetic patient {pid}: visits, calls, admissions, messages",
        ),
        "clinical_reference": _store(
            settings, "CLINICAL_REFERENCE",
            "NIH consumer-health reference: conditions, treatments, monitoring, medication safety",
        ),
        "research_evidence": _store(
            settings, "RESEARCH_EVIDENCE",
            "PubMed research abstracts: clinical studies and their conclusions",
        ),
    }
    sql_tools, engine = build_sql_tools(settings.dsn, settings.db_user, settings.db_password)

    # Each specialist gets search and get_document bound to its own store. In
    # langchain-oci 0.3.2 `search` routes by meaning across every store it was
    # built with; a single-store tool set makes the routing explicit.
    dedicated: dict[str, list] = {}
    for alias in datastores:
        own = _store(settings, datastores[alias].table_name, datastores[alias].datastore_description)
        stores_to_close.append(own)
        tools = []
        for t in create_datastore_tools({alias: own}, embedding_model=embeddings, top_k=6):
            if t.name in ("search", "get_document"):
                t.name = f"{t.name}_{alias}"
                t.description = f"Scoped to the {alias} store. " + t.description
                tools.append(t)
        dedicated[alias] = tools
    worker = chat_model(settings, settings.worker_model)
    fmt = {"patient_id": pid, "display_name": display, "first_name": first_name or "there"}

    subagents = [
        {
            "name": "chart-analyst",
            "description": "Reads this patient's relational chart with SQL and the clinical notes with search; returns cited facts, trends, medication concerns and care gaps.",
            "system_prompt": CHART_ANALYST.format(**fmt),
            "model": worker,
            "tools": [*sql_tools, *dedicated["patient_notes"]],
        },
        {
            "name": "care-coordinator",
            "description": "Turns the findings into proposed care actions for clinician approval: lab requests, a message to the patient, a follow-up visit; escalates medication concerns to medication-safety.",
            "system_prompt": CARE_COORDINATOR.format(**fmt),
            "model": worker,
            "tools": build_care_tools(settings.dsn, settings.db_user, settings.db_password, pid),
        },
        {
            "name": "medication-safety",
            "description": "The only agent allowed to propose a medication change (policy CP-03): reviews an escalation against the chart and the reference, then proposes the change for the doctor or declines it.",
            "system_prompt": MEDICATION_SAFETY.format(**fmt),
            "model": worker,
            "tools": [*build_medication_safety_tools(settings.dsn, settings.db_user, settings.db_password, pid),
                      *sql_tools, *dedicated["clinical_reference"]],
        },
        {
            "name": "guideline-researcher",
            "description": "Searches the NIH clinical reference for monitoring, risks and options relevant to given questions; returns cited findings.",
            "system_prompt": GUIDELINE_RESEARCHER,
            "model": worker,
            "tools": dedicated["clinical_reference"],
        },
        {
            "name": "evidence-researcher",
            "description": "Searches PubMed abstracts for studies relevant to given questions; returns cited findings.",
            "system_prompt": EVIDENCE_RESEARCHER,
            "model": worker,
            "tools": dedicated["research_evidence"],
        },
    ]

    # The lead orchestrates and writes; it holds no SQL or search tools of its
    # own, so every fact reaches the brief through a specialist's report.
    agent = create_deepagents_agent(
        model=chat_model(settings, settings.chat_model),
        system_prompt=LEAD.format(**fmt),
        subagents=subagents,
        # Structured final answer: the schema guarantees the brief's shape.
        response_format=ToolStrategy(PreVisitBrief),
        # deepagents 0.7 no longer puts the to-do list in its base stack; the
        # plan is the first thing the clinician watches, so add it back.
        middleware=[TodoListMiddleware(), *guard_middleware(pid)],
        # Durable state on Oracle (langgraph-oracledb): checkpoints for every
        # step, and long-term memory mounted at /memories/ and loaded into the
        # system prompt. The agent may read its memory, never write it.
        checkpointer=checkpointer,
        store=store,
        backend=agent_memory.backend(pid, store),
        memory=[agent_memory.MEMORY_PATH],
        permissions=[FilesystemPermission(operations=["write"], paths=["/memories/**"], mode="deny")],
        name=f"pre-visit-brief-{settings.patient_key}",
    )

    def cleanup() -> None:
        for ds in [*datastores.values(), *stores_to_close]:
            ds.close()
        close_state()
        engine.dispose()
        conn.close()

    return agent, {"checkpointer": checkpointer, "store": store}, cleanup
