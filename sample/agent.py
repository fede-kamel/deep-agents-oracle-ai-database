"""A minimal Deep Agent on Oracle AI Database, the pattern of the write-up in one file.

A lead plans and delegates to three specialists:
  chart-analyst      reads the chart with SQL (row-level security decides the rows)
  care-coordinator   proposes lab requests and follow-ups; tries medication changes,
                     which the database refuses for this agent
  medication-safety  the only agent the database lets propose a medication change
The lead writes a short pre-visit brief that cites row ids such as [LAB-A-003];
a gate looks every cited id up in the database before the brief is accepted.
Every step is checkpointed in Oracle (langgraph-oracledb OracleSaver).

Environment (inside the sandbox it comes from the 0600 db.env file and the provider):
  SAMPLE_DB_DSN, SAMPLE_DB_USER (SAMPLE_AGENT_A), SAMPLE_DB_PASSWORD
  SAMPLE_PATIENT (SYN-A), OCI_GENAI_API_KEY (a placeholder in the sandbox), OCI_GENAI_REGION

    python agent.py              # run once against the database
    python agent.py --dry-run    # build the agent graph only: no database, no model calls
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from typing import Literal

from langchain_core.tools import tool

PATIENT = os.environ.get("SAMPLE_PATIENT", "SYN-A")
DSN = os.environ.get("SAMPLE_DB_DSN", "")
USER = os.environ.get("SAMPLE_DB_USER", "SAMPLE_AGENT_A")
PASSWORD = os.environ.get("SAMPLE_DB_PASSWORD", "")
REGION = os.environ.get("OCI_GENAI_REGION", "us-chicago-1")
MODEL = os.environ.get("SAMPLE_MODEL", "openai.gpt-5.5")
GENAI_URL = f"https://inference.generativeai.{REGION}.oci.oraclecloud.com/openai/v1"
QUESTION = (f"Prepare a short pre-visit brief for {PATIENT}. What changed in kidney function, "
            "which medications deserve review because of it, and what should happen before the visit?")
# Anything in brackets that looks like an id is a citation, so an invented id
# such as [LAB-SYN-A-EGFR] is checked too, not skipped.
CITED = re.compile(r"\[([A-Z]{2,}(?:-[A-Z0-9]+)+)\]")
SOURCES = {"LAB": ("lab_result", "lab_id"), "MED": ("medication", "med_id"), "SYN": ("patient", "patient_id")}


def connect(agent_name: str):
    """One connection per call, as the patient's own database user. The agent's
    name goes into CLIENT_IDENTIFIER here, in tool code; the model never sets it,
    and the database policy reads it."""
    import oracledb

    conn = oracledb.connect(user=USER, password=PASSWORD, dsn=DSN)
    conn.client_identifier = agent_name   # set by tool code; the policy reads it
    return conn


# ---- tools: reads are free-form SQL, writes are one fixed INSERT -------------

@tool
def query_chart(sql: str) -> str:
    """Run one read-only Oracle SELECT against the patient's chart.

    Tables: SAMPLE_OWNER.patient, SAMPLE_OWNER.medication (med_id, name, dose),
    SAMPLE_OWNER.lab_result (lab_id, test, value, unit, taken_on),
    SAMPLE_OWNER.care_action. Only this patient's rows are visible.
    Cite facts with the row id in brackets: [LAB-A-001], [MED-A-002].
    """
    import oracledb

    statement = sql.strip().rstrip(";")
    if not re.match(r"(?is)^\s*(select|with)\b", statement) or ";" in statement:
        return "Refused: query_chart accepts exactly one SELECT or WITH statement."
    with connect("chart-analyst") as conn:
        cur = conn.cursor()
        try:
            cur.execute(statement)
        except oracledb.DatabaseError as exc:
            return f"Oracle error: {str(exc).splitlines()[0]}"
        cols = [d[0].lower() for d in cur.description]
        rows = cur.fetchmany(101)
    lines = [str(dict(zip(cols, (str(v) for v in row), strict=True))) for row in rows[:100]]
    return "\n".join(lines) or "No rows."


def propose_tool(agent_name: str):
    """The proposal tool, bound to the agent that holds it. The model fills in
    typed arguments; the database decides whether this agent may propose."""

    @tool
    def propose_action(kind: Literal["lab_request", "follow_up", "medication_change"],
                       title: str, rationale: str, citations: str) -> str:
        """Propose a care action for this patient. A person approves it later.

        kind: lab_request, follow_up, or medication_change.
        title: one line, e.g. "Repeat eGFR and urine albumin before the visit".
        rationale: one or two sentences grounded in the chart.
        citations: the row ids behind it, e.g. "[LAB-A-003] [MED-A-003]".
        """
        import oracledb

        with connect(agent_name) as conn:
            cur = conn.cursor()
            new_id = cur.var(oracledb.NUMBER)
            try:
                cur.execute(
                    "INSERT INTO SAMPLE_OWNER.care_action"
                    " (patient_id, kind, title, rationale, citations)"
                    " VALUES (:p, :k, :t, :r, :c) RETURNING id INTO :i",
                    p=PATIENT, k=kind, t=title[:250], r=rationale[:2000], c=citations[:1000], i=new_id)
                conn.commit()
            except oracledb.DatabaseError as exc:
                return f"Refused by the database: {str(exc).splitlines()[0]}"
        action_id = int(new_id.getvalue()[0])
        return f"Proposed care action {action_id} ({kind}); a person decides."

    return propose_action


# ---- the gate: every cited id must exist, looked up as the patient's user ----

def unresolved(brief: str) -> tuple[list[str], list[str]]:
    ids = sorted(set(CITED.findall(brief)))
    missing = []
    with connect("gate") as conn:
        cur = conn.cursor()
        for cid in ids:
            source = SOURCES.get(cid.split("-")[0])
            if source is None:              # not a kind of row this chart has
                missing.append(cid)
                continue
            table, column = source
            cur.execute(f"SELECT COUNT(*) FROM SAMPLE_OWNER.{table}"
                        f" WHERE {column} = :i", i=cid)
            if cur.fetchone()[0] == 0:
                missing.append(cid)
    return ids, missing


# ---- the agent ---------------------------------------------------------------

LEAD = """You prepare a pre-visit brief for synthetic patient {patient}. You hold no data tools.
Plan with write_todos, then delegate with task:
1. chart-analyst: the kidney trend, the medications, recent glucose.
2. care-coordinator: propose what should happen before the visit (labs, a follow-up), and try
   the one medication change that matters most.
3. If the care coordinator reports that the database refused a medication change, delegate
   that change to medication-safety, which may propose it or decline with a reason.
Then write the brief in Markdown: Snapshot, What changed, Medication review, Proposed actions.
Every factual sentence ends with the row ids it rests on, exactly as the tools returned them,
for example [LAB-A-003]. Cite nothing a specialist did not report."""


def build_agent(model, checkpointer):
    from langchain_oci import create_deepagents_agent

    subagents = [
        {"name": "chart-analyst",
         "description": "Reads the patient's chart with SQL and reports facts with their row ids.",
         "system_prompt": "Query the chart with query_chart. Report each fact with its row id, e.g. [LAB-A-002].",
         "tools": [query_chart]},
        {"name": "care-coordinator",
         "description": "Proposes lab requests and follow-ups; tries a medication change if one is needed.",
         "system_prompt": ("Propose at most three actions with propose_action, each with citations. "
                           "If a medication change is refused, say so plainly; do not retry it."),
         "tools": [propose_tool("care-coordinator")]},
        {"name": "medication-safety",
         "description": "The only agent allowed to propose a medication change; re-checks the chart first.",
         "system_prompt": ("Re-read the labs and medications with query_chart, then propose the change with "
                           "propose_action (kind medication_change) or decline it with a cited reason."),
         "tools": [query_chart, propose_tool("medication-safety")]},
    ]
    return create_deepagents_agent(
        model=model,
        system_prompt=LEAD.format(patient=PATIENT),
        subagents=subagents,
        checkpointer=checkpointer,
        name=f"sample-brief-{PATIENT}",
    )


def chat_model():
    from langchain_openai import ChatOpenAI

    # OCI Generative AI's OpenAI-compatible endpoint. In the sandbox the key is a
    # placeholder; the OpenShell proxy swaps in the real key on the way out.
    return ChatOpenAI(model=MODEL, base_url=GENAI_URL, api_key=os.environ["OCI_GENAI_API_KEY"],
                      max_completion_tokens=8000)


def dry_run() -> int:
    from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
    from langgraph.checkpoint.memory import InMemorySaver

    class FakeWithTools(GenericFakeChatModel):
        def bind_tools(self, tools, **kwargs):  # the graph only needs to bind, not to run
            return self

    agent = build_agent(FakeWithTools(messages=iter([])), InMemorySaver())
    nodes = sorted(agent.get_graph().nodes)
    print("agent graph built:", ", ".join(n for n in nodes if not n.startswith("__")))
    print("DRY RUN OK")
    return 0


def main() -> int:
    if not (DSN and PASSWORD and os.environ.get("OCI_GENAI_API_KEY")):
        print("ABORT: SAMPLE_DB_DSN, SAMPLE_DB_PASSWORD and OCI_GENAI_API_KEY must be set.", file=sys.stderr)
        return 2
    from langgraph_oracledb.checkpoint.oracle import OracleSaver

    with connect("checkpointer") as state_conn:
        saver = OracleSaver(state_conn)
        saver.setup()  # creates the checkpoint tables in the agent's own schema, once
        agent = build_agent(chat_model(), saver)
        config = {"configurable": {"thread_id": f"sample-{PATIENT}-{int(time.time())}"}, "recursion_limit": 150}
        result = agent.invoke({"messages": [{"role": "user", "content": QUESTION}]}, config=config)
        brief = result["messages"][-1].content
        ids, missing = unresolved(brief)
        if missing:  # one repair turn, on the same checkpointed thread
            result = agent.invoke({"messages": [{"role": "user", "content":
                f"These cited ids do not exist: {', '.join(missing)}. Rewrite the brief citing only ids "
                "the specialists returned."}]}, config=config)
            brief = result["messages"][-1].content
            ids, missing = unresolved(brief)
    print(brief)
    print(f"\ngate: {len(ids)} cited ids, {len(missing)} missing" + (f" ({', '.join(missing)})" if missing else ""))
    print("BRIEF OK" if ids and not missing else "BRIEF REJECTED")
    return 0 if ids and not missing else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="build the graph only")
    sys.exit(dry_run() if parser.parse_args().dry_run else main())
