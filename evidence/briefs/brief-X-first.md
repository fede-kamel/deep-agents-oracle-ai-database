# Pre-visit brief - Patient X (SYN-X)
> SYNTHETIC RECORD - invented for a demo, not a real patient. For clinician review; not medical advice.

## Snapshot
Alex Moreno is a male born in 1965 with type 2 diabetes, hypertension, hyperlipidaemia, obesity, and right knee osteoarthritis, scheduled for a routine diabetes follow-up on 2026-10-19 [SQL:patient] [SQL:condition] [SQL:appointment]. The key visit issue is worsening diabetic kidney disease risk: eGFR declined to 47 mL/min/1.73m2 by 2026-08-26, UACR rose to 148 mg/g by 2026-03-18, and BP was 149/90 on 2026-08-26 [SQL:lab_result] [SQL:vital_sign]. Diabetes control is also worsening, with HbA1c rising to 8.6% on 2026-08-26, while the patient reports low-sugar symptoms on glipizide during irregular meals [SQL:lab_result] [SYN-X-NOTE-0003] [SYN-X-NOTE-0004] [SYN-X-NOTE-0007].

## What changed
- **Kidney function.** eGFR declined from 68.0 mL/min/1.73m2 on 2025-03-04 to 59.0 on 2025-09-10, 52.0 on 2026-03-18, and 47.0 on 2026-08-26 [SQL:lab_result]. The eGFR slope is -10.00 mL/min/1.73m2/year, which is more negative than the type 2 diabetes cohort 10th percentile of -5.88 mL/min/1.73m2/year, indicating faster decline than most peers in the benchmark [SQL:lab_result] [SQL:cohort_benchmark]. UACR increased from 22.0 mg/g on 2025-03-04 to 148.0 mg/g on 2026-03-18, and no UACR was drawn on 2026-08-26 [SQL:lab_result] [SYN-X-NOTE-0006].
- **Glycaemia and hypoglycaemia.** HbA1c rose from 7.4% on 2025-03-04 to 7.9% on 2025-09-10, 8.3% on 2026-03-18, and 8.6% on 2026-08-26 [SQL:lab_result]. The latest HbA1c is above the type 2 diabetes cohort 90th percentile of 8.51% [SQL:lab_result] [SQL:cohort_benchmark]. The patient reported two late-afternoon episodes of shakiness and sweating after skipped lunch, including one home glucose of 62 mg/dL, and later asked about stopping the afternoon glipizide dose because of “low sugar spells” [SYN-X-NOTE-0004] [SYN-X-NOTE-0007].
- **Blood pressure and weight.** BP increased from 138/84 mmHg on 2025-03-04 to 146/88 on 2026-03-18 and 149/90 on 2026-08-26 [SQL:vital_sign]. Weight increased from 101.0 kg on 2025-03-04 to 103.0 kg on 2026-03-18 and 104.0 kg on 2026-08-26 [SQL:vital_sign].
- **Medication context.** The active medication list includes metformin 1000 mg twice daily, glipizide 10 mg twice daily, lisinopril 20 mg once daily, atorvastatin 40 mg once daily, and ibuprofen 400 mg as needed most days [SQL:medication]. The patient reported irregular meals due to a new warehouse job and uses ibuprofen most days for knee pain despite advice to limit NSAID use because of declining kidney function [SYN-X-NOTE-0003]. Potassium was 5.1 on 2026-03-18 and 5.2 on 2026-08-26 while the patient remained on lisinopril with falling eGFR [SYN-X-NOTE-0005] [SYN-X-NOTE-0006] [SQL:medication].

## Medications to review
| Medication | Concern | What the chart shows | Source |
|---|---|---|---|
| Glipizide 10 mg twice daily | Hypoglycaemia risk with missed meals and declining kidney function | The patient takes glipizide as prescribed and reported late-afternoon shakiness and sweating after skipped lunch with one home glucose of 62 mg/dL [SYN-X-NOTE-0004]. The patient later asked about stopping the afternoon glipizide dose because of low-sugar spells [SYN-X-NOTE-0007]. | [SQL:medication] [SYN-X-NOTE-0004] [SYN-X-NOTE-0007] |
| Metformin 1000 mg twice daily | Renal dosing and monitoring as eGFR approaches lower CKD range | The patient remains on metformin 1000 mg twice daily while eGFR has declined from 68.0 on 2025-03-04 to 47.0 mL/min/1.73m2 on 2026-08-26 [SQL:medication] [SQL:lab_result]. The decline rate is -10.00 mL/min/1.73m2/year, faster than the type 2 diabetes cohort 10th percentile slope of -5.88 mL/min/1.73m2/year [SQL:lab_result] [SQL:cohort_benchmark]. | [SQL:medication] [SQL:lab_result] [SQL:cohort_benchmark] |
| Lisinopril 20 mg once daily | Albuminuria benefit context but potassium/BMP monitoring concern | The patient remains on lisinopril 20 mg daily while UACR increased from 22.0 mg/g on 2025-03-04 to 148.0 mg/g on 2026-03-18 [SQL:medication] [SQL:lab_result]. Potassium was 5.1 on 2026-03-18 and 5.2 on 2026-08-26 [SYN-X-NOTE-0005] [SYN-X-NOTE-0006]. | [SQL:medication] [SQL:lab_result] [SYN-X-NOTE-0005] [SYN-X-NOTE-0006] |
| Ibuprofen 400 mg as needed, most days | Kidney and blood pressure concern in worsening CKD risk | Ibuprofen 400 mg as needed most days is charted as self-reported over the counter use that began on 2025-09-10 [SQL:medication]. The patient preferred ibuprofen over acetaminophen for knee pain and was advised to limit NSAID use because of declining kidney function [SYN-X-NOTE-0003]. | [SQL:medication] [SYN-X-NOTE-0003] |
| Atorvastatin 40 mg once daily | Continue cardiovascular risk review in diabetes and CKD risk | Atorvastatin 40 mg once daily remains active for hyperlipidaemia in a patient with type 2 diabetes, hypertension, and worsening kidney markers [SQL:medication] [SQL:condition] [SQL:lab_result]. No charted statin intolerance or adherence issue was returned in this review [SQL:medication]. | [SQL:medication] [SQL:condition] [SQL:lab_result] |

The combination needing highest visit review is glipizide with irregular meals and reported hypoglycaemia, plus ibuprofen use in the setting of falling eGFR, rising BP, albuminuria, lisinopril therapy, and potassium 5.2 [SYN-X-NOTE-0003] [SYN-X-NOTE-0004] [SYN-X-NOTE-0006] [SYN-X-NOTE-0007] [SQL:lab_result] [SQL:vital_sign] [SQL:medication]. Lisinopril remains relevant to albuminuria but requires potassium and kidney-function review because potassium has risen while eGFR has fallen [SQL:medication] [SQL:lab_result] [SYN-X-NOTE-0005] [SYN-X-NOTE-0006].

## Overdue monitoring and open care gaps
- **Repeat UACR is overdue or missing from latest kidney reassessment.** UACR rose from 22.0 mg/g on 2025-03-04 to 148.0 mg/g on 2026-03-18, but no UACR was drawn on 2026-08-26 [SQL:lab_result] [SYN-X-NOTE-0006]. MEDQUAD clinical reference states that people with type 2 diabetes should have UACR measured at least once yearly [MEDQUAD-02122#chunk-1].
- **Renal panel/BMP and potassium reassessment is due before medication decisions.** eGFR declined to 47.0 mL/min/1.73m2 on 2026-08-26 and potassium was 5.2 on the same date [SQL:lab_result] [SYN-X-NOTE-0006]. MEDQUAD clinical reference notes that damaged kidneys can allow potassium buildup that may cause serious heart problems [MEDQUAD-01695#chunk-0].
- **Retinal screening remains overdue.** A diabetic retinal screening referral was sent on 2025-03-04, the June 2025 appointment was missed, and later reminders were not returned [SYN-X-NOTE-0001] [SYN-X-NOTE-0002] [SYN-X-NOTE-0005]. The referral remains open and overdue [SQL:referral].
- **Foot exam needs update if not done at this visit.** The annual foot exam was normal on 2025-03-04, and no more recent foot exam was returned in the chart review [SYN-X-NOTE-0001]. This is now more than one year old at the 2026 diabetes follow-up [SQL:appointment].
- **Glycaemic monitoring and treatment review are overdue because A1c is rising despite hypoglycaemia episodes.** HbA1c increased to 8.6% on 2026-08-26 while the patient reported symptomatic low glucose episodes and asked about stopping afternoon glipizide [SQL:lab_result] [SYN-X-NOTE-0004] [SYN-X-NOTE-0007]. Adding a second agent was discussed on 2026-03-18, but the patient asked to defer at that time [SYN-X-NOTE-0005].

## What the reference and research say
### Clinical reference
- MEDQUAD states that people with type 2 diabetes should have urine albumin-to-creatinine ratio measured at least once a year [MEDQUAD-02122#chunk-1]. MEDQUAD also states that regular screening is important for diagnosing diabetic kidney disease [MEDQUAD-02122#chunk-1]. *This supports repeating UACR now because Patient X’s UACR rose to 148 mg/g and the latest lab set omitted UACR [SQL:lab_result] [SYN-X-NOTE-0006].*
- MEDQUAD states that eGFR should be calculated at least once a year in all people with type 1 or type 2 diabetes [MEDQUAD-02122#chunk-1]. MEDQUAD identifies eGFR as part of regular diabetic kidney disease screening [MEDQUAD-02122#chunk-1]. *This supports repeat kidney-function monitoring because Patient X’s eGFR decline is rapid at -10.00 mL/min/1.73m2/year [SQL:lab_result].*
- MEDQUAD states that keeping potassium at the proper blood level is essential for heart and muscle function [MEDQUAD-01695#chunk-0]. MEDQUAD states that damaged kidneys can lead to potassium buildup, which can cause serious heart problems [MEDQUAD-01695#chunk-0]. *This supports prompt potassium reassessment because Patient X’s potassium reached 5.2 with eGFR 47 and active lisinopril therapy [SYN-X-NOTE-0006] [SQL:lab_result] [SQL:medication].*
- The MEDQUAD search returned no useful finding for metformin eGFR thresholds, sulfonylurea management in CKD, NSAID kidney risk, SGLT2 inhibitor or GLP-1 receptor agonist therapy in CKD, retinal screening frequency, foot exam frequency, or ACE-inhibitor laboratory monitoring. *For those topics, the chart-driven medication concerns should be treated as issues for clinician judgment and local guideline review rather than as MEDQUAD-supported recommendations.*

### Research evidence
- The evidence-researcher performed targeted PubMed searches for SGLT2 inhibitor kidney outcome trials, GLP-1 receptor agonist kidney and cardiovascular outcomes, NSAID nephrotoxicity, sulfonylurea hypoglycaemia in CKD, metformin safety in moderate CKD, albuminuria/eGFR slope prognosis, and ACE/ARB hyperkalemia monitoring, but returned no useful PMID-cited findings. *No PMID-cited research finding is available from this run to support or oppose medication changes for Patient X.*

## Insights for the clinician: next steps
1. **Obtain updated labs before or at the visit.** Order HbA1c, BMP or renal panel with creatinine/eGFR and potassium, and UACR because A1c is 8.6%, eGFR has fallen to 47, potassium is 5.2, and the latest UACR is missing despite prior UACR 148 mg/g [SQL:lab_result] [SYN-X-NOTE-0006]. MEDQUAD supports at least annual UACR and eGFR monitoring in type 2 diabetes, and notes that potassium can build up when kidneys are damaged [MEDQUAD-02122#chunk-1] [MEDQUAD-01695#chunk-0].
2. **Review glipizide urgently in context of meals and hypoglycaemia.** The patient takes glipizide 10 mg twice daily and reports skipped meals with late-afternoon shakiness, sweating, one glucose of 62 mg/dL, and a request to stop the afternoon dose [SQL:medication] [SYN-X-NOTE-0003] [SYN-X-NOTE-0004] [SYN-X-NOTE-0007]. This should be reconciled before intensifying diabetes therapy because HbA1c is high while symptomatic lows are occurring [SQL:lab_result] [SYN-X-NOTE-0004].
3. **Address ibuprofen exposure and kidney/BP decline.** The patient uses ibuprofen most days and previously preferred it for knee pain despite advice to limit NSAID use because of declining kidney function [SQL:medication] [SYN-X-NOTE-0003]. The concern is higher now because eGFR has declined rapidly, UACR has risen, and BP is 149/90 [SQL:lab_result] [SQL:vital_sign].
4. **Reassess lisinopril safety and BP/albuminuria strategy.** The patient remains on lisinopril 20 mg daily with UACR 148 mg/g, BP 149/90, eGFR 47, and potassium 5.2 [SQL:medication] [SQL:lab_result] [SQL:vital_sign] [SYN-X-NOTE-0006]. Potassium follow-up matters because MEDQUAD notes that kidney damage can lead to potassium buildup with serious heart consequences [MEDQUAD-01695#chunk-0].
5. **Update diabetes complication monitoring.** Retinal screening remains open and overdue after a missed June 2025 appointment and unanswered reminders [SQL:referral] [SYN-X-NOTE-0002] [SYN-X-NOTE-0005]. The last documented foot exam was normal on 2025-03-04, with no more recent exam returned [SYN-X-NOTE-0001].
6. **Use the visit to revisit kidney-protective and weight-conscious diabetes options without repeating the prior generic deferred action.** A second agent was discussed on 2026-03-18 and deferred, but since then the chart shows A1c 8.6%, eGFR 47, UACR 148 mg/g, BP 149/90, and ongoing hypoglycaemia symptoms on glipizide [SYN-X-NOTE-0005] [SQL:lab_result] [SQL:vital_sign] [SYN-X-NOTE-0007]. No useful PMID-cited evidence was returned in this run, so specific drug selection should follow the clinician’s current guideline workflow and the updated labs.

## Proposed actions (awaiting clinician approval)
- **#22 · lab request.** Request HbA1c, UACR, and BMP to reassess glycaemia, albuminuria, eGFR, and potassium before medication decisions.
- **#24 · patient message.** Send a message asking Alex to keep taking medicines until reviewed, bring home glucose readings, report low sugars, and avoid ibuprofen if possible before the visit.
- **#23 · follow up.** Arrange diabetes and kidney disease management follow-up within 30 days because of worsening A1c, rapid eGFR decline, elevated BP, and glipizide-associated hypoglycaemia symptoms.

## Questions for the visit
1. How often is Alex missing meals during warehouse shifts, and do low-sugar symptoms occur only after skipped meals or also after usual meals?
2. What are the home fasting, pre-dinner, bedtime, and symptomatic glucose readings, and can Alex bring the meter or log to the visit?
3. How many days per week is ibuprofen being used, what total daily dose is typical, and would Alex accept non-NSAID knee pain options?
4. Has Alex had any dehydration, acute illness, urinary symptoms, swelling, shortness of breath, or changes in urine output since the eGFR decline?
5. Is Alex willing to revisit diabetes medication options now that A1c, albuminuria, BP, and eGFR have worsened since the prior deferred discussion?
6. Can Alex reschedule retinal screening, and can a foot exam be completed during this visit?
7. What is Alex’s home BP pattern, and is lisinopril being taken consistently without potassium supplements or salt substitutes?

## Sources
- [SQL:patient] Patient demographics and identifiers
- [SQL:condition] Active problem list and condition onset dates
- [SQL:appointment] Scheduled diabetes follow-up appointment
- [SQL:lab_result] Laboratory results including HbA1c, eGFR, UACR, and eGFR slope
- [SQL:cohort_benchmark] Type 2 diabetes cohort benchmarks for HbA1c and eGFR slope
- [SQL:vital_sign] Blood pressure and weight measurements
- [SQL:medication] Active and self-reported medication list
- [SQL:referral] Referral status for diabetic retinal screening
- [SYN-X-NOTE-0001] 2025-03-04 diabetes visit note with foot exam and retinal referral
- [SYN-X-NOTE-0002] Retinal screening missed appointment documentation
- [SYN-X-NOTE-0003] 2025-09-10 note documenting irregular meals, ibuprofen preference, and NSAID-limiting advice
- [SYN-X-NOTE-0004] 2026-01-22 note documenting symptomatic hypoglycaemia and home glucose 62 mg/dL
- [SYN-X-NOTE-0005] 2026-03-18 diabetes/kidney note documenting potassium 5.1, deferred second agent, and retinal reminders
- [SYN-X-NOTE-0006] 2026-08-26 note documenting potassium 5.2 and missing UACR
- [SYN-X-NOTE-0007] 2026-09-02 patient question about stopping afternoon glipizide for low sugar spells
- [MEDQUAD-02122#chunk-1] Diabetic kidney disease screening with UACR and eGFR
- [MEDQUAD-01695#chunk-0] Potassium and kidney disease
