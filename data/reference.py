"""Public medical reference corpus for the demo.

Two openly licensed Hugging Face datasets, filtered to the topics the three
synthetic patients need:

- MedQuAD (NIH consumer-health question and answer pairs, CC BY 4.0),
  mirrored as `keivalya/MedQuad-MedicalQnADataset`.
- PubMedQA (PubMed abstracts with research questions, MIT),
  `qiaojin/PubMedQA`, subset `pqa_unlabeled`.

Neither contains patient records. The selection is deterministic: the first N
matches per topic in dataset order, so every run ingests the same documents.
"""

from __future__ import annotations

import re

TOPICS = {
    "diabetes-kidney": r"diabet\w* (kidney|nephropath)|chronic kidney|albuminuria|metformin|sglt2|hypoglyc|diabetic retinopath|nsaid\w* .*kidney|kidney .*nsaid",
    "heart-failure": r"heart failure|cardiac failure|readmission|hyperkal|spironolact|loop diuretic|furosemide|medication adherence",
    "copd-falls": r"\bcopd\b|chronic obstructive|inhaler|anticholinergic|polypharmacy|\bfalls?\b.*(elderly|older)|(elderly|older).*\bfalls?\b|beers criteria|zolpidem|diphenhydramine|osteopor",
}
MEDQUAD_PER_TOPIC = 60
PUBMED_PER_TOPIC = 120


def _topic(text: str) -> str | None:
    for name, pattern in TOPICS.items():
        if re.search(pattern, text, re.I):
            return name
    return None


def medquad_documents() -> list[dict]:
    from datasets import load_dataset

    rows = load_dataset("keivalya/MedQuad-MedicalQnADataset", split="train")
    counts = {t: 0 for t in TOPICS}
    docs: list[dict] = []
    for i, row in enumerate(rows):
        topic = _topic(row["Question"])
        if not topic or counts[topic] >= MEDQUAD_PER_TOPIC or not row["Answer"]:
            continue
        counts[topic] += 1
        docs.append(
            {
                "id": f"MEDQUAD-{i:05d}",
                "title": row["Question"][:160],
                "content": f"Question: {row['Question']}\nAnswer: {row['Answer'][:4000]}",
                "source": f"medquad:{topic}",
            }
        )
    return docs


def pubmed_documents() -> list[dict]:
    from datasets import load_dataset

    rows = load_dataset("qiaojin/PubMedQA", "pqa_unlabeled", split="train")
    counts = {t: 0 for t in TOPICS}
    docs: list[dict] = []
    for row in rows:
        topic = _topic(row["question"])
        if not topic or counts[topic] >= PUBMED_PER_TOPIC:
            continue
        counts[topic] += 1
        context = " ".join((row.get("context") or {}).get("contexts", []))
        docs.append(
            {
                "id": f"PMID-{row['pubid']}",
                "title": row["question"][:160],
                "content": (
                    f"Research question: {row['question']}\n"
                    f"Abstract: {context[:3500]}\n"
                    f"Conclusion: {row.get('long_answer', '')[:1200]}"
                ),
                "source": f"pubmedqa:{topic}",
            }
        )
    return docs
