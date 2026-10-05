# Pre-visit brief - Patient X (SYN-X)
> SYNTHETIC RECORD - invented for a demo, not a real patient. For clinician review; not medical advice.

## Snapshot
Patient X is a male born in 1965 with type 2 diabetes, essential hypertension, hyperlipidaemia, obesity, and right knee osteoarthritis, scheduled for a routine diabetes follow-up in two weeks. [SQL:patient] [SQL:condition] The main pre-visit issue is rapid kidney-function decline with albuminuria: eGFR fell from 68 mL/min/1.73m2 on 2025-03-04 to 47 mL/min/1.73m2 on 2026-08-26, and UACR rose from 22 mg/g on 2025-03-04 to 148 mg/g on 2026-03-18. [SQL:lab_result] Medication review is important because he is on metformin 1000 mg twice daily, glipizide 10 mg twice daily with symptomatic hypoglycemia, lisinopril 20 mg daily with potassium 5.2 mmol/L, and ibuprofen 400 mg as needed most days. [SQL:medication] [SQL:lab_result] [SYN-X-NOTE-0004] [SYN-X-NOTE-0007] Monitoring gaps include missing repeat UACR with the latest labs, an open missed retinal-screening referral, no foot exam documented after 2025-03-04, and elevated BP at the last documented visit. [SYN-X-NOTE-0006] [SQL:referral] [SYN-X-NOTE-0001] [SYN-X-NOTE-0002] [SYN-X-NOTE-0005]

## What changed
- **Kidney function.** eGFR declined from 68 mL/min/1.73m2 on 2025-03-04 to 59 on 2025-09-10, 52 on 2026-03-18, and 47 on 2026-08-26. [SQL:lab_result] The chart-calculated slope is -14.17 mL/min/1.73m2 per year, indicating rapid decline. [SQL:lab_result] This is faster than the type 2 diabetes cohort 10th percentile decline of -5.88, median decline of -2.75, and 90th percentile change of 0.99, where a more negative slope means faster decline. [SQL:cohort_benchmark]
- **Albuminuria.** UACR increased from 22 mg/g on 2025-03-04 to 148 mg/g on 2026-03-18. [SQL:lab_result] No UACR was drawn with the latest 2026-08-26 labs, leaving current albuminuria status overdue for reassessment. [SYN-X-NOTE-0006]
- **Glycaemic control and hypoglycemia.** A1c increased from 7.4% on 2025-03-04 to 7.9% on 2025-09-10, 8.3% on 2026-03-18, and 8.6% on 2026-08-26. [SQL:lab_result] The latest A1c of 8.6% is above the type 2 diabetes cohort 90th percentile of 8.51%. [SQL:cohort_benchmark] Despite worsening A1c, he reported symptomatic low sugars with home glucose 62 mg/dL on 2026-01-22 and later asked about stopping the afternoon glipizide because of low sugar spells at work. [SYN-X-NOTE-0004] [SYN-X-NOTE-0007]
- **Potassium and blood pressure.** Potassium was 5.1 mmol/L on 2026-03-18 and 5.2 mmol/L on 2026-08-26 while he remained on lisinopril. [SQL:lab_result] BP was 146/88 on 2026-03-18, suggesting ongoing BP control should be reassessed at the visit. [SYN-X-NOTE-0005]

## Medications to review
| Medication | Concern | What the chart shows | Source |
|---|---|---|---|
| Glipizide 10 mg twice daily | Symptomatic hypoglycemia as kidney function declines | He is prescribed glipizide 10 mg twice daily. [SQL:medication] He reported shakiness and sweating with home glucose 62 mg/dL on 2026-01-22 and asked on 2026-09-02 about stopping the afternoon dose because of low sugar spells at work. [SYN-X-NOTE-0004] [SYN-X-NOTE-0007] | [SQL:medication] [SYN-X-NOTE-0004] [SYN-X-NOTE-0007] |
| Metformin 1000 mg twice daily | Needs renal-function monitoring at eGFR 47 and rapid decline | He is prescribed metformin 1000 mg twice daily. [SQL:medication] eGFR declined to 47 mL/min/1.73m2 on 2026-08-26 after being 68 mL/min/1.73m2 on 2025-03-04. [SQL:lab_result] | [SQL:medication] [SQL:lab_result] |
| Lisinopril 20 mg once daily | Renal-protective role with albuminuria, but potassium monitoring needed | He is prescribed lisinopril 20 mg daily. [SQL:medication] UACR was 148 mg/g on 2026-03-18, and potassium rose to 5.2 mmol/L on 2026-08-26. [SQL:lab_result] | [SQL:medication] [SQL:lab_result] |
| Ibuprofen 400 mg as needed, most days | Potential kidney-safety concern in rapid eGFR decline | He is prescribed ibuprofen 400 mg as needed and uses it most days. [SQL:medication] He was advised on 2025-09-10 to limit NSAID use for knee pain but preferred to continue. [SYN-X-NOTE-0003] | [SQL:medication] [SYN-X-NOTE-0003] |
| Atorvastatin 40 mg once daily | Continue cardiovascular-risk review in diabetes and CKD context | He is prescribed atorvastatin 40 mg once daily. [SQL:medication] Hyperlipidaemia is an active diagnosis in the chart. [SQL:condition] | [SQL:medication] [SQL:condition] |

The highest-priority medication-safety combination is glipizide-related hypoglycemia in the setting of rapid eGFR decline and irregular meals from his warehouse job. [SQL:lab_result] [SYN-X-NOTE-0003] [SYN-X-NOTE-0004] [SYN-X-NOTE-0007] Lisinopril plus declining kidney function and potassium 5.2 mmol/L requires potassium/creatinine reassessment rather than automatic discontinuation because he also has albuminuria. [SQL:medication] [SQL:lab_result]

## Overdue monitoring and open care gaps
- **Repeat kidney monitoring is incomplete.** The latest kidney labs on 2026-08-26 included eGFR 47 mL/min/1.73m2 but did not include UACR. [SQL:lab_result] [SYN-X-NOTE-0006] The last UACR was 148 mg/g on 2026-03-18, after rising from 22 mg/g on 2025-03-04. [SQL:lab_result]
- **Retinal screening is overdue.** A diabetic retinal-screening referral was sent on 2025-03-04. [SYN-X-NOTE-0001] The June 2025 appointment was missed, reminders were not returned, and the referral remains open. [SYN-X-NOTE-0002] [SYN-X-NOTE-0005] [SQL:referral]
- **Foot exam is due if annual exam not done elsewhere.** The last documented annual foot exam was normal on 2025-03-04. [SYN-X-NOTE-0001] No more recent foot exam was found in the chart analyst’s review. [SYN-X-NOTE-0001]
- **BP reassessment is needed.** BP was 146/88 on 2026-03-18 while he was on lisinopril 20 mg daily. [SYN-X-NOTE-0005] [SQL:medication] BP control matters because he has diabetes, albuminuria, and rapid eGFR decline. [SQL:lab_result]
- **Diabetes medication plan remains unresolved.** A discussion about adding another diabetes agent was deferred on 2026-03-18 because of his work schedule. [SYN-X-NOTE-0005] Since then, A1c rose to 8.6% on 2026-08-26 and he reported low sugar spells while still taking glipizide. [SQL:lab_result] [SYN-X-NOTE-0007]

## What the reference and research say
### Clinical reference
- The clinical reference states that people with diabetes should have regular kidney-disease screening with both an eGFR calculation and a urine albumin-to-creatinine ratio measurement at least once a year. [MEDQUAD-02122#chunk-1] It applies this screening expectation to all people with type 2 diabetes. [MEDQUAD-02122#chunk-1] *This supports ordering both repeat eGFR/BMP and UACR because the latest labs missed UACR and his eGFR is declining rapidly. [MEDQUAD-02122#chunk-1]*
- The clinical reference describes eGFR below 60 as a possible sign of kidney damage and eGFR 15 or below as kidney failure. [MEDQUAD-02121#chunk-3] It also states that UACR above 30 mg/g may signify kidney disease because albumin is leaking into the urine. [MEDQUAD-02121#chunk-2] *His eGFR 47 and UACR 148 place the kidney findings in a clinically significant range that should drive medication review and monitoring. [MEDQUAD-02121#chunk-3] [MEDQUAD-02121#chunk-2]*
- The clinical reference notes that hypoglycemia can occur as a side effect of oral diabetes medications such as glipizide that increase insulin production. [MEDQUAD-01391#chunk-0] It also notes that combining insulin-increasing pills with other diabetes treatments can heighten hypoglycemia risk. [MEDQUAD-01392#chunk-1] *This directly fits his symptomatic low glucose while on glipizide 10 mg twice daily and supports prioritizing sulfonylurea de-intensification for physician decision. [MEDQUAD-01391#chunk-0]*
- The clinical reference identifies a diabetes care team as including eye-care clinicians and podiatrists for diabetes-related eye and foot care. [MEDQUAD-02123#chunk-1] It frames these services as part of comprehensive diabetes management. [MEDQUAD-02123#chunk-1] *This supports closing the open retinal-screening referral and updating the foot exam at the diabetes follow-up. [MEDQUAD-02123#chunk-1]*
- The clinical reference notes that damaged kidneys can lead to unsafe potassium buildup, which can cause serious heart problems. [MEDQUAD-01695#chunk-0] It therefore supports attention to potassium when kidney function is declining. [MEDQUAD-01695#chunk-0] *His potassium 5.2 mmol/L while on lisinopril and with eGFR 47 makes repeat potassium and creatinine monitoring important before medication decisions. [MEDQUAD-01695#chunk-0]*

### Research evidence
- In a study comparing stage 3A and 3B CKD, stage 3B CKD and albuminuria independently predicted renal dysfunction progression and adverse renal and cardiovascular outcomes. [PMID-22545920] This supports treating albuminuria and movement toward lower eGFR stages as prognostically important. [PMID-22545920] *Patient X is at eGFR 47, near stage 3B, and already has UACR 148, so preventing further decline is time-sensitive. [PMID-22545920]*
- A metformin safety study found that metformin use patterns should be guided by eGFR cutoffs rather than serum creatinine alone because lactic acidosis incidence was very low. [PMID-20977579] The study supports eGFR-based monitoring when kidney function is below 60. [PMID-20977579] *This supports continuing to evaluate metformin against current and future eGFR rather than using creatinine alone. [PMID-20977579]*
- Losartan reduced albuminuria in diabetic nephropathy, with a 100 mg dose more effective than 50 mg in the reported study. [PMID-12081578] This provides evidence that renin-angiotensin system blockade can reduce albuminuria in diabetic kidney disease. [PMID-12081578] *Although he is on lisinopril rather than losartan, the evidence supports preserving an albuminuria-directed RAAS-blockade strategy while monitoring potassium and creatinine. [PMID-12081578]*
- A study of diabetic-retinopathy screening found that general practitioners could effectively screen for diabetic retinopathy and that adherence improved after brief training. [PMID-11884247] This suggests retinopathy screening is feasible to complete in routine care systems. [PMID-11884247] *His missed retinal-screening appointment should be actively rescheduled rather than left open. [PMID-11884247]*

## Insights for the clinician: next steps
1. **Review and likely reduce glipizide, pending physician approval.** Medication-safety resolved escalation 9 by proposing care action 98 to reduce glipizide, and it awaits the doctor under policy CP-02. His home glucose 62 mg/dL with adrenergic symptoms and recurrent low sugar spells while on glipizide make this the most immediate safety issue. [SYN-X-NOTE-0004] [SYN-X-NOTE-0007] [SQL:medication] [MEDQUAD-01391#chunk-0]
2. **Order updated kidney and diabetes monitoring.** Coordinator action 94 requests repeat BMP/eGFR with potassium, bicarbonate if available, UACR, and timing-appropriate A1c because eGFR fell to 47, potassium reached 5.2, and UACR was omitted from the latest labs. [SQL:lab_result] [SYN-X-NOTE-0006] Diabetes kidney monitoring should include at least annual eGFR and UACR, and UACR above 30 mg/g may indicate kidney disease. [MEDQUAD-02122#chunk-1] [MEDQUAD-02121#chunk-2]
3. **Address ibuprofen exposure and knee-pain alternatives.** He uses ibuprofen most days and previously preferred to continue despite advice to limit NSAIDs. [SQL:medication] [SYN-X-NOTE-0003] With eGFR falling much faster than cohort benchmarks, this is a practical nephrotoxin review point even though the medication-change action is focused on glipizide. [SQL:lab_result] [SQL:cohort_benchmark]
4. **Reassess lisinopril safety and BP at the visit.** Lisinopril is relevant to albuminuria management, but potassium is 5.2 mmol/L and BP was 146/88 at the last visit. [SQL:medication] [SQL:lab_result] [SYN-X-NOTE-0005] Kidney damage can cause unsafe potassium buildup, so repeat potassium/creatinine should guide any BP or RAAS-blockade adjustment. [MEDQUAD-01695#chunk-0]
5. **Close overdue retinal and foot screening gaps.** The retinal referral sent in March 2025 remains open after a missed June 2025 appointment and unreturned reminders. [SYN-X-NOTE-0001] [SYN-X-NOTE-0002] [SYN-X-NOTE-0005] [SQL:referral] The last documented foot exam was normal on 2025-03-04, and diabetes care references include eye-care and podiatry/foot-care clinicians as part of comprehensive management. [SYN-X-NOTE-0001] [MEDQUAD-02123#chunk-1]

## Proposed actions (awaiting clinician approval)
- **#94 · lab request.** Request repeat BMP/eGFR with potassium, bicarbonate if available, UACR, and timing-appropriate A1c to reassess rapid kidney decline, albuminuria, hyperkalemia risk, and glycaemic control.
- **#95 · patient message.** Message patient to complete kidney/diabetes labs, bring a glucose log, report low sugar episodes, avoid or minimize ibuprofen until reviewed, and reschedule diabetic retinal screening.
- **#96 · follow up.** Keep the diabetes follow-up in two weeks with focused review of kidney trend, hypoglycemia, BP, NSAID use, and overdue eye/foot monitoring.
- **#98 · medication change.** Medication-safety proposes reducing glipizide for symptomatic hypoglycemia in the setting of declining eGFR; this awaits the doctor under policy CP-02.

## Questions for the visit
1. How often are the low sugar spells occurring, what time of day do they occur, and are they linked to missed or delayed meals at work? [SYN-X-NOTE-0003] [SYN-X-NOTE-0004] [SYN-X-NOTE-0007]
2. Has he already stopped or skipped any glipizide doses, especially the afternoon dose he asked about? [SYN-X-NOTE-0007]
3. How much ibuprofen is he taking per week, and is he willing to switch to kidney-safer knee-pain strategies? [SQL:medication] [SYN-X-NOTE-0003]
4. Can he complete repeat kidney labs and UACR before or at the visit because the latest labs omitted UACR? [SQL:lab_result] [SYN-X-NOTE-0006]
5. Has he had an eye exam outside the system since the missed June 2025 retinal-screening appointment? [SYN-X-NOTE-0002] [SQL:referral]
6. Has he had any new foot numbness, wounds, infections, or a foot exam since the normal 2025-03-04 exam? [SYN-X-NOTE-0001]
7. What home BP readings, if any, has he recorded since BP 146/88 on 2026-03-18? [SYN-X-NOTE-0005]

## Sources
- [SQL:patient] patient table: demographics, situation, and visit reason
- [SQL:condition] condition table: active diagnoses
- [SQL:lab_result] lab_result table: eGFR, UACR, A1c, potassium, and calculated eGFR slope
- [SQL:cohort_benchmark] cohort_benchmark table: type 2 diabetes eGFR-slope and A1c percentiles
- [SQL:medication] medication table: current medication names, doses, and start dates
- [SQL:referral] referral table: open diabetic retinal-screening referral
- [SYN-X-NOTE-0001] 2025-03-04 diabetes follow-up note with normal foot exam and retinal referral
- [SYN-X-NOTE-0002] 2025-06-12 missed retinal-screening note
- [SYN-X-NOTE-0003] 2025-09-10 diabetes follow-up note with irregular meals and NSAID discussion
- [SYN-X-NOTE-0004] 2026-01-22 hypoglycemia message note
- [SYN-X-NOTE-0005] 2026-03-18 diabetes follow-up note with BP, UACR, and deferred therapy discussion
- [SYN-X-NOTE-0006] 2026-08-26 lab-forwarding note noting no UACR drawn
- [SYN-X-NOTE-0007] 2026-09-02 follow-up confirmation and glipizide concern note
- [MEDQUAD-02122#chunk-1] MEDQUAD clinical reference: diabetes kidney-disease screening with eGFR and UACR
- [MEDQUAD-02121#chunk-3] MEDQUAD clinical reference: eGFR interpretation in kidney disease
- [MEDQUAD-02121#chunk-2] MEDQUAD clinical reference: urine albumin-to-creatinine ratio interpretation
- [MEDQUAD-01391#chunk-0] MEDQUAD clinical reference: hypoglycemia from glipizide and insulin-increasing diabetes medicines
- [MEDQUAD-01392#chunk-1] MEDQUAD clinical reference: hypoglycemia risk with insulin-increasing diabetes pills and other therapies
- [MEDQUAD-02123#chunk-1] MEDQUAD clinical reference: diabetes care team including eye and foot care
- [MEDQUAD-01695#chunk-0] MEDQUAD clinical reference: kidney disease and unsafe potassium buildup
- [PMID-22545920] Stage 3 CKD, albuminuria, and adverse renal/cardiovascular outcomes in type 2 diabetes
- [PMID-20977579] Metformin use, eGFR thresholds, and lactic acidosis considerations
- [PMID-12081578] Losartan dose effect on albuminuria in diabetic nephropathy
- [PMID-11884247] General-practice diabetic retinopathy screening feasibility and adherence
