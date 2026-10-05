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
    """Two middlewares, not one per pattern: every middleware adds graph nodes
    around each model call, and LangGraph's recursion limit counts them."""
    identifiers = "|".join(f"(?:{p})" for p in IDENTIFIER_SHAPES.values())
    email = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    blocked = f"{identifiers}|(?:{email})|(?:{other_patient_pattern(patient_id)})"
    return [
        PIIMiddleware("identifier_or_other_patient", detector=blocked, strategy="block", apply_to_input=True),
        PIIMiddleware("identifier_out", detector=f"{identifiers}|(?:{email})", strategy="redact",
                      apply_to_input=False, apply_to_output=True),
    ]
