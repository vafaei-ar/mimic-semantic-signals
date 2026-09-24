# Enhanced structured baseline exact mapping freeze v2

Status: **frozen before feature extraction or predictive evaluation**.

Canonical discovery job: `X8R4Q7M3`

- task: `audit_enhanced_structured_baseline_v2`
- exact project commit: `1d907bf79591bde21fd4afcd00087879cb7a38ab`
- artifact: `outputs/multitask_benchmark/enhanced_structured_baseline_discovery_v2.json`
- artifact SHA-256: `acb466d70fe1ef6af9ef7a58ae784a2810d5206aee0cf218329beb40e5d99a7b`
- exit code: 0
- runtime: 671.461 seconds
- discovery protocol: `docs/enhanced_structured_baseline_discovery_protocol_v2.md`

The final audit used full corrected cohort denominators and preserved outcome membership for ICU stays appearing in multiple outcome cohorts. Earlier discovery runs are superseded for availability estimates; see `docs/enhanced_structured_baseline_discovery_lineage_note.md`.

## Mapping principle

The broad discovery regexes were used only to inspect the local MIMIC dictionaries and prospective availability. Exact feature mappings are now frozen using clinically coherent item sets consistent with the MIT-LCP MIMIC-III derived concept definitions. Broad label-search false positives such as alarm limits, pulmonary-artery pressures, urine chemistry, LDH, HbA1c, and non-blood pH are excluded.

No outcome labels or predictive performance were used to choose the mappings.

## Demographics

- **age_at_icu_years**: ICU admission time minus PATIENTS.DOB, divided by 365.2425 days; values above 90 years are capped at 90 to avoid using the deidentified extreme ages assigned to older MIMIC-III patients.
- **sex**: PATIENTS.GENDER as a categorical feature.

No race/ethnicity, insurance, admission type, service, or source-system indicator is included.

## Six-hour bedside physiology

For heart rate, blood pressure, respiratory rate, oxygen saturation, and temperature:

- use prospectively charted values in the 6 hours ending at the 12-hour ICU landmark;
- exclude CHARTEVENTS rows with numeric non-zero ERROR;
- collapse multiple valid measurements of the same feature at the same charttime by their mean;
- retain the latest value;
- retain 6-hour change = latest minus earliest when at least two distinct measurement times exist.

### Heart rate

Item IDs:

- 211
- 220045

Validity: (0 < HR < 300) bpm.

### Systolic blood pressure

Item IDs:

- 51
- 442
- 455
- 6701
- 220179
- 220050

Validity: (0 < SBP < 400) mmHg.

### Diastolic blood pressure

Item IDs:

- 8368
- 8440
- 8441
- 8555
- 220180
- 220051

Validity: (0 < DBP < 300) mmHg.

### Mean arterial pressure

Item IDs:

- 456
- 52
- 6702
- 443
- 220052
- 220181
- 225312

Validity: (0 < MAP < 300) mmHg.

### Respiratory rate

Item IDs:

- 615
- 618
- 220210
- 224690

Validity: (0 < RR < 70) breaths/minute.

### Peripheral oxygen saturation

Item IDs:

- 646
- 220277

Validity: (0 < SpO2 \le 100) percent.

### Temperature

Celsius item IDs:

- 676
- 223762

Fahrenheit item IDs:

- 678
- 223761

Fahrenheit is converted as ((F-32)/1.8).

Validity before conversion:

- Celsius: (10 < T_C < 50);
- Fahrenheit: (70 < T_F < 120).

Skin, limb, inspired-gas, cooling-device water, blood-CCO, alarm, and temperature-site items are excluded.

## Neurologic status

Use the latest numeric GCS component value in the 6 hours ending at landmark. No delta is used.

### Eye opening

- 184
- 220739

Validity: 1–4.

### Verbal response

- 723
- 223900

Validity: 1–5.

Non-numeric ET/tracheostomy strings are not converted into an extra numeric category for this baseline.

### Motor response

- 454
- 223901

Validity: 1–6.

The three components are retained separately. A derived total is not a primary feature because the handling of intubated/sedated verbal responses requires additional assumptions.

## Twenty-four-hour laboratory physiology

Use the latest valid blood measurement in the 24 hours ending at landmark. When the two WBC item IDs occur at the same charttime, collapse by mean before selecting the latest time.

| Feature | Item ID(s) | Validity |
| --- | --- | --- |
| lactate | 50813 | (0 < x < 50) mmol/L |
| creatinine | 50912 | (0 < x < 150) mg/dL |
| BUN | 51006 | (0 < x < 300) mg/dL |
| WBC | 51300, 51301 | (0 < x < 1000) K/uL |
| hemoglobin | 51222 | (0 < x < 50) g/dL |
| platelets | 51265 | (0 < x < 10000) K/uL |
| sodium | 50983 | (0 < x < 200) mEq/L |
| potassium | 50971 | (0 < x < 30) mEq/L |
| bicarbonate | 50882 | (0 < x < 10000) mEq/L |
| chloride | 50902 | (0 < x < 10000) mEq/L |
| glucose | 50931 | (0 < x < 10000) mg/dL |
| total bilirubin | 50885 | (0 < x < 150) mg/dL |
| INR | 51237 | (0 < x < 50) |
| blood pH | 50820 | (6.0 < x < 8.5) |

Whole-blood alternatives, urine analytes, body-fluid analytes, LDH, HbA1c, and urine pH are excluded from these primary laboratory concepts.

## Six-hour urine output

Use the net urine-output concept in the 6 hours ending at landmark, following the MIT-LCP MIMIC-III urine-output definition.

CareVue urine-output item IDs:

- 40055
- 43175
- 40069
- 40094
- 40715
- 40473
- 40085
- 40057
- 40056
- 40405
- 40428
- 40086
- 40096
- 40651

MetaVision urine-output item IDs:

- 226559
- 226560
- 226561
- 226584
- 226563
- 226564
- 226565
- 226567
- 226557
- 226558
- 227489

GU irrigant input:

- 227488, entered with negative sign.

Only OUTPUTEVENTS values below 5000 mL are used, matching the standard MIMIC concept guardrail. The feature is the six-hour net sum in mL.

## Frozen raw feature set

The raw structured feature set is:

1. age_at_icu_years
2. sex
3. heart_rate_last
4. heart_rate_delta
5. sbp_last
6. sbp_delta
7. dbp_last
8. dbp_delta
9. map_last
10. map_delta
11. resp_rate_last
12. resp_rate_delta
13. spo2_last
14. spo2_delta
15. temperature_c_last
16. temperature_c_delta
17. gcs_eye_last
18. gcs_verbal_last
19. gcs_motor_last
20. lactate_last
21. creatinine_last
22. bun_last
23. wbc_last
24. hemoglobin_last
25. platelets_last
26. sodium_last
27. potassium_last
28. bicarbonate_last
29. chloride_last
30. glucose_last
31. bilirubin_total_last
32. inr_last
33. ph_last
34. urine_output_6h_net_ml

Training-fold imputation, scaling, categorical encoding, and missingness indicators are deferred to the predictive evaluation protocol. They are not performed during feature extraction.

## Guardrails

- no `dbsource` predictor;
- no outcome-conditioned feature selection;
- no predictive model during extraction;
- no semantic/text score during extraction;
- no use of post-landmark measurements;
- all v1 structured features remain preserved;
- v2 row-level features remain local and are never declared as RunRelay artifacts.
