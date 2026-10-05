"""The brief as structured output.

The lead agent returns a `PreVisitBrief` (the Deep Agent's `response_format`)
instead of free-form Markdown, so the structure is guaranteed by the schema and
the runner renders the document. Field descriptions carry the writing brief;
the verifier still checks length and grounding on the rendered text.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

CITE = "Citations in square brackets at the end, e.g. [SQL:lab_result] or [SYN-X-NOTE-0003]."


class Change(BaseModel):
    headline: str = Field(description="Short label, e.g. 'Kidney function'.")
    detail: str = Field(description="Two to four sentences with dated values, the rate of change, the cohort comparison when known, and the events behind it. " + CITE)


class MedicationRow(BaseModel):
    medication: str = Field(description="Name and dose as charted.")
    concern: str = Field(description="The concern in a few words, e.g. 'hypoglycaemia risk as eGFR falls'.")
    chart_evidence: str = Field(description="What the chart shows, one or two sentences.")
    sources: str = Field(description="The citation ids for this row, e.g. '[SQL:medication] [SYN-X-NOTE-0003]'.")


class Gap(BaseModel):
    gap: str = Field(description="What is missing or unresolved.")
    detail: str = Field(description="Since when and why it matters, one or two sentences. " + CITE)


class Finding(BaseModel):
    finding: str = Field(description="What the source says, two or three sentences in your own words with a short quote if useful. " + CITE)
    relevance: str = Field(description="One sentence: why it matters for this patient.")


class NextStep(BaseModel):
    step: str = Field(description="What the clinician should do, in a few words, e.g. 'Stop the potassium supplement'.")
    why: str = Field(description="One or two sentences of reasoning. " + CITE)


class ProposedAction(BaseModel):
    action_id: int = Field(description="The care action id the care coordinator reported.")
    kind: str = Field(description="lab_request, patient_message, follow_up, or medication_change.")
    summary: str = Field(description="One line: what it does and why; for a medication change, say it awaits the doctor (policy CP-02).")


class Source(BaseModel):
    id: str = Field(description="The cited id exactly as used, e.g. 'PMID-12345678' or 'SQL:lab_result'.")
    title: str = Field(description="The source's title, or the table's content for SQL ids.")


class PreVisitBrief(BaseModel):
    """The pre-visit brief for one synthetic patient: complete, concise, and grounded."""

    snapshot: str = Field(description="Three or four sentences: who the patient is, why they are coming, the two or three issues that matter most. " + CITE)
    what_changed: list[Change] = Field(description="Three to five changes, most important first.")
    medications_to_review: list[MedicationRow] = Field(description="Every medication worth discussing, one row each (usually three to six).")
    interactions_note: str = Field(description="One or two sentences on interactions or duplications across the rows. " + CITE)
    care_gaps: list[Gap] = Field(description="Every overdue item or open care gap (usually two to five).")
    clinical_reference: list[Finding] = Field(description="Three to five findings from the guideline-researcher's MEDQUAD ids.")
    research_evidence: list[Finding] = Field(description="Three to five findings from the evidence-researcher's PMID ids.")
    questions_for_visit: list[str] = Field(description="Five to seven specific, answerable questions for the clinician to raise.")
    next_steps: list[NextStep] = Field(description="Insights for the clinician: four to six next steps, most important first.")
    proposed_actions: list[ProposedAction] = Field(description="The care actions the care coordinator proposed, awaiting approval.")
    sources: list[Source] = Field(description="Every id cited anywhere above, once each.")


def render(brief: PreVisitBrief, display_name: str, patient_id: str, banner: str) -> str:
    out = [f"# Pre-visit brief - {display_name} ({patient_id})", f"> {banner}", "", "## Snapshot", brief.snapshot, ""]
    out += ["## What changed"] + [f"- **{c.headline}.** {c.detail}" for c in brief.what_changed] + [""]
    out += [
        "## Medications to review",
        "| Medication | Concern | What the chart shows | Source |",
        "|---|---|---|---|",
    ]
    out += [
        f"| {r.medication} | {r.concern} | {r.chart_evidence} | {r.sources} |".replace("\n", " ")
        for r in brief.medications_to_review
    ]
    out += ["", brief.interactions_note, ""]
    out += ["## Overdue monitoring and open care gaps"] + [f"- **{g.gap}.** {g.detail}" for g in brief.care_gaps] + [""]
    out += ["## What the reference and research say", "### Clinical reference"]
    out += [f"- {f.finding} *{f.relevance}*" for f in brief.clinical_reference] + ["", "### Research evidence"]
    out += [f"- {f.finding} *{f.relevance}*" for f in brief.research_evidence] + [""]
    out += ["## Insights for the clinician: next steps"]
    out += [f"{i}. **{n.step}.** {n.why}" for i, n in enumerate(brief.next_steps, 1)] + [""]
    out += ["## Proposed actions (awaiting clinician approval)"]
    out += [f"- **#{a.action_id} · {a.kind.replace('_', ' ')}.** {a.summary}" for a in brief.proposed_actions] + [""]
    out += ["## Questions for the visit"] + [f"{i}. {q}" for i, q in enumerate(brief.questions_for_visit, 1)] + [""]
    out += ["## Sources"] + [f"- [{s.id.strip('[]')}] {s.title}" for s in brief.sources]
    return "\n".join(out) + "\n"
