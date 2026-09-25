# Enhanced structured baseline feature result freeze v2.1

Updated: 2026-09-25

## Status

**Frozen for preregistration design work.**

Canonical RunRelay job:

- job: `Q4T9R6M3 — Extract Structured v2.1 Features`
- exact project commit: `b4eb01794b73f9ed06d15b622fde495aab4335ae`
- task: `build_enhanced_structured_baseline_v2_1`
- status: completed
- exit code: 0
- runtime: 886.245 seconds
- aggregate artifact: `outputs/multitask_benchmark/enhanced_structured_baseline_features_v2_1.json`
- artifact SHA-256: `52186258c55a77446d89be87aa5c27761e985c94bd2f7744404413a6d9e185c7`

No predictive model was fit or scored.

## Cohort-contract verification

Before feature scanning, the extractor verified the frozen v2.1 expected-count contract from:

- `config/corrected_landmark12_v2_1_expected_counts.json`
- canonical cohort job: `K7Q3M8R4`
- frozen cohort artifact SHA-256: `662afa8b5535d44037e2e7dc07cc02f32a2356caef7369294591db7996b67b19`

All row, case, control, unique-patient, and note-availability counts matched.

## Feature definition

The core structured comparator remains the frozen 34-feature physiology/laboratory/urine representation:

- age and sex;
- latest and 6-hour change in HR, SBP, DBP, MAP, RR, SpO2, temperature;
- GCS eye, verbal, motor;
- lactate, creatinine, BUN, WBC, hemoglobin, platelets, sodium, potassium, bicarbonate, chloride, glucose, bilirubin, INR, pH;
- 6-hour net urine output.

No `dbsource`, note-content, semantic, lexical, or outcome-conditioned feature was included.

## GCS verbal airway correction

The v2.1 extractor treats airway-coded verbal responses as missing rather than physiologic verbal GCS=1.

Aggregate CHARTEVENTS diagnostics:

- candidate rows: 42,836,279;
- error rows excluded: 16,822;
- out-of-range rows excluded: 37,315;
- **GCS verbal airway-coded rows excluded: 32,942**.

This is a material correction, especially for RRT and ICU-death cohorts.

### Verbal GCS availability

| Outcome | v2.1 nonmissing fraction |
| --- | ---: |
| Ventilation | 0.9303 |
| RRT | 0.6816 |
| ICU death | 0.6448 |

The large reduction relative to pre-v2.1 reflects removal of ETT/tracheostomy-coded verbal values, not missing cohort rows.

## Adult/NICU correction and feature availability

The death cohort shows the expected improvement in several core physiologic/laboratory features after adult/NICU restriction.

Selected v2.1 nonmissing fractions:

| Feature | Ventilation | RRT | ICU death |
| --- | ---: | ---: | ---: |
| HR | 0.9824 | 0.9887 | 0.9809 |
| MAP | 0.9815 | 0.9878 | 0.9789 |
| GCS eye | 0.9380 | 0.9467 | 0.9466 |
| GCS motor | 0.9374 | 0.9450 | 0.9447 |
| Creatinine | 0.9817 | 0.9874 | 0.9670 |
| WBC | 0.9777 | 0.9844 | 0.9561 |
| Urine output | 0.8909 | 0.9319 | 0.9035 |

In the pre-v2.1 death extraction, MAP was about 0.902, GCS eye about 0.872, and creatinine about 0.892. Their v2.1 increases are consistent with removal of neonatal/pediatric stays with structurally different documentation and laboratory patterns.

## Missingness summary

| Outcome | Rows | Numeric missing fraction | Clinical numeric missing fraction | Rows with all clinical numeric features missing |
| --- | ---: | ---: | ---: | ---: |
| Ventilation | 11,116 | 0.0912 | 0.0940 | 11 |
| RRT | 19,395 | 0.0862 | 0.0889 | 11 |
| ICU death | 45,571 | 0.0998 | 0.1029 | 270 |

The all-clinical-missing diagnostic excludes age, so it is now meaningful.

## Other extraction diagnostics

- unique ICU stays processed: 45,608;
- age nonmissing: 100%;
- age capped at 90: 2,281;
- sex: 25,772 M / 19,836 F;
- laboratory candidate rows: 6,755,431;
- laboratory out-of-range rows excluded: 39;
- urine candidate rows: 3,212,581;
- urine rows >=5000 mL excluded: 9.

## Interpretation

The feature layer is now suitable for the remaining **preregistration-only** design work:

1. label-free treatment/support/code-status mapping audit;
2. documentation-behavior construction;
3. death CareVue/MetaVision source-proxy diagnostic;
4. exact split freezing;
5. aggregate-count power/MDE planning;
6. synthetic refit-bootstrap benchmark.

It is **not yet authorized for real-label predictive evaluation**. The OSF registration execution lock remains in force.
