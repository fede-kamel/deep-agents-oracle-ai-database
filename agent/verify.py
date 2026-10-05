"""Structural and grounding checks on a written brief.

The runner applies these before it accepts /brief.md, and hands the problems
back to the lead agent when a check fails. `scripts/verify.py` repeats them
against the database afterwards and also confirms that every cited note and
reference id exists.
"""

from __future__ import annotations

import re

SECTIONS = [
    "Snapshot",
    "What changed",
    "Medications to review",
    "Overdue monitoring and open care gaps",
    "What the reference and research say",
    "Insights for the clinician: next steps",
    "Proposed actions (awaiting clinician approval)",
    "Questions for the visit",
    "Sources",
]
BANNER = "SYNTHETIC RECORD"
BANNER_LINE = "SYNTHETIC RECORD - invented for a demo, not a real patient. For clinician review; not medical advice."
CITATION = re.compile(r"\[([A-Z][A-Za-z0-9:_#,\- ]+)\]")
MIN_CITATIONS = 15
MIN_WORDS = 1100


def citations(text: str) -> list[str]:
    ids: list[str] = []
    for group in CITATION.findall(text):
        ids.extend(part.strip() for part in group.split(",") if part.strip())
    return ids


def stamp_header(text: str, display_name: str, patient_id: str) -> str:
    """Replace whatever precedes the first section with the canonical title and
    banner: the synthetic label is a system stamp, not model output."""
    head = f"# Pre-visit brief - {display_name} ({patient_id})\n> {BANNER_LINE}\n\n"
    at = text.find("## ")
    return head + (text[at:] if at >= 0 else text)


def problems(text: str, patient_id: str) -> list[str]:
    found: list[str] = []
    headings = {h.strip().lower() for h in re.findall(r"^##\s+(.+)$", text, re.M)}
    missing = [s for s in SECTIONS if s.lower() not in headings]
    if missing:
        found.append("Missing '## ' sections: " + ", ".join(missing) + ".")
    body = text.split("## Sources")[0]
    ids = citations(body)
    if len(ids) < MIN_CITATIONS:
        found.append(f"Only {len(ids)} citations in the body; every factual sentence needs one (at least {MIN_CITATIONS}).")
    words = len(re.findall(r"\b\w+\b", CITATION.sub("", body)))
    if words < MIN_WORDS:
        found.append(f"The body is {words} words; expand it to 1,200-1,800 words with the detail each section asks for.")
    if "|" not in text.split("## Medications to review")[-1].split("##")[0]:
        found.append("'Medications to review' needs the table | Medication | Concern | What the chart shows | Source |.")
    if not any(i.startswith("SQL:") for i in ids):
        found.append("No [SQL:<table>] citation: chart facts must cite the table they came from.")
    if not any(i.startswith(f"{patient_id}-NOTE-") or i.startswith("SQL:clinical_note") for i in ids):
        found.append(f"No chart-note citation ([{patient_id}-NOTE-nnnn] or [SQL:clinical_note]).")
    if not any(i.startswith(("MEDQUAD-", "PMID-")) for i in ids):
        found.append("No reference or research citation: delegate to the guideline-researcher and the evidence-researcher and cite their ids.")
    foreign = sorted({i for i in ids if i.startswith("SYN-") and not i.startswith(patient_id + "-")})
    if foreign:
        found.append("Citations name another patient: " + ", ".join(foreign) + ". Remove them.")
    return found


STORES = {"SYN-": "PATIENT_NOTE_VEC", "MEDQUAD-": "CLINICAL_REFERENCE", "PMID-": "RESEARCH_EVIDENCE"}


def unresolved(conn, ids: list[str], chart_tables: list[str]) -> list[str]:
    """Cited ids that do not exist, looked up as the patient's own user, so an
    id from another patient's chart is as unknown as an invented one."""
    cur = conn.cursor()
    missing = []
    for cid in sorted(set(ids)):
        base = cid.split("#")[0]
        if base.startswith("SQL:"):
            ok = base[4:].lower() in chart_tables
        else:
            table = next((t for prefix, t in STORES.items() if base.startswith(prefix)), None)
            ok = False
            if table:
                cur.execute(f"SELECT COUNT(*) FROM {table} WHERE JSON_VALUE(metadata, '$.id') = :i", i=base)
                ok = cur.fetchone()[0] > 0
        if not ok:
            missing.append(cid)
    return missing
