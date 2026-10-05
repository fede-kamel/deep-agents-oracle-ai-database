"""Synthetic patient charts for the demo, as relational rows.

Every person, date, identifier and value in this file is invented. The charts
are written by hand so that each one is clinically coherent and carries a few
findings a careful reader would raise before the next visit. No record is
derived from a real patient, and the identifiers use the reserved `SYN-`
prefix so the input guard can tell them apart from anything real.

The shape mirrors the relational schema in `migrations/`: one patient row,
then conditions, allergies, medications, encounters with their notes, lab
results, vital signs, referrals and appointments.
"""

from __future__ import annotations

SYNTHETIC_BANNER = "SYNTHETIC RECORD - invented for a demo, not a real patient."

# medications: (name, dose, frequency, source, started_on, status)
# labs:        (collected_on, test, value, unit)
# vitals:      (measured_on, kind, value, unit)
# encounters:  (date, kind, setting, note text)
# referrals:   (kind, opened_on, status, detail)
# appointments:(scheduled_for, kind, status)

PATIENTS: dict[str, dict] = {
    "X": {
        "id": "SYN-X",
        "display_name": "Patient X",
        "alias": "Alex Moreno (synthetic)",
        "birth_year": 1965,
        "age": 61,
        "sex": "male",
        "situation": "Type 2 diabetes with declining kidney function",
        "visit_reason": "Routine diabetes follow-up in two weeks",
        "question": (
            "Prepare a pre-visit brief for Patient X's diabetes follow-up. "
            "What has changed in kidney function, which medications deserve "
            "review because of it, and which monitoring is overdue?"
        ),
        "conditions": [
            ("Type 2 diabetes mellitus", "2014-05-01", "active"),
            ("Essential hypertension", "2016-02-11", "active"),
            ("Hyperlipidaemia", "2016-02-11", "active"),
            ("Osteoarthritis of the right knee", "2023-10-03", "active"),
            ("Obesity", "2018-01-15", "active"),
        ],
        "allergies": [],
        "medications": [
            ("Metformin", "1000 mg", "twice daily", "prescribed", "2014-05-01", "active"),
            ("Glipizide", "10 mg", "twice daily", "prescribed", "2019-08-20", "active"),
            ("Lisinopril", "20 mg", "once daily", "prescribed", "2016-02-11", "active"),
            ("Atorvastatin", "40 mg", "once daily", "prescribed", "2016-02-11", "active"),
            ("Ibuprofen", "400 mg", "as needed, most days", "self-reported over the counter", "2025-09-10", "active"),
        ],
        "labs": [
            ("2025-03-04", "eGFR", 68, "mL/min/1.73m2"),
            ("2025-03-04", "HbA1c", 7.4, "%"),
            ("2025-03-04", "UACR", 22, "mg/g"),
            ("2025-09-10", "eGFR", 59, "mL/min/1.73m2"),
            ("2025-09-10", "HbA1c", 7.9, "%"),
            ("2026-03-18", "eGFR", 52, "mL/min/1.73m2"),
            ("2026-03-18", "HbA1c", 8.3, "%"),
            ("2026-03-18", "UACR", 148, "mg/g"),
            ("2026-03-18", "Potassium", 5.1, "mmol/L"),
            ("2026-08-26", "eGFR", 47, "mL/min/1.73m2"),
            ("2026-08-26", "HbA1c", 8.6, "%"),
            ("2026-08-26", "Potassium", 5.2, "mmol/L"),
        ],
        "vitals": [
            ("2025-03-04", "Systolic BP", 138, "mmHg"), ("2025-03-04", "Diastolic BP", 84, "mmHg"),
            ("2025-03-04", "Weight", 101, "kg"),
            ("2026-03-18", "Systolic BP", 146, "mmHg"), ("2026-03-18", "Diastolic BP", 88, "mmHg"),
            ("2026-03-18", "Weight", 103, "kg"),
            ("2026-08-26", "Systolic BP", 149, "mmHg"), ("2026-08-26", "Diastolic BP", 90, "mmHg"),
            ("2026-08-26", "Weight", 104, "kg"),
        ],
        "encounters": [
            ("2025-03-04", "Primary care visit", "outpatient",
             "Diabetes reasonably controlled on metformin and glipizide. HbA1c 7.4%. "
             "eGFR 68, UACR 22 mg/g, within normal range. Annual foot exam normal. "
             "Patient reports walking 20 minutes most days. Retinal screening due; "
             "referral sent to ophthalmology."),
            ("2025-06-12", "Ophthalmology referral status", "administrative",
             "Retinal screening appointment missed. Two reminder calls not returned. "
             "Referral remains open."),
            ("2025-09-10", "Primary care visit", "outpatient",
             "HbA1c up to 7.9%. eGFR 59. Patient started a warehouse job with long "
             "shifts and reports irregular meals. Knee pain worse at work; taking "
             "ibuprofen most days, bought over the counter. Advised to limit NSAID "
             "use; patient prefers to keep using it because acetaminophen 'does not work'."),
            ("2026-01-22", "Nurse telephone call", "telephone",
             "Patient reports two episodes of shakiness and sweating in the late "
             "afternoon after skipped lunch, relieved by juice. Home glucose 62 mg/dL "
             "during one episode. Taking glipizide as prescribed."),
            ("2026-03-18", "Primary care visit", "outpatient",
             "HbA1c 8.3%. eGFR 52, UACR now 148 mg/g (was 22 a year ago). BP 146/88 "
             "on lisinopril 20 mg. Potassium 5.1. Discussed adding a second agent; "
             "patient asked to defer until after a work schedule change. Still using "
             "ibuprofen several times a week. Retinal screening still not completed."),
            ("2026-08-26", "Lab result note", "administrative",
             "eGFR 47, HbA1c 8.6%, potassium 5.2. No UACR drawn this cycle. Results "
             "forwarded to primary care for the September follow-up."),
            ("2026-09-02", "Care coordinator message", "portal",
             "Patient confirmed the follow-up visit. Asked whether he can stop the "
             "afternoon glipizide dose because of 'low sugar spells' at work. "
             "Message routed to the physician."),
        ],
        "referrals": [
            ("Ophthalmology - diabetic retinal screening", "2025-03-04", "open",
             "Appointment missed 2025-06; reminders not returned"),
        ],
        "appointments": [
            ("2026-10-19", "Diabetes follow-up", "scheduled"),
        ],
    },
    "Y": {
        "id": "SYN-Y",
        "display_name": "Patient Y",
        "alias": "Jordan Ellis (synthetic)",
        "birth_year": 1954,
        "age": 72,
        "sex": "female",
        "situation": "Heart failure, readmitted twice in 90 days",
        "visit_reason": "Post-discharge heart failure clinic visit in one week",
        "question": (
            "Prepare a pre-visit brief for Patient Y's post-discharge heart "
            "failure visit. Why does she keep being readmitted, what is "
            "concerning in the latest labs and medications, and what should the "
            "clinic address first?"
        ),
        "conditions": [
            ("Heart failure with reduced ejection fraction (EF 30%)", "2020-03-02", "active"),
            ("Coronary artery disease, prior inferior myocardial infarction", "2019-11-14", "active"),
            ("Chronic kidney disease stage 3a", "2024-06-20", "active"),
            ("Type 2 diabetes mellitus", "2012-09-01", "active"),
            ("Lives alone; limited transport", "2026-07-19", "social"),
        ],
        "allergies": [("Sulfa drugs", "rash")],
        "medications": [
            ("Furosemide", "40 mg", "twice daily", "prescribed", "2026-06-08", "active"),
            ("Lisinopril", "10 mg", "once daily", "prescribed", "2020-03-02", "active"),
            ("Spironolactone", "25 mg", "once daily", "prescribed", "2021-01-12", "active"),
            ("Carvedilol", "6.25 mg", "twice daily", "prescribed", "2020-03-02", "active"),
            ("Potassium chloride", "20 mEq", "once daily", "prescribed", "2026-06-08", "active"),
            ("Metformin", "500 mg", "twice daily", "prescribed", "2012-09-01", "active"),
            ("Aspirin", "81 mg", "once daily", "prescribed", "2019-11-14", "active"),
            ("Atorvastatin", "80 mg", "once daily", "prescribed", "2019-11-14", "active"),
        ],
        "labs": [
            ("2026-06-03", "BNP", 980, "pg/mL"),
            ("2026-06-03", "Potassium", 4.6, "mmol/L"),
            ("2026-06-03", "eGFR", 51, "mL/min/1.73m2"),
            ("2026-07-19", "BNP", 1240, "pg/mL"),
            ("2026-07-19", "Potassium", 4.9, "mmol/L"),
            ("2026-07-19", "eGFR", 46, "mL/min/1.73m2"),
            ("2026-08-30", "BNP", 1410, "pg/mL"),
            ("2026-08-30", "Potassium", 5.6, "mmol/L"),
            ("2026-08-30", "eGFR", 42, "mL/min/1.73m2"),
            ("2026-08-30", "Sodium", 133, "mmol/L"),
        ],
        "vitals": [
            ("2026-06-08", "Weight", 71.0, "kg"), ("2026-06-08", "Systolic BP", 118, "mmHg"),
            ("2026-07-24", "Weight", 70.4, "kg"), ("2026-07-24", "Systolic BP", 112, "mmHg"),
            ("2026-09-04", "Weight", 70.8, "kg"), ("2026-09-04", "Systolic BP", 108, "mmHg"),
            ("2026-09-15", "Weight", 73.9, "kg"),
        ],
        "encounters": [
            ("2026-06-03", "Hospital admission", "inpatient",
             "Admitted with dyspnoea and leg oedema. BNP 980. Diuresed with IV "
             "furosemide, 3.1 kg net loss. Echo EF 30%, unchanged. Discharged "
             "2026-06-08 on furosemide 40 mg twice daily with a daily-weights "
             "instruction sheet."),
            ("2026-07-19", "Hospital readmission", "inpatient",
             "Readmitted 41 days after discharge with orthopnoea. Patient explains she "
             "stopped the afternoon furosemide dose 'to avoid running to the bathroom' "
             "on days she takes the bus to the shops. No home scale. Diuresed, "
             "discharged 2026-07-24 with a scale provided by social work."),
            ("2026-07-30", "Pharmacy note", "pharmacy",
             "Patient asked about cost of her medications; copay for eight medicines "
             "is difficult on a fixed income. Furosemide refill picked up 9 days late."),
            ("2026-08-30", "Hospital readmission", "inpatient",
             "Second readmission in 90 days. Weight up 3.4 kg from discharge. "
             "Potassium 5.6 on admission while taking spironolactone, lisinopril and "
             "potassium chloride together. Potassium chloride held during stay. "
             "eGFR 42. Sodium 133."),
            ("2026-09-04", "Discharge summary", "inpatient",
             "Discharge medication list reconciled by the night team; potassium "
             "chloride appears on the discharge list again. No SGLT2 inhibitor; reason "
             "not documented. Follow-up in heart failure clinic within 14 days "
             "requested. Home health not arranged - patient declined because of cost."),
            ("2026-09-15", "Nurse telephone call", "telephone",
             "Patient reports weight 73.9 kg on her home scale this morning (3.1 kg "
             "above discharge weight), new ankle swelling and needing two pillows to "
             "sleep. Reports taking all medicines including the potassium tablet. "
             "Advised to attend clinic; she asked whether transport can be arranged."),
        ],
        "referrals": [
            ("Home health nursing", "2026-09-04", "declined", "Declined because of cost"),
            ("Transport assistance", "2026-09-15", "requested", "Asked by patient on nurse call"),
        ],
        "appointments": [
            ("2026-09-18", "Heart failure clinic", "scheduled"),
        ],
    },
    "Z": {
        "id": "SYN-Z",
        "display_name": "Patient Z",
        "alias": "Morgan Hale (synthetic)",
        "birth_year": 1947,
        "age": 79,
        "sex": "female",
        "situation": "COPD with polypharmacy and a recent fall",
        "visit_reason": "Annual wellness visit with medication review in ten days",
        "question": (
            "Prepare a pre-visit brief for Patient Z's medication review. Which "
            "medications add to fall risk or duplicate each other, how is her COPD "
            "being managed, and what should be discussed at the visit?"
        ),
        "conditions": [
            ("Chronic obstructive pulmonary disease, GOLD group E", "2015-04-09", "active"),
            ("Osteoporosis (T-score -2.8)", "2024-04-15", "active"),
            ("Overactive bladder", "2021-07-30", "active"),
            ("Insomnia", "2023-02-02", "active"),
            ("Generalised anxiety", "2022-05-18", "active"),
            ("Fall at home", "2026-08-21", "resolved"),
        ],
        "allergies": [("Penicillin", "hives")],
        "medications": [
            ("Tiotropium", "18 mcg inhaled", "once daily", "prescribed", "2017-03-01", "active"),
            ("Ipratropium inhaler", "2 puffs", "four times daily", "urgent care", "2026-05-14", "active"),
            ("Budesonide-formoterol", "160/4.5 two puffs", "twice daily", "prescribed", "2019-10-10", "active"),
            ("Salbutamol inhaler", "2 puffs", "as needed", "prescribed", "2015-04-09", "active"),
            ("Oxybutynin", "5 mg", "twice daily", "prescribed", "2021-07-30", "active"),
            ("Zolpidem", "10 mg", "at bedtime", "prescribed", "2023-02-02", "active"),
            ("Diphenhydramine", "50 mg", "at bedtime", "self-reported over the counter", "2026-07-02", "active"),
            ("Sertraline", "50 mg", "once daily", "prescribed", "2022-05-18", "active"),
            ("Alendronate", "70 mg", "once weekly", "prescribed", "2024-04-20", "active"),
            ("Prednisone", "40 mg", "daily for 5 days", "prescribed", "2026-07-02", "completed"),
        ],
        "labs": [
            ("2025-11-10", "FEV1", 48, "% predicted"),
            ("2026-07-02", "Eosinophils", 320, "cells/uL"),
            ("2026-07-02", "Sodium", 131, "mmol/L"),
            ("2026-07-02", "Glucose (random)", 188, "mg/dL"),
            ("2024-04-15", "DEXA T-score", -2.8, "lumbar spine"),
        ],
        "vitals": [
            ("2026-07-02", "SpO2", 91, "%"), ("2026-07-02", "Systolic BP", 132, "mmHg"),
            ("2026-08-21", "Systolic BP lying", 128, "mmHg"),
            ("2026-08-21", "Systolic BP standing", 108, "mmHg"),
            ("2026-08-28", "Timed Up and Go", 16, "s"),
        ],
        "encounters": [
            ("2025-11-10", "Pulmonology visit", "outpatient",
             "FEV1 48% predicted. Two exacerbations in the past year. Inhaler "
             "technique observed: poor coordination with the pressurised inhaler. "
             "Pulmonary rehabilitation referral offered; patient declined due to "
             "transport."),
            ("2026-05-14", "Urgent care visit", "urgent care",
             "Cough and wheeze. Ipratropium inhaler added four times daily. No "
             "reconciliation with existing tiotropium documented."),
            ("2026-07-02", "Primary care visit", "outpatient",
             "Exacerbation; third prednisone course in 12 months. Eosinophils 320. "
             "Patient reports poor sleep, now taking zolpidem 10 mg and an over the "
             "counter sleep aid containing diphenhydramine 'when zolpidem is not "
             "enough'. Sodium 131 on sertraline."),
            ("2026-08-21", "Emergency department visit", "emergency",
             "Fall in the kitchen at 03:00 while getting up to urinate. No fracture "
             "on imaging; bruised hip. Orthostatic drop 20 mmHg systolic. Patient "
             "says she felt 'groggy' after her bedtime pills."),
            ("2026-08-28", "Physiotherapy note", "outpatient",
             "Gait slow, Timed Up and Go 16 seconds. Uses furniture to steady herself "
             "at home. Recommended a walking aid and a home safety assessment."),
            ("2026-09-10", "Pharmacist message", "pharmacy",
             "Community pharmacist flagged two long-acting anticholinergic inhalers "
             "plus oxybutynin and diphenhydramine on the same profile. Requests a "
             "prescriber review."),
        ],
        "referrals": [
            ("Pulmonary rehabilitation", "2025-11-10", "declined", "Declined due to transport"),
            ("Home safety assessment", "2026-08-28", "not scheduled", "Recommended by physiotherapy"),
        ],
        "appointments": [
            ("2026-10-15", "Annual wellness visit with medication review", "scheduled"),
        ],
    },
}
