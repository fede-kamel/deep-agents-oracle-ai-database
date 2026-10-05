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
three specialists, and writes the brief to /brief.md in its file system.

The chat model is Gemini on OCI Generative AI through the OpenAI-compatible
endpoint, so the only credential the process holds is an API key, and inside
the sandbox that key is a placeholder the OpenShell proxy swaps in transit.
"""

from __future__ import annotations

import json

from langchain_oci import create_deepagents_agent
from langchain_oci.datastores import ADB, create_datastore_tools
from langchain_openai import ChatOpenAI
from langchain_oracledb.embeddings import OracleEmbeddings

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
Never invent an id. If a search returns nothing useful, say so."""

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
2. Read every clinical note: SELECT note_date, kind, body FROM
   DA_OWNER.clinical_note ORDER BY note_date DESC. The chart is small; read
   all of it, and weigh the most recent notes most. Cite notes by their id,
   which search_patient_notes returns (search it for the facts you use), or as
   [SQL:clinical_note] with the note date. Compare discharge medication lists
   with what was held or stopped, and note any guideline-recommended therapy
   the chart says is absent.
   Always report the most recent value of a lab as "latest", with its date.
   For cohort_benchmark trends, a more negative slope means a faster decline:
   compare a falling eGFR slope with p10, not p90.
3. Return a compact fact sheet, most recent first: each line one fact, with numbers, dates and a
   citation. Flag changes, drug-disease or drug-drug concerns, duplications,
   overdue monitoring and care gaps. Do not recommend treatment.

{CITATIONS}"""

GUIDELINE_RESEARCHER = f"""\
You are the guideline researcher. Given the clinical questions the lead agent
sends, search with search_clinical_reference and report
what the reference text says about monitoring, risks and options. Quote short
phrases, attribute each to its id, and say plainly when the reference text
does not cover a question.

{CITATIONS}"""

EVIDENCE_RESEARCHER = f"""\
You are the evidence researcher. Given the clinical questions the lead agent
sends, search with search_research_evidence for studies
that bear on them. For each useful abstract give the research question, the
finding in one sentence, and its id. Prefer two or three relevant abstracts to
many weak ones, and say when nothing relevant turns up.

{CITATIONS}"""

LEAD = f"""\
You prepare pre-visit clinical briefs for a clinician. Every patient in this
system is synthetic; the brief supports a clinician's review and is not
medical advice.

This run is scoped to one patient, {{patient_id}} ({{display_name}}). The
database only shows this patient's rows; never ask for or mention anyone else.

Your first action is write_todos with a short plan (four to six items), and
you update it as items finish. Then delegate with the task tool:
- chart-analyst: the patient's facts, trends, medications, gaps (always first);
- guideline-researcher and evidence-researcher: once you know the questions
  the chart raises, send each of them those questions.
Run the two researchers after the chart analyst, and in parallel with each other.

Write the brief to /brief.md with write_file, in this structure:

# Pre-visit brief - {{display_name}} ({{patient_id}})
> SYNTHETIC RECORD - invented for a demo, not a real patient. For clinician review; not medical advice.

## Snapshot
## What changed
## Medications to review
## Overdue monitoring and open care gaps
## What the reference and research say
## Questions for the visit
## Sources

Rules: every factual sentence carries a citation; patient facts come only
from the chart analyst's sources; reference and research claims come only from
the researchers' ids; compare with cohort_benchmark when the analyst reports
it. The Sources section lists every id you cited, one per line, with its
title. Keep the brief under 700 words. When the file is written, reply with a
two-sentence summary.

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
    return GeminiChatOpenAI(
        model=model,
        api_key=settings.genai_api_key,
        base_url=settings.genai_base_url,
        # OCI streams zstd when asked for it; httpx does not decode zstd.
        default_headers={"Accept-Encoding": "gzip, deflate"},
        temperature=0.1,
        timeout=180,
        max_retries=2,
    )


def build_agent(settings: Settings, *, checkpointer=None, display_name: str | None = None):
    """Build the Deep Agent for one patient. Returns (agent, cleanup)."""
    import oracledb

    pid = settings.patient_id
    display = display_name or f"Patient {settings.patient_key}"
    conn = oracledb.connect(user=settings.db_user, password=settings.db_password, dsn=settings.dsn)
    embeddings = OracleEmbeddings(conn=conn, params={"provider": "database", "model": EMBEDDING_MODEL})
    stores_to_close: list[ADB] = []

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
    fmt = {"patient_id": pid, "display_name": display}

    subagents = [
        {
            "name": "chart-analyst",
            "description": "Reads this patient's relational chart with SQL and the clinical notes with search; returns cited facts, trends, medication concerns and care gaps.",
            "system_prompt": CHART_ANALYST.format(**fmt),
            "model": worker,
            "tools": [*sql_tools, *dedicated["patient_notes"]],
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

    agent = create_deepagents_agent(
        tools=sql_tools,
        datastores=datastores,
        default_store="patient_notes",
        embedding_model=embeddings,
        top_k=6,
        model=chat_model(settings, settings.chat_model),
        system_prompt=LEAD.format(**fmt),
        subagents=subagents,
        middleware=guard_middleware(pid),
        checkpointer=checkpointer,
        name=f"pre-visit-brief-{settings.patient_key}",
    )

    def cleanup() -> None:
        for store in [*datastores.values(), *stores_to_close]:
            store.close()
        engine.dispose()
        conn.close()

    return agent, cleanup
