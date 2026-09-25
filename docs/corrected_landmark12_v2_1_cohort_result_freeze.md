# Corrected adult 12-hour landmark cohort result freeze v2.1

Updated: 2026-09-25

## Status

**Frozen for downstream preregistration-only analysis.**

Canonical RunRelay job:

- job: `K7Q3M8R4 — Rebuild Adult v2.1 Cohorts`
- exact project commit: `0a5b59023c9cb96950be6ec2e71e26fbec4378da`
- task: `build_corrected_landmark12_v2_1_cohorts`
- status: completed
- exit code: 0
- aggregate artifact: `outputs/multitask_benchmark/population_landmark12_cohort_manifest_v2_1.json`
- artifact SHA-256: `662afa8b5535d44037e2e7dc07cc02f32a2356caef7369294591db7996b67b19`

No predictive model was fit or scored.

## Adult eligibility

The source ICU table contained 61,522 stays.

- age <18: 8,193 stays;
- NICU first-careunit: 8,093 stays;
- missing age: 0;
- adult/NICU-excluded eligible stays: 53,329;
- unique eligible patients: 38,510.

The age and NICU counts overlap substantially and must not be added together as independent exclusions.

Eligibility is determined before the >89 deidentification age cap used for modeling.

## Primary cohorts

| Outcome | Source rule | Rows | Patients | Cases | Controls | Prevalence | Note rows | Note coverage |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Invasive ventilation | MetaVision only | 11,116 | 8,982 | 279 | 10,837 | 2.510% | 4,499 | 40.47% |
| RRT | MetaVision only | 19,395 | 15,080 | 314 | 19,081 | 1.619% | 7,709 | 39.75% |
| ICU death | all sources | 45,571 | 33,807 | 521 | 45,050 | 1.143% | 31,271 | 68.62% |

These are the expected-count contract for downstream v2.1 extraction and split-freezing.

## Corrected direct-language prevalence

The direct-language regexes were corrected before this freeze.

Among note-available rows:

| Outcome | Direct-language notes | Overall fraction | Case-note fraction | Control-note fraction |
| --- | ---: | ---: | ---: | ---: |
| Invasive ventilation | 618 | 13.74% | 23.70% | 13.43% |
| RRT | 347 | 4.50% | 54.55% | 3.56% |
| ICU death | 1,962 | 6.27% | 40.33% | 5.87% |

The RRT case-note prevalence remains high enough that the fixed-note stripped corpus remains mandatory and is planned as the primary text corpus.

## Ventilation endpoint sensitivities

### High-specificity primary

Primary case endpoint:

- MetaVision procedure item 224385 (Intubation).

Primary pre-landmark exclusion/control-disqualifying evidence remains broader ventilatory/intubation evidence.

Result:

- rows 11,116;
- cases 279;
- controls 10,837.

### Explicit-intubation evidence sensitivity

The first v2.1 descriptive build revealed that using the explicit endpoint itself as the pre-landmark disqualifying definition changed the risk set. That implementation was corrected **before any predictive performance was run or opened**.

The corrected sensitivity:

- uses the same broad pre-landmark exclusion/control rule as the primary;
- broadens only the post-landmark endpoint to procedure or explicit intubation chart evidence.

Result:

- rows 11,116;
- cases 279;
- controls 10,837.

Therefore the additional explicit-intubation chart items identify **no additional post-landmark cases** once the primary at-risk population is enforced. This sensitivity is empirically identical to the primary cohort and need not create a duplicate predictive analysis unless required for audit reporting.

### Broad respiratory-support sensitivity

Broad endpoint/disqualifying evidence includes:

- 224385;
- explicit intubation chart evidence;
- ventilator mode;
- set tidal volume;
- set respiratory rate.

Result:

- rows 11,380;
- patients 9,174;
- cases 543;
- controls 10,837;
- prevalence 4.772%;
- note rows 4,590.

This is the meaningful alternative ventilation-endpoint sensitivity.

## Note hygiene

Aggregate note-hygiene checks:

- 878 numeric nonzero `ISERROR` rows excluded;
- whitespace-normalized Physician and Respiratory categories retained;
- note identity selected before any language stripping;
- outcome-language matching does not determine note availability.

## Outcome ascertainment caveat retained

Cases whose ICU discharge time precedes the end of the nominal horizon because the event occurred first:

- ventilation: 4;
- RRT: 27;
- ICU death: 345.

This is consistent with the frozen estimand: complete 12-hour outcome ascertainment, with the event itself establishing the outcome before discharge.

## Guardrails

- all primary cohorts are adult and NICU-excluded;
- ventilation/RRT are MetaVision-only;
- `dbsource` is not a predictor;
- no predictive performance has been opened;
- row-level cohort files remain local;
- downstream jobs must assert the machine-readable expected-count contract before analysis.

Machine-readable contract:

- `config/corrected_landmark12_v2_1_expected_counts.json`
