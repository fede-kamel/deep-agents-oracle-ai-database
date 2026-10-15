"""The input guard's patterns (agent/guards.py): real-looking identifiers and other patients."""

import re

from agent import guards


def test_other_patients_are_matched_and_this_one_is_not():
    other = re.compile(guards.other_patient_pattern("SYN-X"))
    assert other.search("see SYN-Y-NOTE-0002")
    assert not other.search("see SYN-X and SYN-X-NOTE-0003")


def test_identifier_shapes():
    shapes = {name: re.compile(p, re.I) for name, p in guards.IDENTIFIER_SHAPES.items()}
    assert shapes["us_ssn"].search("SSN 123-45-6789")
    assert shapes["phone"].search("call (415) 555-0134")
    assert shapes["mrn"].search("MRN: A1234567")
    assert shapes["date_of_birth"].search("DOB 04/12/1951")


def test_clinical_values_are_not_identifiers():
    text = "eGFR 47 mL/min, potassium 5.6, A1c 8.4%, seen 2026-08-20"
    assert not any(re.search(p, text, re.I) for p in guards.IDENTIFIER_SHAPES.values())


def test_two_middlewares_not_one_per_pattern():
    assert len(guards.guard_middleware("SYN-Y")) == 2
