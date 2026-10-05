"""Build the deck on the Oracle FY26 corporate template.

The template (masters, layouts, theme) comes from an Oracle FY26 deck passed as
--template; every existing slide is dropped and the slides below are built on
its "Title/Cover_5" and "Light - Blank" layouts with the same type system: an
Oracle Sans kicker in Oracle red, a 30 pt title, a short red rule, and the
copyright footer. Run metrics are read from the event logs, so the numbers on
the slides are the numbers in the evidence.

    uv run --with python-pptx python deck/build_deck.py \
        --template ~/Desktop/litellm/LiteLLM-OCI-PPO-FY26.pptx \
        --out deck/Deep-Agents-Oracle-AI-Database-FY26.pptx
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "docs" / "figures"
LOGOS = ROOT / "docs" / "figures-src" / "logos"
EVIDENCE = ROOT / "evidence"

RED = RGBColor(0xC7, 0x46, 0x34)
INK = RGBColor(0x2A, 0x2F, 0x2F)
BODY = RGBColor(0x57, 0x5C, 0x5C)
MUTED = RGBColor(0x8A, 0x8F, 0x8F)
TEAL = RGBColor(0x04, 0x53, 0x6F)
SAND = RGBColor(0xF4, 0xF2, 0xF0)
SAND_LINE = RGBColor(0xE2, 0xDF, 0xDB)
CARD_LINE = RGBColor(0xE6, 0xE2, 0xDE)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GREEN = RGBColor(0x5F, 0x7D, 0x4F)
OCHRE = RGBColor(0xB0, 0x7D, 0x1F)
VIOLET = RGBColor(0x6B, 0x4F, 0xA0)
YELLOW = RGBColor(0xF0, 0xCC, 0x71)
FONT = "Oracle Sans"
MONO = "Consolas"
QUESTIONS = [
    "What has changed in kidney function, and which medications and monitoring deserve review?",
    "Why does she keep being readmitted, and what should the clinic address first?",
    "Which medications add to fall risk or duplicate each other?",
]
FOOTER = "Copyright © 2026, Oracle and/or its affiliates   —   Personal open-source work with synthetic data"


# ------------------------------------------------------------------ helpers --

def drop_all_slides(prs: Presentation) -> None:
    ids = prs.slides._sldIdLst
    for sid in list(ids):
        prs.part.drop_rel(sid.rId)
        ids.remove(sid)


def layout(prs, name):
    return next(l for l in prs.slide_layouts if l.name == name)


def text(slide, x, y, w, h, runs, size=14, color=BODY, bold=False, align=PP_ALIGN.LEFT, font=FONT,
         anchor=MSO_ANCHOR.TOP, spacing=None, line=1.12):
    """runs: str, or list of paragraphs; a paragraph is a str or a list of (text, overrides) tuples."""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    paragraphs = [runs] if isinstance(runs, str) else runs
    for i, para in enumerate(paragraphs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line
        parts = [(para, {})] if isinstance(para, str) else para
        for chunk, o in parts:
            r = p.add_run()
            r.text = chunk
            f = r.font
            f.name = o.get("font", font)
            f.size = Pt(o.get("size", size))
            f.bold = o.get("bold", bold)
            f.italic = o.get("italic", False)
            f.color.rgb = o.get("color", color)
            if spacing or o.get("spacing"):
                r._r.get_or_add_rPr().set("spc", str(o.get("spacing", spacing)))
        if isinstance(para, list) and para and para[0][1].get("space_after") is not None:
            p.space_after = Pt(para[0][1]["space_after"])
    return box


def rect(slide, x, y, w, h, fill, line=None, shape=MSO_SHAPE.RECTANGLE):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(0.75)
    s.shadow.inherit = False
    return s


def header(slide, kicker, title):
    text(slide, 0.72, 0.46, 11.9, 0.3, kicker.upper(), size=11.5, color=RED, bold=True, spacing=180)
    text(slide, 0.72, 0.78, 11.9, 1.0, title, size=30, color=INK, bold=True)
    rect(slide, 0.72, 1.40, 1.15, 0.06, RED)
    text(slide, 0.72, 7.06, 11.9, 0.3, FOOTER, size=8, color=MUTED)


def bullets(slide, x, y, w, h, items, size=14.5):
    paras = []
    for lead, rest in items:
        paras.append([("▪  ", {"color": RED, "bold": True, "size": size}), (lead + " ", {"bold": True, "color": INK, "size": size}),
                      (rest, {"color": BODY, "size": size})])
    box = text(slide, x, y, w, h, paras, size=size)
    for p in box.text_frame.paragraphs:
        p.space_after = Pt(11)
    return box


def card(slide, x, y, w, h, title, body, accent=RED, fill=SAND, title_size=15, body_size=12.5):
    rect(slide, x, y, w, h, fill, line=CARD_LINE)
    rect(slide, x, y, w, 0.07, accent)
    text(slide, x + 0.2, y + 0.2, w - 0.4, h - 0.3,
         [[(title, {"bold": True, "color": INK, "size": title_size})], [(body, {"color": BODY, "size": body_size})]], line=1.15)


def figure(slide, name, x, y, w, caption=None, frame=True):
    path = FIG / name
    if frame:
        rect(slide, x - 0.08, y - 0.08, w + 0.16, 0.1, WHITE)  # placeholder, resized below
    pic = slide.shapes.add_picture(str(path), Inches(x), Inches(y), width=Inches(w))
    if frame:
        border = slide.shapes[-2]
        border.top, border.left = pic.top - Inches(0.08), pic.left - Inches(0.08)
        border.width, border.height = pic.width + Inches(0.16), pic.height + Inches(0.16)
        border.line.color.rgb = CARD_LINE
        border.line.width = Pt(0.75)
    if caption:
        cy = Emu(pic.top + pic.height).inches + 0.14
        text(slide, x, cy, w, 0.5, caption, size=10.5, color=BODY, line=1.1)
        slide.shapes[-1].text_frame.paragraphs[0].runs[0].font.italic = True
    return pic


def code(slide, x, y, w, h, source, size=11.5):
    rect(slide, x, y, w, h, SAND, line=SAND_LINE)
    rect(slide, x, y, 0.07, h, TEAL)
    lines = source.strip("\n").splitlines()
    paras = []
    for ln in lines:
        stripped = ln.lstrip()
        color = MUTED if stripped.startswith("#") else (TEAL if stripped.split(" ")[0] in ("from", "import", "def", "return", "CREATE", "BEGIN", "END;", "SELECT", "FROM", "WHERE") else INK)
        paras.append([(ln or " ", {"font": MONO, "size": size, "color": color})])
    text(slide, x + 0.25, y + 0.2, w - 0.4, h - 0.3, paras, line=1.05)


def table(slide, x, y, w, rows, col_w, size=12, header_fill=TEAL):
    shape = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(0.4 * len(rows)))
    tbl = shape.table
    for j, cw in enumerate(col_w):
        tbl.columns[j].width = Inches(cw)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = tbl.cell(i, j)
            cell.fill.solid()
            cell.fill.fore_color.rgb = header_fill if i == 0 else (WHITE if i % 2 else SAND)
            tf = cell.text_frame
            tf.paragraphs[0].text = ""
            r = tf.paragraphs[0].add_run()
            r.text = str(val)
            r.font.name = FONT
            r.font.size = Pt(size)
            r.font.bold = i == 0 or j == 0
            r.font.color.rgb = WHITE if i == 0 else (INK if j == 0 else BODY)
            cell.margin_left = cell.margin_right = Inches(0.12)
    return tbl


def notes(slide, body):
    slide.notes_slide.notes_text_frame.text = body


def flow_runs() -> list[dict]:
    """The published evidence flow: one summary line per run (evidence/flow.jsonl)."""
    path = EVIDENCE / "flow.jsonl"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if "label" in d:
            rows.append(d)
    return rows


def run_metrics(key: str) -> dict:
    """Metrics of the published run for one patient, from its event log."""
    path = EVIDENCE / f"run-{key}.jsonl"
    m = {"seconds": "–", "tool_calls": "–", "sql": "–", "searches": "–", "delegations": "–", "citations": "–", "verified": "–"}
    if not path.exists():
        return m
    for line in path.read_text().splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("type") == "done":
            m.update({k: e[k] for k in ("seconds", "tool_calls", "sql", "searches", "delegations")})
        if e.get("type") == "verify" and e.get("final", True):
            m["citations"] = e.get("citations", "–")
            m["verified"] = "passed" if e.get("passed") else "failed"
    return m


# ------------------------------------------------------------------- slides --

def build(template: Path, out: Path) -> None:
    prs = Presentation(str(template))
    drop_all_slides(prs)
    blank = layout(prs, "Light - Blank")

    # 1 · cover
    s = prs.slides.add_slide(layout(prs, "Title/Cover_5"))
    for ph in s.placeholders:
        idx = ph.placeholder_format.idx
        if idx == 0:
            ph.text = "Deep Agents on Your Own Data"
        elif ph.placeholder_format.type is not None and ph.name.startswith("Text Placeholder 2"):
            ph.text = "LangChain Deep Agents on Oracle AI Database"
        elif ph.name.startswith("Text Placeholder 3"):
            ph.text = "Federico Kamelhar"
        elif ph.name.startswith("Text Placeholder 4"):
            ph.text = "Senior Principal Architect, Agentic AI\nOracle\nOctober 2026"
    for ph in list(s.placeholders):
        if ph.has_text_frame and not ph.text_frame.text.strip():
            ph._element.getparent().remove(ph._element)
    rect(s, 2.62, 1.1, 0.02, 0.4, RGBColor(0x8F, 0xA6, 0xAD))
    s.shapes.add_picture(str(LOGOS / "langchain-white.png"), Inches(2.82), Inches(1.12), height=Inches(0.36))
    rect(s, 4.67, 1.1, 0.02, 0.4, RGBColor(0x8F, 0xA6, 0xAD))
    s.shapes.add_picture(str(LOGOS / "nvidia-white-mono.png"), Inches(4.87), Inches(1.12), height=Inches(0.36))
    notes(s, "Deep Agents on your own data: a LangChain Deep Agent, built with the open-source langchain-oracle packages, "
             "writes a pre-visit clinical brief from Oracle AI Database 26ai, inside an NVIDIA OpenShell sandbox. "
             "Every patient is synthetic.")

    # 2 · why
    s = prs.slides.add_slide(blank)
    header(s, "Agents on data that matters", "Why this matters")
    bullets(s, 0.72, 1.95, 6.55, 4.8, [
        ("The data is the hard part.", "Agents earn their keep on a company's own records, and those records are exactly what nobody wants an agent to wander through."),
        ("Deep Agents do real research.", "They plan, delegate to specialists, query and search, and write a document. That is more reach than a chat window, not less."),
        ("Safety has to be structural.", "The database decides which rows an agent sees; the sandbox decides which hosts it reaches; the key never enters it."),
        ("Grounding has to be checked.", "A brief is useful only when every claim points at a row, a note, or a source that exists."),
    ])
    figure(s, "figure1-architecture.png", 7.62, 1.92, 4.9,
           "Figure 1 — The Deep Agent runs inside an OpenShell sandbox; Oracle AI Database holds the chart, the vectors and the model.")
    notes(s, "Set up the problem: the value of agents is on your own data, and the risk is too. The answer in this talk is "
             "structural: the database, the sandbox and a grounding gate each refuse on their own.")

    # 3 · the scenario
    s = prs.slides.add_slide(blank)
    header(s, "Three synthetic patients, one question each", "The scenario: a pre-visit clinical brief")
    pats = [
        ("Patient X · SYN-X", "Type 2 diabetes with declining kidney function", "eGFR 68 → 47 in 18 months, UACR 22 → 148, daily ibuprofen, glipizide lows, retinal screening open since 2025.", TEAL),
        ("Patient Y · SYN-Y", "Heart failure, readmitted twice in 90 days", "K 5.6 on spironolactone + lisinopril + potassium chloride, KCl back on the discharge list, skipped diuretic doses, cost barriers.", RED),
        ("Patient Z · SYN-Z", "COPD with polypharmacy and a recent fall", "Tiotropium + ipratropium, oxybutynin, zolpidem + diphenhydramine, orthostatic drop, pulmonary rehab declined.", VIOLET),
    ]
    for i, (t, sit, body, c) in enumerate(pats):
        x = 0.72 + i * 4.12
        rect(s, x, 2.0, 3.86, 3.65, SAND, line=CARD_LINE)
        rect(s, x, 2.0, 3.86, 0.07, c)
        text(s, x + 0.22, 4.15, 3.4, 1.4, [[("The clinician asks: ", {"bold": True, "size": 11.5, "color": INK}),
                                           ("“" + QUESTIONS[i] + "”", {"italic": True, "size": 11.5, "color": BODY})]], line=1.15)
        text(s, x + 0.22, 2.22, 3.4, 3.3, [
            [(t, {"bold": True, "size": 16, "color": INK})],
            [(sit, {"bold": True, "size": 13, "color": c})],
            [(body, {"size": 12.5, "color": BODY})],
        ], line=1.18)
    rect(s, 0.72, 5.95, 11.9, 0.82, TEAL)
    text(s, 0.98, 6.07, 11.4, 0.6, [[("Every record is invented. ", {"bold": True, "color": WHITE, "size": 14}),
                                    ("The schema enforces it (CHECK is_synthetic = 'Y', ids start with SYN-), and the agent's input guard blocks real-looking identifiers. "
                                     "Reference text is public: MedQuAD (NIH) and PubMedQA.", {"color": WHITE, "size": 12.5})]])
    notes(s, "Each chart is hand-written to carry findings a careful clinician would raise. No real patient data is used anywhere, by design and by policy.")

    # 4 · the deep agent
    s = prs.slides.add_slide(blank)
    header(s, "LangChain Deep Agents, built with langchain-oracle", "Plan, delegate, retrieve, write")
    figure(s, "figure2-deep-agent.png", 0.72, 1.9, 7.1)
    bullets(s, 8.15, 1.95, 4.5, 4.9, [
        ("Lead.", "Plans with write_todos, delegates with task, and returns a structured PreVisitBrief. It holds no data tools."),
        ("Chart analyst.", "Reads the relational chart with read-only SQL and the notes with hybrid search."),
        ("Two researchers.", "Each bound to one store, five or more searches, six to ten sources each."),
        ("Care coordinator.", "Turns findings into proposed lab requests, a patient message and a follow-up."),
        ("Models.", "GPT-5.5 leads; Gemini 2.5 Flash runs the specialists, both on OCI Generative AI."),
    ], size=13.5)
    notes(s, "create_deepagents_agent from langchain-oci composes the LangChain Deep Agents harness with Oracle datastores. "
             "Specialists each get a single-store tool set so routing is explicit.")

    # 5 · code
    s = prs.slides.add_slide(blank)
    header(s, "Thirty lines of langchain-oracle", "Build the agent")
    code(s, 0.72, 1.9, 7.4, 4.6, '''
from langchain_oci import create_deepagents_agent
from langchain_oci.datastores import ADB, create_datastore_tools
from langchain_oracledb.embeddings import OracleEmbeddings

# Embeddings run inside Oracle AI Database (ONNX model)
emb = OracleEmbeddings(conn=conn, params={
    "provider": "database", "model": "DA_OWNER.MINILM_L12"})

notes = ADB(dsn=dsn, user="DA_AGENT_Y", password=pw,
            table_name="PATIENT_NOTE_VEC")
analyst_tools = [*sql_tools, *create_datastore_tools(
    {"patient_notes": notes}, embedding_model=emb)]

agent = create_deepagents_agent(
    model=ChatOpenAI(model="openai.gpt-5.5",
                     base_url=OCI_OPENAI_ENDPOINT,
                     api_key=os.environ["OCI_GENAI_API_KEY"]),
    system_prompt=LEAD,
    subagents=[chart_analyst, guideline, evidence],
    middleware=[TodoListMiddleware(), *guards],
    response_format=ToolStrategy(PreVisitBrief),
)''', size=11)
    card(s, 8.45, 1.9, 4.17, 1.9, "One credential in the process",
         "OCI_GENAI_API_KEY is a placeholder inside the sandbox; OpenShell's proxy swaps in the real key on the way to OCI.", accent=GREEN)
    card(s, 8.45, 4.05, 4.17, 1.9, "Schema-shaped output",
         "ToolStrategy(PreVisitBrief) fixes the brief's sections; the runner renders and checks it before anyone reads it.", accent=TEAL)
    notes(s, "The agent is ordinary langchain-oracle code. The interesting parts are what it does not hold: no OCI key, no write grant.")

    # 6 · the data layer
    s = prs.slides.add_slide(blank)
    header(s, "Relational, vector, and the model, in one database", "Oracle AI Database 26ai as the system of record")
    figure(s, "figure3-data.png", 0.72, 1.9, 7.1)
    bullets(s, 8.15, 1.95, 4.5, 4.9, [
        ("Alembic migrations.", "Clinical schema, OracleVS-shaped vector tables, a cohort benchmark, row-level security, and citable note ids."),
        ("Embedded from the rows.", "OracleAutonomousDatabaseLoader reads the notes; OracleTextSplitter and the ONNX model run in the database."),
        ("Hybrid search.", "Vector similarity plus Oracle Text, fused by the langchain-oci search tool."),
        ("Benchmarks, not rows.", "300 background patients become percentiles the agent may compare against."),
    ], size=13.5)
    notes(s, "Text never leaves the database to be vectorised. The cohort benchmark is how an agent compares without reading other patients.")

    # 7 · agent to SQL + VPD
    s = prs.slides.add_slide(blank)
    header(s, "Agent to SQL, scoped by the database", "Any SELECT the model writes, one patient's rows")
    code(s, 0.72, 1.9, 6.7, 4.1, """
CREATE FUNCTION DA_PATIENT_SCOPE(p_schema, p_object)
RETURN VARCHAR2 AS
  v_user := SYS_CONTEXT('USERENV', 'SESSION_USER');
BEGIN
  IF v_user = 'DA_OWNER' THEN RETURN '1=1';
  ELSIF REGEXP_LIKE(v_user, '^DA_AGENT_[A-Z]$') THEN
    RETURN 'patient_id = ''SYN-' || SUBSTR(v_user, -1) || '''';
  END IF;
  RETURN '1=0';
END;

-- Alembic 0004: one policy per patient table + the note vectors
DBMS_RLS.ADD_POLICY('DA_OWNER', 'LAB_RESULT', 'DA_SCOPE_LAB_RESULT',
                    'DA_OWNER', 'DA_PATIENT_SCOPE');

-- the chart analyst, as DA_AGENT_Y
SELECT REGR_SLOPE(value, collected_on - DATE '2024-01-01') * 365
FROM DA_OWNER.lab_result WHERE test = 'eGFR';   -- -37.4 / year""", size=10.5)
    table(s, 7.7, 1.9, 4.92, [
        ["Probe as DA_AGENT_X", "Result"],
        ["SELECT patients", "1 (SYN-X)"],
        ["rows of SYN-Y", "0"],
        ["note vectors visible", "1 patient"],
        ["UPDATE medication", "ORA-41900"],
        ["CREATE TABLE", "ORA-01031"],
        ["id without SYN-", "ORA-02290"],
    ], col_w=[2.9, 2.02], size=12)
    text(s, 7.7, 5.35, 4.92, 1.4, [[("The model writes the SQL; Oracle decides the rows. ", {"bold": True, "color": INK, "size": 13}),
                                   ("scripts/verify.py --rls-only: 14 of 14 checks pass for the three agent users.", {"color": BODY, "size": 12.5})]])
    notes(s, "Virtual Private Database adds a predicate to every statement the agent session runs. The tool layer is the weakest guard on purpose.")

    # 7b · from brief to action
    s = prs.slides.add_slide(blank)
    header(s, "Agentic workflows, with a human in the loop", "From brief to action")
    figure(s, "figure8-workflow.png", 0.72, 1.85, 7.25)
    bullets(s, 8.3, 1.95, 4.35, 4.9, [
        ("Propose.", "The care coordinator inserts proposals: a lab request, a portal message, a follow-up. A trigger forces 'proposed'; VPD refuses any other patient."),
        ("Approve.", "The clinician reviews each card in the web app, edits if needed, approves or rejects."),
        ("Execute.", "DECIDE_CARE_ACTION creates the lab order, queues the message, requests the appointment, and audits every step."),
    ], size=13.5)
    notes(s, "Three identities, three powers. The agent never holds the power to act; the database does, on the clinician's word.")

    # 7c · state and memory
    s = prs.slides.add_slide(blank)
    header(s, "langgraph-oracledb in the agent's own schema", "The agent remembers")
    figure(s, "figure9-memory.png", 0.72, 1.85, 7.25)
    bullets(s, 8.3, 1.95, 4.35, 4.9, [
        ("Checkpoints.", "OracleSaver persists every step of every run; repairs resume from state."),
        ("Long-term memory.", "OracleStore with an IVF vector index over in-database embeddings, mounted at /memories/ by StoreBackend."),
        ("What it remembers.", "Each accepted brief and each clinician decision. The next brief says what changed and never re-proposes what was done or rejected."),
    ], size=13.5)
    notes(s, "The persistence pattern is the one documented in langchain-oracle's deepagents guide: checkpointer=OracleSaver, store=OracleStore, backend=StoreBackend.")

    # 8 · safety net
    s = prs.slides.add_slide(blank)
    header(s, "Measured from inside the sandbox", "Four layers, none asks the agent to behave")
    figure(s, "figure4-safety-net.png", 0.72, 1.85, 7.25)
    bullets(s, 8.3, 1.95, 4.35, 4.9, [
        ("Sandbox egress.", "Two surfaces granted; example.com, Object Storage and PyPI refused at connect; PUT gets 403."),
        ("Database.", "One patient per agent user: SELECT, plus proposals that only the clinician can approve; non-synthetic rows rejected."),
        ("Input guard.", "Blocks SSN, phone, email, MRN, date of birth and other patients' ids."),
        ("Brief gate.", "Structure, length and every cited id, checked before acceptance."),
    ], size=13.5)
    notes(s, "Each layer has its own transcript: safety_probe.sh 7/7, verify.py 14/14, guard checks 7/7.")

    # 9 · one run
    s = prs.slides.add_slide(blank)
    header(s, "The web app and Codex call the same script", "One run, beat by beat")
    figure(s, "figure5-sequence.png", 0.72, 1.85, 7.25)
    bullets(s, 8.3, 1.95, 4.35, 4.9, [
        ("Create.", "Sandbox with the provider and the policy; the key stays in the gateway."),
        ("Upload.", "Agent code and a 0600 login file, deleted as soon as it is read."),
        ("Run.", "Plan, delegate, query, search, return the structured brief."),
        ("Watch.", "Every hop is a NET:OPEN or HTTP:POST line with ALLOWED and the policy that allowed it."),
    ], size=13.5)
    notes(s, "OpenShell 0.1.2 note: the first settings poll reloads policy about ten seconds in; the script waits for it.")

    # 10 · the web app
    s = prs.slides.add_slide(blank)
    header(s, "Pick a patient, ask, watch the agents work", "The application")
    shots = ROOT / "docs" / "screenshots"
    if (shots / "02-agents-at-work.png").exists():
        figure(s, "../screenshots/02-agents-at-work.png", 0.72, 1.85, 5.8)
        figure(s, "../screenshots/06-inspect-trace.png", 6.82, 1.85, 5.8)
        text(s, 0.72, 5.7, 11.9, 0.9, [[("Overview: ", {"bold": True, "color": INK, "size": 12.5}),
            ("a guided flow (patient, agents at work, brief, actions, memory); the live plan beside the sandbox console, where each agent's step sits next to the network decision it caused.  ", {"size": 12.5}),
            ("Agent trace: ", {"bold": True, "color": INK, "size": 12.5}),
            ("every reasoning step, delegation, tool call with full arguments and result, the gate's verdicts, filterable by agent; any panel goes full screen.", {"size": 12.5})]])
    notes(s, "The UI is a thin client: FastAPI runs scripts/sandbox.sh and streams the agent channel and the console channel over SSE.")

    # 10b · actions
    s = prs.slides.add_slide(blank)
    header(s, "The clinician decides", "Proposed actions, approved and executed")
    if (shots / "04-actions.png").exists():
        figure(s, "../screenshots/04-actions.png", 0.72, 1.85, 7.25)
    bullets(s, 8.3, 1.95, 4.35, 4.9, [
        ("Each card", "shows the rationale with its citations, the drafted patient message (editable), the tests, or the follow-up window."),
        ("Approve and execute", "calls DECIDE_CARE_ACTION as DA_CLINICIAN; the card moves proposed → approved → executed."),
        ("Every decision", "is written to the patient's memory. Y's second brief did not re-order the executed labs, asked for a BNP instead, and escalated the follow-up."),
    ], size=13.5)
    notes(s, "Nothing is sent anywhere real: the portal outbox is a table, and every patient is synthetic.")

    # 11 · grounding gate
    s = prs.slides.add_slide(blank)
    header(s, "Caught on a real run", "A brief is accepted only when its sources exist")
    figure(s, "figure7-grounding-gate.png", 0.72, 1.85, 7.25)
    bullets(s, 8.3, 1.95, 4.35, 4.9, [
        ("What happened.", "The lead cited MEDQUAD-00001 for a heart-failure fact. No search had returned it."),
        ("What the gate did.", "Looked every id up as the patient's own user, and sent the draft back with the missing id named."),
        ("Why it matters.", "Fluent and wrong is the expensive failure. Here it never reaches the clinician."),
    ], size=13.5)
    notes(s, "The real heart-failure reference rows are MEDQUAD-036xx. The gate runs inside the sandbox; scripts/verify.py repeats it afterwards.")

    # 12 · results
    s = prs.slides.add_slide(blank)
    header(s, "Four runs inside the sandbox, through the web app", "Results")
    rows = [["Run", "Seconds", "Tool calls", "SQL", "Searches", "Actions", "Citations", "Memory", "Gate"]]
    for r in flow_runs():
        rows.append([f"Patient {r['patient']} · {r['label'].split(',')[0]}", round(r.get("seconds") or 0), r.get("tool_calls"), r.get("sql"),
                     r.get("searches"), r.get("actions", 0), r.get("citations"), f"{r.get('memory_entries', 0)} loaded",
                     "passed" if r.get("passed") else "failed"])
    table(s, 0.72, 1.95, 11.9, rows, col_w=[2.6, 1.0, 1.15, 0.8, 1.1, 1.0, 1.15, 1.6, 1.5], size=12)
    card(s, 0.72, 4.35, 3.86, 1.75, "Sandbox boundary", "safety_probe.sh: 7 of 7. Key is a placeholder; only GenAI and the database are reachable; 0 denied during runs.", accent=GREEN)
    card(s, 4.84, 4.35, 3.86, 1.75, "Database guarantees", "verify.py --rls-only: 19 of 19. One patient per user, proposals only for that patient, no approval or execution by the agent.", accent=RED)
    card(s, 8.96, 4.35, 3.66, 1.75, "Grounding", "Every cited id resolves in the database as the patient's own user, checked twice: in the sandbox and afterwards.", accent=TEAL)
    notes(s, "All numbers come from evidence/run-*.jsonl and the probe and verify transcripts.")

    # 13 · built by codex
    s = prs.slides.add_slide(blank)
    header(s, "The same method as the OpenShell kill switch", "Built and run by Codex")
    figure(s, "figure6-codex.png", 0.72, 1.85, 7.25)
    bullets(s, 8.3, 1.95, 4.35, 4.9, [
        ("A spec with checkpoints.", "codex/SPEC.md: inputs, preflight, build steps, acceptance, known behaviour, report."),
        ("Two operator steps.", "ADMIN password and GenAI key, typed with read -rs in the operator's own terminal."),
        ("Nothing else needs a person.", "Codex migrates, seeds, embeds, probes, runs X, Y and Z, verifies, and reports."),
    ], size=13.5)
    notes(s, "Codex never sees a secret: the two secret-bearing steps are handed to the operator with 'reply done'.")

    # 14 · field notes
    s = prs.slides.add_slide(blank)
    header(s, "What cost real time", "Field notes")
    notes_rows = [
        ("python-oracledb 26.x thin", "OracleEmbeddings fails building VECTOR_ARRAY_T (DPY-3013). Pin oracledb<4."),
        ("Gemini on the OpenAI endpoint", "Rejects exclusiveMinimum in tool schemas; tool results must be JSON objects."),
        ("langchain-oci 0.3.2 search", "Routes by meaning across all stores, with no store argument: give each specialist its own."),
        ("deepagents 0.7", "No to-do list in the base stack: add TodoListMiddleware for a visible plan."),
        ("Middleware and recursion", "Each middleware adds graph nodes; eleven PII guards meant six model turns. Merge them."),
        ("OpenShell 0.1.2", "The first settings poll closes open connections about 10 s in: wait for it. ADB TLS needs tcp + tls: skip."),
        ("Ids from memory", "Models cite plausible ids they never retrieved: give SQL rows their vector id (Alembic 0005) and check every id."),
        ("PL/SQL through Alembic", "op.execute reads :NEW in trigger bodies as a bind parameter: use exec_driver_sql for PL/SQL."),
        ("GPT-6 on API keys", "Chat Completions refuses tools with reasoning on; /responses returned 404 for our API key. GPT-5.5 leads."),
    ]
    table(s, 0.72, 1.95, 11.9, [["Where", "What we found"]] + [list(r) for r in notes_rows], col_w=[3.3, 8.6], size=12)
    notes(s, "Each of these is in the repository's codex/SPEC.md troubleshooting table or a code comment.")

    # 15 · conclusion
    s = prs.slides.add_slide(blank)
    rect(s, 0, 0, 13.333, 7.5, TEAL)
    text(s, 0.72, 0.7, 11.9, 0.35, "CONCLUSION", size=12, color=YELLOW, bold=True, spacing=200)
    text(s, 0.72, 1.15, 11.9, 1.7, [[("Deep Agents on your own data, safely", {"size": 34, "bold": True, "color": WHITE})],
                                   [("A LangChain Deep Agent plans, delegates and writes a grounded brief from Oracle AI Database; the database, the sandbox and the gate each "
                                     "decide what it can do, and none of them asks the agent to cooperate.", {"size": 15, "color": WHITE})]], line=1.15)
    steps = [("1  Run it", "github.com/fede-kamel/deep-agents-oracle-ai-database — hand codex/PROMPT.md to Codex."),
             ("2  Build on it", "langchain-oracle: create_deepagents_agent, ADB datastores, OracleEmbeddings, OracleVS, Oracle Text."),
             ("3  Keep it safe", "Row-level security for data, OpenShell for egress and keys, a gate for grounding.")]
    for i, (t, b) in enumerate(steps):
        x = 0.72 + i * 4.12
        rect(s, x, 3.85, 3.86, 1.9, RGBColor(0x03, 0x45, 0x5C), line=RGBColor(0x0B, 0x63, 0x80))
        rect(s, x, 3.85, 3.86, 0.07, YELLOW)
        text(s, x + 0.22, 4.05, 3.42, 2.0, [[(t, {"bold": True, "size": 16, "color": WHITE})], [(b, {"size": 12.5, "color": RGBColor(0xD8, 0xE6, 0xEA)})]], line=1.15)
    text(s, 0.72, 6.6, 11.9, 0.5, "Every claim on these slides has a transcript in the repository's evidence/ folder.", size=15, color=YELLOW, bold=True)
    text(s, 0.72, 7.08, 11.9, 0.3, FOOTER, size=8, color=RGBColor(0xC8, 0xD6, 0xDB))
    notes(s, "Close on the method: structural safety plus a grounding gate, reproducible from a spec.")

    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out))
    print("wrote", out, len(prs.slides._sldIdLst), "slides")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=ROOT / "deck" / "Deep-Agents-Oracle-AI-Database-FY26.pptx")
    a = ap.parse_args()
    build(a.template.expanduser(), a.out)
