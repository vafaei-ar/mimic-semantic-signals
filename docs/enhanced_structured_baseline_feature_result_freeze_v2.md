# Enhanced structured baseline feature extraction result freeze v2

Canonical RunRelay job: `C8R6Q9M5`

- task: `build_enhanced_structured_baseline_v2`
- exact project commit: `c71357e6df1209b1549a31fb24170d7607ca170a`
- artifact: `outputs/multitask_benchmark/enhanced_structured_baseline_features_v2.json`
- artifact SHA-256: `7c40ef2dfc28af23ac12e544226570787ea6d2ad6a20aadc8b177356c15e287f`
- exit code: 0
- runtime: 956.854 seconds
- mapping freeze: `docs/enhanced_structured_baseline_mapping_freeze_v2.md`

No predictive model or semantic/text model was fit during extraction. Row-level features remain local.

## Feature set

The frozen baseline contains 34 raw features:

- age and sex;
- latest and 6-hour change for heart rate, SBP, DBP, MAP, respiratory rate, SpO2, and temperature;
- latest GCS eye, verbal, and motor components;
- latest 24-hour lactate, creatinine, BUN, WBC, hemoglobin, platelets, sodium, potassium, bicarbonate, chloride, glucose, total bilirubin, INR, and blood pH;
- 6-hour net urine output.

No ICU source-system variable is present.

## Coverage and missingness

| Outcome | Rows | Numeric missing fraction | All-numeric-missing rows |
| --- | ---: | ---: | ---: |
| Invasive ventilation | 11,126 | 9.10% | 0 |
| RRT | 19,414 | 7.82% | 0 |
| ICU death | 49,546 | 14.47% | 0 |

Common bedside physiology is highly observed in ventilation/RRT and remains well observed in ICU death. Lower-availability features such as lactate, bilirubin, pH, and temperature change remain prespecified and are not dropped post hoc.

Selected nonmissing fractions:

### Invasive ventilation

- HR last 98.2%
- MAP last 98.1%
- temperature last 96.0%
- GCS components ~93.6–93.8%
- creatinine 98.2%
- lactate 54.9%
- bilirubin 51.5%
- pH 38.9%
- 6-hour urine output 89.1%

### RRT

- HR last 98.9%
- MAP last 98.8%
- temperature last 91.7%
- GCS components ~94.5%
- creatinine 98.7%
- lactate 69.4%
- bilirubin 47.7%
- pH 62.3%
- 6-hour urine output 93.2%

### ICU death

- HR last 98.0%
- MAP last 90.2%
- temperature last 86.0%
- GCS components ~87.0%
- creatinine 89.2%
- lactate 55.2%
- bilirubin 42.5%
- pH 65.2%
- 6-hour urine output 88.9%

## Demographics and data cleaning

Across 49,584 unique ICU stays:

- age available: 100%;
- sex: 27,960 male and 21,624 female;
- 2,281 deidentified extreme ages were capped at 90 years per the frozen mapping rule.

Extraction diagnostics:

- CHARTEVENTS candidate rows: 44,577,410;
- CHARTEVENTS numeric-error rows excluded: 16,833;
- CHARTEVENTS physiologically out-of-range rows excluded: 4,386;
- LABEVENTS candidate rows: 6,895,998;
- laboratory out-of-range rows excluded: 39;
- urine-output candidate rows: 3,325,988;
- urine-output values >=5000 mL excluded: 9.

## Frozen decision

The enhanced structured feature layer is ready for predictive evaluation.

The next analysis must remain structured-only. It will establish the performance and calibration ceiling of the corrected enhanced physiology baseline before any v2 semantic or lexical model is evaluated.

All semantic/text inference remains locked until this structured-only evaluation protocol is frozen.
