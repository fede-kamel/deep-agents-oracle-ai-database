#!/usr/bin/env python3
"""Figures for the deck, the README and the write-up.

Same visual system as the NeMo Relay and OpenShell figures: white canvas,
letter-spaced kicker, bold headline with an accent rule, flat panels with a
coloured edge, embedded brand logos, labelled connectors. Writes SVG next to
this file; `web/scripts/svg2png.mjs 2 docs/figures-src/*.svg` renders PNG.

    python3 docs/figures-src/gen.py
"""

from __future__ import annotations

import base64
import html
import os

OUT = os.path.dirname(os.path.abspath(__file__))
LOGO = os.path.join(OUT, "logos")
INK, SUB, MUT, LINE, PANEL, CARD = "#1F2430", "#6B7280", "#9AA1AC", "#D5D8DE", "#F7F8FA", "#FFFFFF"
GREEN = "#76B900"     # NVIDIA / OpenShell
RED = "#C74634"       # Oracle
NAVY = "#161F34"      # LangChain
SKY = "#3B8FD9"       # LangChain accent, readable on white
TEAL = "#2C7A7B"      # SQL and the relational chart
VIOLET = "#6B4FA0"    # research evidence
MOSS = "#5F7D4F"      # clinical reference
OCHRE = "#B07D1F"     # chart notes, secrets
OKG, BADR = "#2E8B57", "#C0392B"
FONT = "Helvetica Neue, Helvetica, Arial, sans-serif"
MONO = "SFMono-Regular, Menlo, Consolas, monospace"
ASPECT = {"openshell-lockup.png": 3.378, "nvidia.png": 3.888, "oracle.png": 4.762, "openai-mark.png": 1.0,
          "langchain.png": 4.72, "adb.png": 1.137, "genai.png": 1.084, "google.png": 2.957}


def esc(s):
    return html.escape(str(s), quote=True)


def b64(name):
    with open(os.path.join(LOGO, name), "rb") as f:
        return base64.b64encode(f.read()).decode()


class Fig:
    def __init__(self, w, h):
        self.w, self.h, self.e = w, h, []

    def logo(self, name, x, y, w):
        h = w / ASPECT[name]
        self.e.append(f'<image x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid meet" '
                      f'xlink:href="data:image/png;base64,{b64(name)}"/>')
        return h

    def rect(self, x, y, w, h, fill=CARD, stroke=LINE, sw=2, rx=16, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.e.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def panel(self, x, y, w, h, accent, fill=PANEL):
        self.rect(x, y, w, h, fill=fill, stroke=LINE, sw=3, rx=24)
        self.e.append(f'<rect x="{x}" y="{y}" width="14" height="{h}" rx="7" fill="{accent}"/>')

    def text(self, x, y, s, size, fill=INK, anchor="middle", weight="400", spacing=None, mono=False, italic=False):
        sp = f' letter-spacing="{spacing}"' if spacing else ""
        it = ' font-style="italic"' if italic else ""
        self.e.append(f'<text x="{x}" y="{y}" font-family="{MONO if mono else FONT}" font-size="{size}" fill="{fill}" '
                      f'text-anchor="{anchor}" font-weight="{weight}"{sp}{it}>{esc(s)}</text>')

    def card(self, x, y, w, h, title, lines=(), ts=25, tcol=INK, fill=CARD, stroke=LINE, mono_lines=False, lsize=20):
        self.rect(x, y, w, h, fill=fill, stroke=stroke)
        cy = y + (42 if lines else h / 2 + 9)
        self.text(x + w / 2, cy, title, ts, tcol, weight="700")
        for i, ln in enumerate(lines):
            self.text(x + w / 2, cy + 30 + i * 27, ln, lsize, SUB, mono=mono_lines)

    def chip(self, x, y, w, label, color, h=40, size=18, mono=True):
        self.rect(x, y, w, h, fill=CARD, stroke=color, sw=2, rx=10)
        self.text(x + w / 2, y + h / 2 + 6, label, size, color, weight="600", mono=mono)

    def badge(self, x, y, n, color=INK, r=17):
        self.e.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>')
        self.text(x, y + 6, n, int(r * 1.1), "#FFFFFF", weight="700")

    def arrow(self, x1, y1, x2, y2, color=SUB, sw=3.5, dash=None, label=None, lx=None, ly=None, lcol=None, lsize=20):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.e.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}" marker-end="url(#ar)"{d}/>')
        if label:
            self.text(lx if lx is not None else (x1 + x2) / 2, ly if ly is not None else (y1 + y2) / 2 - 12,
                      label, lsize, lcol or SUB, weight="600")

    def header(self, label, title, subtitle, accent=RED, left_logo=None):
        self.logo("oracle.png", self.w - 70 - 170, 38, 170)
        if left_logo:
            self.logo(left_logo[0], 70, 40, left_logo[1])
        self.text(self.w / 2, 70, label, 24, MUT, weight="600", spacing="6")
        self.text(self.w / 2, 132, title, 46, INK, weight="700")
        self.e.append(f'<rect x="{self.w / 2 - 160}" y="156" width="320" height="7" rx="3.5" fill="{accent}"/>')
        self.text(self.w / 2, 208, subtitle, 25, SUB)

    def legend(self, y, items):
        # Lay out by label length so long and short labels sit evenly.
        widths = [40 + len(label) * 11 for _, label in items]
        gap = (self.w - 160 - sum(widths)) / max(1, len(items) - 1)
        x = 80
        for (color, label), w in zip(items, widths):
            self.e.append(f'<circle cx="{x + 11}" cy="{y}" r="11" fill="{color}"/>')
            self.text(x + 34, y + 7, label, 21, INK, anchor="start")
            x += w + gap

    def save(self, name):
        defs = (f'<defs><marker id="ar" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="8" markerHeight="8" '
                f'orient="auto-start-reverse"><path d="M0,1 L9,5 L0,9 z" fill="{SUB}"/></marker></defs>')
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{self.w}" '
               f'height="{self.h}" viewBox="0 0 {self.w} {self.h}" font-family="{FONT}"><rect width="{self.w}" '
               f'height="{self.h}" fill="#FFFFFF"/>{defs}' + "".join(self.e) + "</svg>")
        with open(os.path.join(OUT, name), "w") as fh:
            fh.write(svg)
        print("wrote", name)


# ===================================================== Figure 1 · architecture
f = Fig(2000, 1400)
f.header("FIGURE 1 · ARCHITECTURE", "A Deep Agent on your own data, inside a sandbox",
         "one question in, a cited brief out: the agent plans and delegates; the database and the gateway decide what it can reach")
# entry points
f.card(60, 420, 270, 150, "Clinician", ["web app: pick a", "patient, ask"])
f.card(60, 620, 270, 150, "Codex", ["runs the spec:", "same scripts"])
f.logo("openai-mark.png", 82, 642, 36)
f.arrow(330, 495, 410, 560, color=INK, sw=3)
f.arrow(330, 695, 410, 610, color=INK, sw=3)
f.badge(368, 585, 1, INK)
# sandbox panel
f.panel(410, 300, 820, 760, GREEN)
f.logo("openshell-lockup.png", 446, 326, 250)
f.logo("nvidia.png", 1040, 336, 160)
f.text(820, 420, "sandbox: one patient, one run", 24, GREEN, weight="700")
f.rect(450, 450, 740, 430, fill="#FFFFFF", stroke=NAVY, sw=2.5, rx=18)
f.logo("langchain.png", 470, 466, 180)
f.text(1170, 498, "Deep Agent · langchain-oci", 22, NAVY, anchor="end", weight="700")
f.card(480, 520, 680, 92, "Lead: plan · delegate · return PreVisitBrief", lines=(), ts=22, tcol=NAVY, stroke=NAVY)
specs = [("Chart analyst", "SQL + notes", TEAL), ("Guideline", "MedQuAD", MOSS), ("Evidence", "PubMed", VIOLET), ("Care coord.", "proposes actions", OCHRE)]
for i, (t, s, c) in enumerate(specs):
    x = 480 + i * 172
    f.rect(x, 650, 160, 110, stroke=c, sw=2.5)
    f.text(x + 80, 692, t, 20, c, weight="700")
    f.text(x + 80, 724, s, 16, SUB)
    f.arrow(820, 612, x + 80, 650, color=MUT, sw=2.5)
f.text(820, 800, "memory: /memories/ in OracleStore · checkpoints in OracleSaver", 19, SUB)
f.text(820, 830, "gate: accepts the brief only if every cited id exists", 19, SUB)
f.rect(450, 905, 360, 120, fill="#FDF6E3", stroke=OCHRE, sw=2.5)
f.text(630, 945, "GenAI key", 21, OCHRE, weight="700")
f.text(630, 976, "a placeholder here;", 18, SUB)
f.text(630, 1002, "the gateway holds the key", 18, SUB)
f.rect(830, 905, 360, 120, fill="#EAF3F3", stroke=TEAL, sw=2.5)
f.text(1010, 945, "DA_AGENT_<patient>", 21, TEAL, weight="700", mono=True)
f.text(1010, 976, "SELECT only, uploaded 0600,", 18, SUB)
f.text(1010, 1002, "deleted after it is read", 18, SUB)
# Oracle panel
f.panel(1290, 300, 650, 760, RED)
f.logo("oracle.png", 1326, 330, 170)
f.text(1915, 360, "Oracle AI Database 26ai", 22, RED, anchor="end", weight="700")
f.card(1330, 400, 580, 150, "Relational chart", ["patient · medication · lab_result · encounter", "clinical_note · referral · … (Alembic 0001)"], ts=23, lsize=18)
f.card(1330, 570, 580, 150, "Vector stores", ["PATIENT_NOTE_VEC · CLINICAL_REFERENCE", "RESEARCH_EVIDENCE · Oracle Text indexes"], ts=23, lsize=18)
f.card(1330, 740, 580, 130, "In-database embeddings", ["ONNX all-MiniLM-L12-v2, 384 dimensions"], ts=23, lsize=18)
f.card(1330, 890, 580, 140, "Row-level security (VPD)", ["agent X reads SYN-X, proposes for SYN-X;", "approval and execution belong to the clinician"], ts=23, tcol=RED, stroke=RED, lsize=17)
f.arrow(1230, 640, 1290, 640, color=TEAL, sw=4)
f.text(1260, 596, "SQL", 16, TEAL, weight="700")
f.text(1260, 616, "vector", 16, TEAL, weight="700")
f.badge(1260, 668, 2, TEAL)
# GenAI strip
f.panel(410, 1100, 1530, 170, RED)
f.logo("genai.png", 450, 1130, 92)
f.text(570, 1170, "OCI Generative AI · OpenAI-compatible endpoint", 25, INK, anchor="start", weight="700")
f.text(570, 1206, "lead openai.gpt-5.5 · specialists google.gemini-2.5-flash · the proxy swaps the placeholder in transit", 20, SUB, anchor="start")
f.text(570, 1238, "nothing else is reachable: no rule, no connection", 20, BADR, anchor="start", weight="600")
f.arrow(820, 1060, 820, 1100, color=GREEN, sw=4)
f.badge(860, 1080, 3, RED)
f.legend(1340, [(GREEN, "NVIDIA OpenShell: isolation, egress, keys"), (NAVY, "LangChain Deep Agents"),
                (RED, "Oracle: database and models"), (OCHRE, "credentials")])
f.save("figure1-architecture.svg")

# ===================================================== Figure 2 · the deep agent
f = Fig(2000, 1240)
f.header("FIGURE 2 · THE DEEP AGENT", "Plan, delegate, retrieve, write",
         "the lead holds no data tools: every fact reaches the brief through a specialist that queried for it", accent=NAVY,
         left_logo=("langchain.png", 230))
cols = [
    ("1", "Plan", NAVY, ["write_todos", "4-5 items, updated", "as work finishes"]),
    ("2", "Delegate", NAVY, ["task → chart-analyst", "then both researchers", "in parallel"]),
    ("3", "Retrieve", TEAL, ["query_chart (SELECT)", "search_<store> (hybrid:", "vector + Oracle Text)"]),
    ("4", "Return", RED, ["PreVisitBrief", "structured output:", "the schema fixes the shape"]),
    ("5", "Gate", OKG, ["sections, length", "every cited id looked", "up in the database"]),
]
x = 80
for n, title, color, lines in cols:
    f.panel(x, 290, 336, 360, color)
    f.badge(x + 60, 350, n, color, r=20)
    f.text(x + 186, 362, title, 32, INK, weight="700")
    for i, ln in enumerate(lines):
        f.text(x + 180, 440 + i * 40, ln, 21, SUB, mono=(i == 0))
    if x < 1400:
        f.arrow(x + 336, 470, x + 370, 470, color=MUT, sw=3)
    x += 370
f.text(1000, 712, "SPECIALISTS, EACH BOUND TO ITS OWN STORE", 22, MUT, weight="700", spacing="4")
lanes = [
    ("chart-analyst", TEAL, "relational chart + notes", ["query_chart: trends, REGR_SLOPE,", "meds, referrals, benchmark", "SELECT note_ref … (0005)", "search_patient_notes"]),
    ("guideline-researcher", MOSS, "NIH reference", ["search_clinical_reference", "five or more searches", "6-10 passages with ids", "says when not covered"]),
    ("evidence-researcher", VIOLET, "PubMed abstracts", ["search_research_evidence", "five or more searches", "6-10 abstracts with ids", "skips weak matches"]),
    ("care-coordinator", OCHRE, "proposes, never executes", ["list_care_actions first", "propose_lab_request", "draft_patient_message", "propose_follow_up · max 5"]),
]
x = 80
for name, color, sub, lines in lanes:
    f.rect(x, 750, 440, 330, stroke=color, sw=3, rx=20)
    f.text(x + 220, 800, name, 23, color, weight="700", mono=True)
    f.text(x + 220, 836, sub, 19, SUB)
    for i, ln in enumerate(lines):
        f.text(x + 220, 900 + i * 40, ln, 18, INK, mono=(i == 0))
    x += 465
f.text(1000, 1140, "GPT-5.5 plans and writes; Gemini 2.5 Flash runs the four specialists. Memory loads at the start; every step is checkpointed in Oracle.", 22, INK, weight="600")
f.text(1000, 1180, "create_deepagents_agent · OracleSaver · OracleStore + StoreBackend · memory= · permissions= · ToolStrategy(PreVisitBrief)", 19, MUT, mono=True)
f.save("figure2-deep-agent.svg")

# ===================================================== Figure 3 · the data layer
f = Fig(2000, 1260)
f.header("FIGURE 3 · THE DATA", "One system of record: relational, vector, and the model",
         "Alembic builds the chart; the notes are embedded from those rows inside Oracle AI Database", accent=TEAL)
migs = [("0001", "clinical schema", "10 tables, CHECK synthetic"), ("0002", "vector stores", "OracleVS shape, 384-d"),
        ("0003", "cohort benchmark", "aggregates, no ids"), ("0004", "row-level security", "VPD + SELECT grants"),
        ("0005", "citable note ids", "note_ref = vector id")]
x = 80
for rev, title, sub in migs:
    f.rect(x, 280, 336, 120, stroke=TEAL, sw=2.5)
    f.text(x + 24, 330, rev, 24, TEAL, anchor="start", weight="700", mono=True)
    f.text(x + 104, 330, title, 21, INK, anchor="start", weight="700")
    f.text(x + 104, 366, sub, 18, SUB, anchor="start")
    if x < 1500:
        f.arrow(x + 336, 340, x + 366, 340, color=MUT, sw=3)
    x += 366
f.text(1000, 440, "alembic upgrade head  ·  python db/seed.py  ·  python db/embed.py", 22, MUT, mono=True)
f.panel(80, 480, 780, 560, TEAL)
f.text(470, 540, "RELATIONAL CHART (DA_OWNER)", 22, TEAL, weight="700", spacing="3")
tables = ["patient", "condition", "allergy", "medication", "encounter", "clinical_note", "lab_result", "vital_sign", "referral", "appointment"]
for i, t in enumerate(tables):
    cx, cy = 130 + (i % 2) * 350, 580 + (i // 2) * 74
    f.chip(cx, cy, 330, t, TEAL, h=54, size=20)
f.text(470, 990, "3 featured patients · 300 background · 1,677 lab rows", 20, SUB)
f.panel(1140, 480, 780, 560, RED)
f.text(1530, 540, "VECTOR STORES (IN-DATABASE EMBEDDINGS)", 22, RED, weight="700", spacing="3")
vec = [("PATIENT_NOTE_VEC", "19 notes → 19 chunks", OCHRE), ("CLINICAL_REFERENCE", "147 MedQuAD → 344 chunks", MOSS),
       ("RESEARCH_EVIDENCE", "360 PubMedQA → 955 chunks", VIOLET)]
for i, (t, s, c) in enumerate(vec):
    y = 580 + i * 120
    f.rect(1190, y, 680, 100, stroke=c, sw=2.5)
    f.text(1220, y + 44, t, 23, c, anchor="start", weight="700", mono=True)
    f.text(1220, y + 78, s, 19, SUB, anchor="start")
f.card(1190, 950, 680, 70, "OracleTextSplitter · OracleEmbeddings(MINILM_L12) · Oracle Text", ts=18, tcol=INK)
f.arrow(810, 754, 1190, 630, color=OCHRE, sw=4)
f.text(1000, 700, "OracleAutonomous-", 17, OCHRE, weight="700", mono=True)
f.text(1000, 722, "DatabaseLoader", 17, OCHRE, weight="700", mono=True)
f.text(1000, 1100, "Text never leaves the database to be vectorised: the splitter and the ONNX model run where the rows live.", 23, INK, weight="600")
f.text(1000, 1140, "Public reference text: MedQuAD (NIH, CC BY 4.0), PubMedQA (MIT). Every patient record is synthetic.", 20, SUB)
f.legend(1205, [(TEAL, "relational chart and SQL"), (OCHRE, "chart notes"), (MOSS, "clinical reference"), (VIOLET, "research evidence")])
f.save("figure3-data.svg")

# ===================================================== Figure 4 · safety net
f = Fig(2000, 1300)
f.header("FIGURE 4 · THE SAFETY NET", "Four layers, each measured, none asks the agent to behave",
         "the sandbox, the database, the guards and the runner each refuse on their own", accent=GREEN,
         left_logo=("openshell-lockup.png", 230))
layers = [
    ("SANDBOX EGRESS", GREEN, [("ALLOWED", "OCI GenAI chat completion → HTTP 200"), ("ALLOWED", "database listener :1521, python3.12 only"),
                               ("REFUSED", "example.com → Errno 13 at connect"), ("REFUSED", "Object Storage API → Errno 13"),
                               ("REFUSED", "pypi.org → Errno 13"), ("REFUSED", "PUT on the GenAI host → 403")]),
    ("DATABASE", RED, [("ALLOWED", "agent X: SELECT + propose, SYN-X only"), ("REFUSED", "rows of SYN-Y → 0 rows (VPD)"),
                       ("REFUSED", "propose for SYN-Y → ORA-28115"), ("REFUSED", "approve (UPDATE) → ORA-41900"),
                       ("REFUSED", "execute the procedure → ORA-06550"), ("REFUSED", "patient id without SYN- → CHECK")]),
]
x = 80
for title, color, rows in layers:
    f.panel(x, 290, 900, 560, color)
    f.text(x + 450, 350, title, 23, color, weight="700", spacing="4")
    for i, (verdict, what) in enumerate(rows):
        y = 380 + i * 75
        f.rect(x + 40, y, 820, 62, rx=12)
        ok = verdict == "ALLOWED"
        f.rect(x + 56, y + 13, 132, 36, fill="#EDF6E8" if ok else "#FBEAE7", stroke=OKG if ok else BADR, rx=8)
        f.text(x + 122, y + 38, verdict, 18, OKG if ok else BADR, weight="700", mono=True)
        f.text(x + 212, y + 39, what, 21, INK, anchor="start")
    x += 940
f.panel(80, 890, 900, 270, OCHRE)
f.text(530, 948, "INPUT GUARD (PIIMiddleware)", 23, OCHRE, weight="700", spacing="4")
for i, ln in enumerate(["blocks: SSN · phone · email · MRN · date of birth", "blocks: any SYN- id but this run's patient", "redacts the same shapes in model output"]):
    f.text(530, 1000 + i * 42, ln, 21, INK)
f.panel(1020, 890, 900, 270, NAVY)
f.text(1470, 948, "BRIEF GATE (the runner)", 23, NAVY, weight="700", spacing="4")
for i, ln in enumerate(["sections, length, the medication table", "≥ 15 citations, of every kind", "every cited id looked up as the patient's user"]):
    f.text(1470, 1000 + i * 42, ln, 21, INK)
f.text(1000, 1215, "Measured: scripts/safety_probe.sh 7/7 · scripts/verify.py --rls-only 19/19 · guard unit checks 7/7", 21, MUT, mono=True)
f.save("figure4-safety-net.svg")

# ===================================================== Figure 5 · one run, beat by beat
f = Fig(2000, 1380)
f.header("FIGURE 5 · ONE RUN, BEAT BY BEAT", "From a question to a verified brief",
         "the web app and Codex call the same script; the console in the app is the gateway's own log", accent=RED)
actors = [("Web app / Codex", INK), ("scripts/sandbox.sh", INK), ("OpenShell gateway", GREEN), ("Sandbox · Deep Agent", NAVY),
          ("Oracle AI Database", RED), ("OCI Generative AI", RED)]
xs = [170 + i * 332 for i in range(len(actors))]
for (name, c), x in zip(actors, xs):
    f.rect(x - 140, 260, 280, 64, stroke=c, sw=3, rx=12)
    f.text(x, 300, name, 21, c, weight="700")
    f.e.append(f'<line x1="{x}" y1="324" x2="{x}" y2="1270" stroke="{LINE}" stroke-width="3" stroke-dasharray="6 8"/>')
beats = [
    (0, 1, "run Y", INK), (1, 2, "sandbox create --provider --policy", GREEN), (2, 3, "start: placeholder key in env", GREEN),
    (1, 3, "upload code + 0600 db.env", INK), (1, 2, "wait for the first policy reload", MUT), (1, 3, "exec python -m agent.run", INK),
    (3, 5, "plan: write_todos (GPT-5.5)", NAVY), (3, 4, "chart-analyst: SELECT … VPD filters to SYN-Y", TEAL),
    (3, 5, "researchers: Gemini Flash", VIOLET), (3, 4, "hybrid search: vector + Oracle Text", VIOLET),
    (3, 5, "PreVisitBrief (structured)", NAVY), (3, 4, "gate: every cited id exists?", OKG),
    (3, 0, "events + brief (stdout) · console (stderr)", INK), (1, 2, "sandbox delete", GREEN),
]
y = 380
for a, b, label, c in beats:
    x1, x2 = xs[a], xs[b]
    off = 12 if x2 > x1 else -12
    f.arrow(x1 + off, y, x2 - off, y, color=c, sw=3)
    f.text((x1 + x2) / 2, y - 12, label, 18, c, weight="600")
    y += 63
f.text(1000, 1320, "Every network hop above appears in the console as NET:OPEN or HTTP:POST with ALLOWED and the policy that allowed it.", 22, INK, weight="600")
f.save("figure5-sequence.svg")

# ===================================================== Figure 6 · built and run by Codex
f = Fig(2000, 1060)
f.header("FIGURE 6 · BUILT AND RUN BY CODEX", "A spec with checkpoints, two operator steps, no secret in the agent",
         "the coding agent learns the command lines once; the operator types only the two secrets", accent=VIOLET)
f.logo("openai-mark.png", 70, 40, 56)
steps = [("preflight", "read-only", INK), ("db-admin", "operator: ADMIN", OCHRE), ("provider", "operator: key", OCHRE),
         ("setup-data", "migrate · seed · embed", TEAL), ("probe", "7/7 boundary", GREEN), ("briefs", "X · Y · Z", NAVY),
         ("verify", "ids · RLS", OKG), ("report", "SPEC §9", INK)]
x = 70
for i, (t, s, c) in enumerate(steps):
    f.rect(x, 300, 214, 140, stroke=c, sw=3, rx=16)
    f.badge(x + 34, 334, i + 1, c, r=16)
    f.text(x + 118, 384, t, 23, c, weight="700", mono=True)
    f.text(x + 107, 418, s, 17, SUB)
    if i < len(steps) - 1:
        f.arrow(x + 214, 370, x + 236, 370, color=MUT, sw=3)
    x += 236
f.panel(80, 500, 900, 420, OCHRE)
f.text(530, 560, "THE TWO OPERATOR STEPS", 22, OCHRE, weight="700", spacing="4")
for i, ln in enumerate(["scripts/operator/db-admin.sh", "  read -rs ADMIN → users, model,", "  passwords to 0600 files",
                        "scripts/operator/genai-provider.sh", "  read -rs key → the gateway", "reply 'done'; never paste output"]):
    f.text(150 + (40 if ln.startswith("  ") else 0), 620 + i * 46, ln.strip(), 22, INK, anchor="start", mono=(not ln.startswith("reply")))
f.panel(1020, 500, 900, 420, VIOLET)
f.text(1470, 560, "WHAT CODEX RUNS, AND NEVER DOES", 22, VIOLET, weight="700", spacing="4")
for i, ln in enumerate(["runs: preflight, setup-data, sandbox.sh,", "safety_probe, verify, teardown", "",
                        "never: reads a secret, runs ADMIN,", "touches objects the demo did not make,", "edits a script to make a check pass"]):
    f.text(1470, 620 + i * 46, ln, 22, INK)
f.text(1000, 990, "codex/SPEC.md · codex/PROMPT.md · AGENTS.md — the same method as the OpenShell kill-switch demo", 21, MUT, mono=True)
f.save("figure6-codex.svg")

# ===================================================== Figure 7 · the grounding gate
f = Fig(2000, 1120)
f.header("FIGURE 7 · THE GROUNDING GATE", "A brief is accepted only when its sources exist",
         "measured on a real run: the model cited a reference id from memory; the gate caught it before the clinician saw it", accent=OKG)
f.panel(80, 290, 560, 640, NAVY)
f.text(360, 350, "DRAFT FROM THE LEAD", 22, NAVY, weight="700", spacing="4")
for i, (cid, ok) in enumerate([("SQL:lab_result", True), ("SYN-Y-NOTE-0011", True), ("SYN-Y-NOTE-0012", True), ("MEDQUAD-01695", True),
                               ("PMID-19065446", True), ("MEDQUAD-00001", False)]):
    f.chip(130, 390 + i * 84, 460, cid, OKG if ok else BADR, h=62, size=22)
f.arrow(640, 610, 760, 610, color=INK, sw=4)
f.panel(760, 290, 520, 640, OKG)
f.text(1020, 350, "LOOKUP AS DA_AGENT_Y", 22, OKG, weight="700", spacing="4")
for i, ln in enumerate(["SELECT COUNT(*)", "FROM <store>", "WHERE JSON_VALUE(", "  metadata, '$.id')", "  = :cited_id"]):
    f.text(820, 420 + i * 44, ln, 22, INK, anchor="start", mono=True)
f.text(1020, 700, "row-level security applies:", 21, SUB)
f.text(1020, 732, "another patient's note id is", 21, SUB)
f.text(1020, 764, "as unknown as an invented one", 21, SUB)
f.arrow(1280, 470, 1400, 420, color=OKG, sw=4, label="all exist", lx=1340, ly=410, lcol=OKG)
f.arrow(1280, 750, 1400, 800, color=BADR, sw=4, label="one missing", lx=1340, ly=822, lcol=BADR)
f.card(1400, 330, 520, 190, "Accepted", ["rendered from PreVisitBrief", "verified · 168 citations (Y, second brief)"], tcol=OKG, stroke=OKG)
f.card(1400, 680, 520, 230, "Sent back", ["'MEDQUAD-00001 does not exist.", "Cite only ids a search returned;", "drop or re-source the claim.'"], tcol=BADR, stroke=BADR)
f.text(1000, 1000, "The real heart-failure reference rows are MEDQUAD-036xx. The draft's MEDQUAD-00001 never appeared in any tool result.", 22, INK, weight="600")
f.text(1000, 1045, "agent/verify.py · agent/run.py (two repair turns at most) · scripts/verify.py repeats the check afterwards", 19, MUT, mono=True)
f.save("figure7-grounding-gate.svg")


# ===================================================== Figure 8 · the workflow
f = Fig(2000, 1180)
f.header("FIGURE 8 · FROM BRIEF TO ACTION", "The agent proposes, the clinician approves, the database executes",
         "three identities, three powers; every transition audited in care_action_event", accent=OCHRE)
cols = [
    ("1", "Propose", OCHRE, "DA_AGENT_<P> · in the sandbox", ["INSERT into care_action only", "trigger forces status = proposed", "VPD update_check: own patient", "no UPDATE, no EXECUTE"]),
    ("2", "Approve", TEAL, "DA_CLINICIAN · the web app", ["reviews each card, may edit", "approve or reject", "EXECUTE on one procedure", "no table writes of its own"]),
    ("3", "Execute", RED, "DECIDE_CARE_ACTION · definer rights", ["lab_request → lab_order", "patient_message → portal outbox", "follow_up → appointment", "one transaction, then audited"]),
]
x = 80
for n, t, c, who, lines in cols:
    f.panel(x, 290, 580, 520, c)
    f.badge(x + 66, 352, n, c, r=22)
    f.text(x + 110, 365, t, 34, INK, anchor="start", weight="700")
    f.text(x + 310, 420, who, 20, c, weight="700", mono=True)
    for i, ln in enumerate(lines):
        f.rect(x + 50, 460 + i * 80, 500, 62, rx=12)
        f.text(x + 300, 499 + i * 80, ln, 20, INK)
    if x < 1300:
        f.arrow(x + 580, 550, x + 620, 550, color=MUT, sw=4)
    x += 620
f.panel(80, 860, 1840, 200, NAVY)
f.text(1000, 915, "MEASURED ON A REAL RUN (PATIENT Y)", 22, NAVY, weight="700", spacing="4")
f.text(1000, 965, "#26 lab request → approved → executed: lab_order 5 (basic metabolic panel, magnesium)", 21, INK, mono=True)
f.text(1000, 1003, "#25 follow-up → executed: appointment requested within 7 days · #27 patient message → rejected", 21, INK, mono=True)
f.text(1000, 1041, "the second brief, from memory: no repeat of #26, a BNP instead, the follow-up escalated, a new message", 20, SUB)
f.text(1000, 1120, "scripts/verify.py --rls-only proves each refusal: ORA-28115 · ORA-41900 · ORA-06550, and the audit trail proposed > approved > executed", 19, MUT, mono=True)
f.save("figure8-workflow.svg")

# ===================================================== Figure 9 · durable state
f = Fig(2000, 1080)
f.header("FIGURE 9 · STATE AND MEMORY ON ORACLE", "The agent remembers, and every step is a checkpoint",
         "langgraph-oracledb, in the agent user's own schema; the chart stays read-only", accent=TEAL, left_logo=("langchain.png", 230))
items = [
    ("checkpointer=", "OracleSaver", TEAL, ["every super-step of the graph", "thread_id brief-<P>-<run>", "~130 checkpoints per brief", "repairs resume from state"]),
    ("store=", "OracleStore", RED, ["namespace (patient, SYN-<P>)", "IVF vector index", "in-database embeddings", "semantic search over memory"]),
    ("backend= / memory=", "StoreBackend", NAVY, ["/memories/ → OracleStore", "patient-history.md loaded", "into the system prompt", "agent: read only (permissions)"]),
]
x = 80
for k, cls, c, lines in items:
    f.panel(x, 290, 580, 560, c)
    f.text(x + 310, 360, k, 22, MUT, weight="700", mono=True)
    f.text(x + 310, 412, cls, 34, c, weight="700", mono=True)
    for i, ln in enumerate(lines):
        f.rect(x + 50, 460 + i * 86, 500, 66, rx=12)
        f.text(x + 300, 501 + i * 86, ln, 20, INK)
    x += 620
f.text(1000, 920, "Who writes memory: the runner records each accepted brief; the web app records each clinician decision.", 22, INK, weight="600")
f.text(1000, 962, "The model reads it and builds on it; it cannot write it, so memory holds facts the system can stand behind.", 21, SUB)
f.text(1000, 1020, "agent/memory.py · DA_AGENT_<P>: CREATE TABLE, 64 MB quota, own schema only", 19, MUT, mono=True)
f.save("figure9-memory.svg")
