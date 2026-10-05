# Pre-visit brief - Patient Y (SYN-Y)
> SYNTHETIC RECORD - invented for a demo, not a real patient. For clinician review; not medical advice.

## Snapshot
Jordan Ellis is a woman born in 1954 with HFrEF, EF 30%, and two heart-failure readmissions within 90 days before this post-discharge heart failure visit. [SQL:patient] [SYN-Y-NOTE-0008] She appears to be cycling back into congestion because she has had diuretic nonadherence on bus days, delayed furosemide refill, cost and transport barriers, and recurrent weight gain with edema and orthopnea after discharge. [SYN-Y-NOTE-0009] [SYN-Y-NOTE-0010] [SYN-Y-NOTE-0013] The most urgent safety issue is that potassium chloride was held during the last admission for K 5.6 mmol/L while she was on lisinopril and spironolactone, but potassium chloride reappeared on the discharge list and she reports taking it again. [SYN-Y-NOTE-0011] [SYN-Y-NOTE-0012] [SYN-Y-NOTE-0013]

## What changed
- **Recurrent post-discharge congestion.** She was hospitalized on 2026-06-03 for dyspnea and leg edema with BNP 980 pg/mL, was diuresed with 3.1 kg net loss, and was discharged on 2026-06-08 with furosemide 40 mg twice daily and daily-weight instructions. [SYN-Y-NOTE-0008] She was readmitted 41 days later on 2026-07-19 with orthopnea after stopping the afternoon furosemide dose on bus days and lacking a home scale, and social work provided a scale at discharge. [SYN-Y-NOTE-0009] She was readmitted again on 2026-08-30 with weight 3.4 kg above discharge, and by 2026-09-15 she again reported weight 73.9 kg, 3.1 kg above discharge, with ankle swelling and two-pillow orthopnea. [SYN-Y-NOTE-0011] [SYN-Y-NOTE-0013]
- **Hyperkalemia medication discrepancy.** During the 2026-08-30 readmission, potassium was 5.6 mmol/L while she was taking spironolactone, lisinopril, and potassium chloride together, so potassium chloride was held. [SYN-Y-NOTE-0011] Potassium chloride appeared again on the 2026-09-04 discharge medication list, and on 2026-09-15 she reported taking all medicines including the potassium tablet. [SYN-Y-NOTE-0012] [SYN-Y-NOTE-0013]
- **Kidney function and sodium are concerning.** The last reported inpatient eGFR was 42 mL/min/1.73m2 on 2026-08-30, which raises concern when combined with potassium-raising medicines and potassium supplementation. [SYN-Y-NOTE-0011] The same admission recorded sodium 133 mmol/L, which is a concerning low sodium value in the setting of recurrent decompensated heart failure. [SYN-Y-NOTE-0011] No eGFR slope or cohort_benchmark comparison was available in the chart analyst’s returned data. [SQL:lab_result]
- **Access barriers remain active.** She reported that copays for eight medicines are difficult on a fixed income, and furosemide refill was picked up 9 days late. [SYN-Y-NOTE-0010] A transport-assistance request is open, while home health nursing was declined because of cost. [SQL:referral] [SYN-Y-NOTE-0012]

## Medications to review
| Medication | Concern | What the chart shows | Source |
|---|---|---|---|
| Furosemide 40 mg twice daily | Recurrent congestion from missed afternoon dose and delayed refill | The medication is active as furosemide 40 mg twice daily. [SQL:medication] She stopped the afternoon dose to avoid bathroom trips on bus days, later had a furosemide refill picked up 9 days late, and now reports recurrent weight gain, ankle swelling, and two-pillow orthopnea. [SYN-Y-NOTE-0009] [SYN-Y-NOTE-0010] [SYN-Y-NOTE-0013] | [SQL:medication] [SYN-Y-NOTE-0009] [SYN-Y-NOTE-0010] [SYN-Y-NOTE-0013] |
| Potassium chloride, dose not returned by chart analyst | Likely inappropriate continuation after hyperkalemia | Potassium chloride was held during the 2026-08-30 admission after K 5.6 mmol/L while she was also on lisinopril and spironolactone. [SYN-Y-NOTE-0011] It reappeared on the 2026-09-04 discharge medication list, and she reported taking the potassium tablet on 2026-09-15. [SYN-Y-NOTE-0012] [SYN-Y-NOTE-0013] | [SYN-Y-NOTE-0011] [SYN-Y-NOTE-0012] [SYN-Y-NOTE-0013] |
| Lisinopril 10 mg once daily | Potassium and renal monitoring needed | Lisinopril 10 mg once daily is active. [SQL:medication] The key concern is the combination of lisinopril with spironolactone and potassium chloride after K 5.6 mmol/L and eGFR 42 mL/min/1.73m2. [SYN-Y-NOTE-0011] [SYN-Y-NOTE-0013] | [SQL:medication] [SYN-Y-NOTE-0011] [SYN-Y-NOTE-0013] |
| Spironolactone 25 mg once daily | Hyperkalemia risk with ACE inhibitor, potassium supplement, and eGFR 42 | Spironolactone 25 mg once daily is active. [SQL:medication] Potassium was 5.6 mmol/L when she was taking spironolactone, lisinopril, and potassium chloride together. [SYN-Y-NOTE-0011] | [SQL:medication] [SYN-Y-NOTE-0011] |
| SGLT2 inhibitor not documented | HFrEF therapy gap or undocumented rationale | The discharge review noted no SGLT2 inhibitor and no documented reason. [SYN-Y-NOTE-0012] This should be reviewed after potassium, renal function, volume status, cost, and discharge-medication reconciliation are addressed. [SYN-Y-NOTE-0011] [SYN-Y-NOTE-0012] | [SYN-Y-NOTE-0011] [SYN-Y-NOTE-0012] |

The highest-risk interaction is the potassium-raising combination of lisinopril plus spironolactone plus potassium chloride after documented K 5.6 mmol/L and eGFR 42 mL/min/1.73m2. [SYN-Y-NOTE-0011] The practical driver of readmission appears to be under-diuresis from skipped or delayed furosemide in the setting of transport, urinary-frequency, and cost barriers. [SYN-Y-NOTE-0009] [SYN-Y-NOTE-0010] [SQL:referral]

## Overdue monitoring and open care gaps
- **Immediate post-discharge potassium and renal-function reassessment.** The chart returned no outpatient potassium or creatinine/eGFR after discharge despite K 5.6 mmol/L on 2026-08-30 and renewed potassium chloride exposure after discharge. [SYN-Y-NOTE-0011] [SYN-Y-NOTE-0012] [SYN-Y-NOTE-0013]
- **Medication reconciliation with physical bottles and discharge list.** Potassium chloride was held during admission but reappeared on the discharge list, and she reports taking it. [SYN-Y-NOTE-0011] [SYN-Y-NOTE-0012] [SYN-Y-NOTE-0013] Furosemide adherence and access also need reconciliation because she skipped afternoon doses and picked up a refill 9 days late. [SYN-Y-NOTE-0009] [SYN-Y-NOTE-0010]
- **SGLT2 inhibitor rationale absent.** No SGLT2 inhibitor was documented, and no reason was recorded on the discharge review. [SYN-Y-NOTE-0012] This remains a HFrEF optimization question once immediate safety and access issues are stabilized. [SYN-Y-NOTE-0012]
- **Transport and medication-cost support unresolved.** She requested transport assistance, and she stated that copays for eight medicines are difficult on a fixed income. [SQL:referral] [SYN-Y-NOTE-0010] Home health nursing was declined because of cost, so lower-cost support routes are needed. [SYN-Y-NOTE-0012]

## What the reference and research say
### Clinical reference
- The clinical reference identifies diuretics and ACE inhibitors among medications used to manage heart failure, with diuretics used to reduce fluid buildup and ACE inhibitors used to improve heart failure in multiple ways. [MEDQUAD-03657#chunk-0] *This supports first addressing whether her prescribed diuretic regimen is being taken and whether the ACE inhibitor can be continued safely after potassium and renal testing. [MEDQUAD-03657#chunk-0] [SYN-Y-NOTE-0009] [SYN-Y-NOTE-0011]*
- The clinical reference states that proper blood potassium level is essential, that potassium keeps the heart beating regularly, and that damaged kidneys can allow potassium to build up and cause serious heart problems. [MEDQUAD-01695#chunk-0] *This directly applies because her last admission showed K 5.6 mmol/L, eGFR 42 mL/min/1.73m2, and continued potassium tablet use after discharge. [MEDQUAD-01695#chunk-0] [SYN-Y-NOTE-0011] [SYN-Y-NOTE-0013]*
- The clinical reference states that older adults should limit sodium intake and explains that salt can cause extra fluid buildup and contribute to high blood pressure. [MEDQUAD-03651#chunk-0] *This is relevant because she has recurrent fluid overload manifested by weight gain, edema, and orthopnea after discharge. [MEDQUAD-03651#chunk-0] [SYN-Y-NOTE-0013]*
- The clinical reference states that excess sodium can cause blood to hold fluid and that people with CKD need to avoid fluid buildup because it strains the heart and kidneys. [MEDQUAD-01694#chunk-0] *This matters because her eGFR was 42 mL/min/1.73m2 and she has recurrent heart-failure congestion. [MEDQUAD-01694#chunk-0] [SYN-Y-NOTE-0011]*
- The clinical reference states that eGFR below 60 may indicate kidney damage. [MEDQUAD-02121#chunk-3] *Her eGFR of 42 mL/min/1.73m2 increases the importance of medication and electrolyte monitoring. [MEDQUAD-02121#chunk-3] [SYN-Y-NOTE-0011]*

### Research evidence
- A randomized study of continued heart-failure clinic follow-up versus usual care found no significant difference in the combined outcome of unplanned hospitalization or death, but it did find fewer heart-failure-related hospitalizations and improved quality of life in the heart-failure clinic group. [PMID-19065446] *This supports prioritizing close HF-clinic management for her recurrent HF-related readmissions. [PMID-19065446] [SQL:patient]*
- A study using claims data examined whether primary-care practice style, including mean delay between consultations and intensity of care, was associated with readmissions in heart-failure patients. [PMID-27727296] *This supports minimizing follow-up delays because she is already symptomatic again after discharge. [PMID-27727296] [SYN-Y-NOTE-0013]*
- A study of Joint Commission heart-failure discharge instructions evaluated diet, exercise, weight monitoring, worsening-symptom instructions, and patient understanding as factors relevant to preventing readmissions. [PMID-24996200] *This supports teach-back on weights, swelling, orthopnea, diuretic timing, and when to call because she missed diuretic doses and then regained weight. [PMID-24996200] [SYN-Y-NOTE-0009] [SYN-Y-NOTE-0013]*
- A heart-failure self-management intervention study evaluated effects on health-related quality of life and supports attention to patient self-management behaviors. [PMID-23743855] *This supports pairing medication reconciliation with realistic self-care planning for bus days, cost barriers, and daily weights. [PMID-23743855] [SYN-Y-NOTE-0009] [SYN-Y-NOTE-0010]*

## Insights for the clinician: next steps
1. **Check same-day BMP, magnesium, renal function, and weight before medication decisions.** Potassium was 5.6 mmol/L with eGFR 42 mL/min/1.73m2 during the last admission, and she reports taking potassium chloride again after discharge. [SYN-Y-NOTE-0011] [SYN-Y-NOTE-0013] Proper potassium level is essential for cardiac function, and damaged kidneys can allow potassium to build up and cause serious heart problems. [MEDQUAD-01695#chunk-0]
2. **Reconcile medications first, with special focus on stopping the unintended potassium loop if confirmed.** Potassium chloride was held during the hospitalization but reappeared on the discharge medication list, and she reports taking it. [SYN-Y-NOTE-0011] [SYN-Y-NOTE-0012] [SYN-Y-NOTE-0013] The potassium-raising combination of lisinopril, spironolactone, and potassium chloride is the clearest near-term safety risk in the returned chart. [SYN-Y-NOTE-0011]
3. **Treat current congestion and solve the diuretic-adherence barrier.** She is 3.1 kg above discharge weight with ankle swelling and two-pillow orthopnea after prior readmission from skipping the afternoon furosemide dose on bus days. [SYN-Y-NOTE-0009] [SYN-Y-NOTE-0013] Diuretics are used to reduce fluid buildup, so the plan should include an acceptable dosing schedule, refill access, and clear response thresholds. [MEDQUAD-03657#chunk-0] [SYN-Y-NOTE-0010]
4. **Address cost and transport during the visit, not after another readmission.** Medication copays for eight medicines are difficult, the furosemide refill was 9 days late, and transport assistance was requested. [SYN-Y-NOTE-0010] [SQL:referral] These access barriers plausibly explain why standard discharge instructions have not translated into stable outpatient control. [SYN-Y-NOTE-0009] [SYN-Y-NOTE-0013]
5. **Re-teach daily weights, sodium/fluid precautions, and symptom escalation with teach-back.** The reference links sodium to fluid buildup, and the research emphasizes patient understanding of diet, weight monitoring, worsening symptoms, and discharge instructions. [MEDQUAD-03651#chunk-0] [PMID-24996200] Her readmissions and current symptoms followed missed diuretics and recurrent weight gain, so self-management needs to be concrete and feasible. [SYN-Y-NOTE-0009] [SYN-Y-NOTE-0013]
6. **Review HFrEF optimization after immediate safety issues are controlled.** The discharge review documented no SGLT2 inhibitor and no reason, so the clinic should determine whether this is a contraindication, access issue, or missed opportunity. [SYN-Y-NOTE-0012] HF-clinic follow-up has evidence for fewer HF-related hospitalizations and improved quality of life, which supports using this visit to stabilize and optimize therapy. [PMID-19065446]

## Proposed actions (awaiting clinician approval)
- **#26 · lab request.** Order urgent BMP with potassium, creatinine/eGFR, sodium, plus magnesium before or at the visit because she had K 5.6 mmol/L, eGFR 42 mL/min/1.73m2, and renewed potassium chloride exposure. [SYN-Y-NOTE-0011] [SYN-Y-NOTE-0013]
- **#27 · patient message.** Send a clinician-approved message asking her to come promptly, bring all medication bottles and the discharge list, report worsening dyspnea/chest symptoms immediately, keep daily weights, and not miss diuretic doses without calling. [SYN-Y-NOTE-0009] [SYN-Y-NOTE-0013]
- **#25 · follow up.** Schedule comprehensive post-discharge HF follow-up for medication reconciliation, potassium chloride review, volume assessment, diuretic access planning, transport support, medication-cost help, and a close phone check. [SYN-Y-NOTE-0010] [SQL:referral] [PMID-19065446]

## Questions for the visit
1. Did she take potassium chloride today, and can she identify which bottle or discharge instruction led her to restart it? [SYN-Y-NOTE-0012] [SYN-Y-NOTE-0013]
2. What are today’s potassium, creatinine/eGFR, sodium, magnesium, weight, blood pressure, and volume exam findings? [SYN-Y-NOTE-0011] [SYN-Y-NOTE-0013]
3. Which furosemide doses is she missing, especially on bus days, and would a different timing plan preserve diuresis while reducing bathroom concerns? [SYN-Y-NOTE-0009]
4. Has she been able to use the home scale daily since it was provided, and what weight threshold was she told should trigger a call? [SYN-Y-NOTE-0009] [SYN-Y-NOTE-0013]
5. Which medications are unaffordable or were refilled late, and can formulary, copay, or pharmacy synchronization support be arranged? [SYN-Y-NOTE-0010]
6. What transport support is needed for this visit, labs, pharmacy pickup, and early follow-up? [SQL:referral]
7. Why is no SGLT2 inhibitor documented, and is there a contraindication, affordability barrier, or plan to start later? [SYN-Y-NOTE-0012]

## Sources
- [SQL:patient] Patient demographics, heart-failure readmission context, and visit reason
- [SQL:lab_result] Laboratory results including BNP and absence of returned outpatient trend data
- [SQL:medication] Active medication list and doses returned from chart
- [SQL:referral] Referral and transport-assistance information
- [SYN-Y-NOTE-0008] 2026-06-03 to 2026-06-08 heart-failure admission and discharge summary
- [SYN-Y-NOTE-0009] 2026-07-19 readmission note documenting diuretic nonadherence and scale provision
- [SYN-Y-NOTE-0010] Medication cost concern and delayed furosemide refill note
- [SYN-Y-NOTE-0011] 2026-08-30 readmission note with hyperkalemia, eGFR, sodium, and potassium chloride held
- [SYN-Y-NOTE-0012] 2026-09-04 discharge review with potassium chloride on list, no SGLT2 inhibitor reason, and home health declined
- [SYN-Y-NOTE-0013] 2026-09-15 nurse call with recurrent weight gain, edema, orthopnea, and potassium tablet use
- [MEDQUAD-03657#chunk-0] Heart failure treatment reference: diuretics and ACE inhibitors
- [MEDQUAD-01695#chunk-0] Potassium and kidney disease reference
- [MEDQUAD-03651#chunk-0] Sodium restriction and fluid buildup reference
- [MEDQUAD-01694#chunk-0] Sodium, CKD, fluid buildup, heart and kidney strain reference
- [MEDQUAD-02121#chunk-3] eGFR interpretation reference
- [PMID-19065446] Heart failure clinic follow-up, HF hospitalizations, and quality of life study
- [PMID-27727296] Primary care style and heart-failure readmissions study
- [PMID-24996200] Heart-failure discharge instructions and patient understanding study
- [PMID-23743855] Heart-failure self-management intervention study
