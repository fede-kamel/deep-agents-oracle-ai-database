"""Input and output guards: synthetic data only, one patient per run.

Built on LangChain's PIIMiddleware. On the way in, a message that carries
something shaped like a real identifier (a US social security number, a phone
number, an email address, a medical record number, a date of birth) is
blocked before the model sees it, and so is any patient identifier other than
the one this run is scoped to. On the way out, the same identifier shapes are
redacted from model output.
"""

from __future__ import annotations

from langchain.agents.middleware import PIIMiddleware

IDENTIFIER_SHAPES = {
    "us_ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "phone": r"(?<!\d)(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)",
    "mrn": r"\b(?:MRN|medical record (?:number|no\.?))\W{0,3}[A-Z0-9-]{5,}\b",
    "date_of_birth": r"\b(?:DOB|date of birth)\W{0,3}\d{1,4}[/-]\d{1,2}[/-]\d{1,4}\b",
}


def other_patient_pattern(patient_id: str) -> str:
    """Any SYN- identifier except this run's patient (SYN-X matches SYN-X-NOTE-0003)."""
    return rf"\bSYN-(?!{patient_id.split('-')[1]}\b)(?!{patient_id.split('-')[1]}-)[A-Z0-9]+"


def guard_middleware(patient_id: str) -> list:
    blocks = [PIIMiddleware("email", strategy="block", apply_to_input=True)]
    for name, pattern in IDENTIFIER_SHAPES.items():
        blocks.append(PIIMiddleware(name, detector=pattern, strategy="block", apply_to_input=True))
    blocks.append(
        PIIMiddleware("other_patient", detector=other_patient_pattern(patient_id), strategy="block", apply_to_input=True)
    )
    redactions = [
        PIIMiddleware(f"{name}_out", detector=pattern, strategy="redact", apply_to_input=False, apply_to_output=True)
        for name, pattern in IDENTIFIER_SHAPES.items()
    ]
    return blocks + redactions
