"""A deterministic background cohort of synthetic patients.

Row-level security hides these rows from every agent user. They exist so the
owner can compute population benchmarks (COHORT_BENCHMARK) that the agent may
read: how fast does eGFR usually fall in this clinic's type 2 diabetes
cohort, how often are heart-failure patients readmitted, how many medicines
does an older COPD patient usually take. Nothing here is real; the generator
is seeded, so every run produces the same people.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

SEED = 26
SIZES = {"T2D": 160, "HFREF": 70, "COPD75": 70}


def _d(base: date, days: int) -> str:
    return (base + timedelta(days=days)).isoformat()


def generate() -> list[dict]:
    rng = random.Random(SEED)
    patients: list[dict] = []
    n = 0
    for cohort, size in SIZES.items():
        for _ in range(size):
            n += 1
            pid = f"SYN-C{n:04d}"
            p = {
                "id": pid, "display_name": f"Cohort {n:04d}", "alias": "Background cohort (synthetic)",
                "sex": rng.choice(["female", "male"]), "conditions": [], "medications": [],
                "labs": [], "encounters": [],
            }
            start = date(2024, 9, 1) + timedelta(days=rng.randint(0, 120))
            if cohort == "T2D":
                p["birth_year"] = rng.randint(1950, 1985)
                p["conditions"].append(("Type 2 diabetes mellitus", "2015-01-01", "active"))
                egfr = rng.gauss(72, 12)
                slope = rng.gauss(-2.5, 2.2)  # mL/min/1.73m2 per year
                a1c = rng.gauss(7.3, 0.8)
                for k in range(4):
                    day = k * 180 + rng.randint(-15, 15)
                    p["labs"].append((_d(start, day), "eGFR", round(max(15, egfr + slope * day / 365 + rng.gauss(0, 2)), 1), "mL/min/1.73m2"))
                    p["labs"].append((_d(start, day), "HbA1c", round(max(5.5, a1c + rng.gauss(0, 0.3)), 1), "%"))
                p["labs"].append((_d(start, 540), "UACR", round(max(5, rng.lognormvariate(3.2, 0.9)), 0), "mg/g"))
                meds = rng.randint(3, 8)
            elif cohort == "HFREF":
                p["birth_year"] = rng.randint(1940, 1965)
                p["conditions"].append(("Heart failure with reduced ejection fraction", "2020-01-01", "active"))
                p["labs"].append((_d(start, 300), "Potassium", round(rng.gauss(4.5, 0.4), 1), "mmol/L"))
                p["labs"].append((_d(start, 300), "BNP", round(rng.lognormvariate(6.2, 0.6), 0), "pg/mL"))
                admit = _d(start, 200)
                p["encounters"].append((admit, "Hospital admission", "inpatient"))
                for r in range(rng.choices([0, 1, 2], weights=[70, 22, 8])[0]):
                    p["encounters"].append((_d(start, 200 + 30 * (r + 1)), "Hospital readmission", "inpatient"))
                meds = rng.randint(5, 10)
            else:
                p["birth_year"] = rng.randint(1938, 1951)
                p["conditions"].append(("Chronic obstructive pulmonary disease", "2014-01-01", "active"))
                p["labs"].append((_d(start, 100), "FEV1", round(rng.gauss(58, 12), 0), "% predicted"))
                meds = max(2, int(rng.gauss(7, 2.2)))
            for m in range(meds):
                p["medications"].append((f"Background medication {m + 1}", None, None, "prescribed", "2023-01-01", "active"))
            p["cohort"] = cohort
            patients.append(p)
    return patients
