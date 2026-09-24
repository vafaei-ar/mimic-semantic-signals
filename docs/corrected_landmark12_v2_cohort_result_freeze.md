# Corrected 12-hour landmark cohort result freeze v2

Canonical RunRelay job: `Q8R3V7M4`

- task: `build_corrected_landmark12_v2_cohorts`
- exact project commit: `09cd489b5273a3068c5f909c13b9ae481fba4e9a`
- artifact: `outputs/multitask_benchmark/population_landmark12_cohort_manifest_v2.json`
- artifact SHA-256: `e1113d0a280389c61ea5b6d326ca81bb3e128854aba3d085837baa2e8d180e12`
- exit code: 0
- runtime: 982.115 seconds
- protocol: `docs/corrected_landmark12_v2_protocol.md`

No model was fit or scored during this build.

## Source mapping validation

All configured v2 endpoint/disqualifying item IDs exist in `D_ITEMS` and are identified as MetaVision for the ventilation and RRT source-compatible risk sets.

## Corrected cohorts

| Outcome | Source rule | Rows | Cases | Controls | Prevalence | Note coverage |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Invasive ventilation | MetaVision only | 11,126 | 280 | 10,846 | 2.517% | 40.47% |
| RRT | MetaVision only | 19,414 | 314 | 19,100 | 1.617% | 39.75% |
| ICU death | all sources | 49,546 | 537 | 49,009 | 1.084% | 70.91% |

The ventilation source-system artifact present in v1 is therefore removed by construction. RRT is also restricted to a source-compatible primary definition.

## Note hygiene correction

The corrected loader strips category whitespace and parses error flags numerically.

Within admissions represented in the v2 source scan, corrected note categories include:

- Physician: 139,749 retained rows after normalization;
- Respiratory: 31,626 retained rows after normalization;
- Nursing: 220,362;
- Nursing/other: 820,636;
- General: 8,144;
- Consult: 98.

A total of 879 numerically non-zero note-error rows were excluded.

These Physician/Respiratory categories were systematically missed by the v1 string-matching implementation.

## Note availability is no longer created by language deletion

The selected predictor note is chosen without deleting notes based on future-outcome vocabulary.

Note coverage by label is now:

| Outcome | Cases | Controls |
| --- | ---: | ---: |
| Ventilation | 48.21% | 40.27% |
| RRT | 45.54% | 39.65% |
| ICU death | 71.32% | 70.91% |

This does not make note availability non-informative, but the availability indicator is no longer mechanically changed by the outcome-language exclusion rule.

## Direct outcome language in the prospectively selected note

Because v2 selects the actual prospective note before any language sensitivity, some selected notes contain direct treatment/outcome terminology:

| Outcome | All note-available rows | Cases | Controls |
| --- | ---: | ---: | ---: |
| Ventilation | 17.06% | 27.41% | 16.74% |
| RRT | 10.21% | 81.82% | 8.86% |
| ICU death | 5.62% | 39.16% | 5.25% |

This is a real prospective-information feature but creates a major interpretability issue for intervention/outcome prediction. Therefore any manuscript-facing text/semantic claim must report a fixed-note treatment-language-stripped sensitivity using the identical selected note identity. The sensitivity may alter note content only; it may not alter note availability, note time, category, or cohort membership.

For RRT in particular, unstripped text performance must not be interpreted as evidence of latent semantic deterioration because direct RRT language is present in most note-available cases.

## Horizon ascertainment

Cases discharged before the nominal horizon end after their observed event:

- ventilation: 4/280;
- RRT: 27/314;
- ICU death: 360/537.

These remain valid binary cases because the endpoint is observed before discharge. Event-free controls require observation through the full horizon. Manuscript terminology must use **landmark cohort with complete outcome ascertainment**, not an uncensored population sample.

## Frozen interpretation

The v2 cohort correction successfully addresses the known v1 source-system and note-selection artifacts at the cohort-construction level.

No predictive result from v1 should be transplanted to these cohorts. New structured features, text workload, semantic inference, and predictive evaluation require a separate v2 lineage.

The next gate is a model-free audit and freeze of an enhanced prospective structured baseline before any v2 semantic performance is examined.
