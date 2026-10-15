"""The brief gate's offline checks (agent/verify.py): structure and citations."""

from agent import verify

PATIENT = "SYN-Y"


def good_brief() -> str:
    filler = " ".join(["word"] * 1200)
    parts = [f"## {section}\nText [SQL:lab_result] [{PATIENT}-NOTE-0003] [MEDQUAD-03600] [PMID-12345678].\n"
             for section in verify.SECTIONS if section != "Sources"]
    meds = "| Medication | Concern | What the chart shows | Source |\n|---|---|---|---|\n"
    body = "\n".join(parts).replace("## Medications to review\n", "## Medications to review\n" + meds)
    return f"{body}\n{filler}\n## Sources\n- [SQL:lab_result]\n"


def test_citations_split_grouped_ids():
    assert verify.citations("a [SQL:lab_result, SYN-Y-NOTE-0001] b [PMID-1]") == [
        "SQL:lab_result", "SYN-Y-NOTE-0001", "PMID-1"]


def test_a_complete_brief_passes():
    assert verify.problems(good_brief(), PATIENT) == []


def test_missing_section_is_named():
    text = good_brief().replace("## Questions for the visit", "## Something else")
    assert any("Questions for the visit" in p for p in verify.problems(text, PATIENT))


def test_another_patients_id_is_refused():
    text = good_brief().replace("## Snapshot\nText", "## Snapshot\nText [SYN-X-NOTE-0001]")
    assert any("another patient" in p and "SYN-X-NOTE-0001" in p for p in verify.problems(text, PATIENT))


def test_a_brief_without_research_citations_goes_back():
    text = good_brief().replace("[MEDQUAD-03600]", "").replace("[PMID-12345678]", "")
    assert any("reference or research" in p for p in verify.problems(text, PATIENT))


def test_header_is_a_system_stamp():
    stamped = verify.stamp_header("# Made-up title\nmodel text\n## Snapshot\nx", "Patient Y", PATIENT)
    assert stamped.startswith("# Pre-visit brief - Patient Y (SYN-Y)\n> SYNTHETIC RECORD")
    assert "Made-up title" not in stamped
