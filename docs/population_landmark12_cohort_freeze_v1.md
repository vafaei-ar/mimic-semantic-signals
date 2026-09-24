# Population-representative 12-hour landmark cohort freeze v1

Canonical build job: `S4M7R2V8`

- exact project commit: `bb074b5df763eaf61b6d47be9977c292facb103d`
- task: `build_population_landmark12_cohorts`
- artifact: `outputs/multitask_benchmark/population_landmark12_cohort_manifest_v1.json`
- artifact SHA-256: `c629dd0e51bfe83a76db451b2ff4e05883880d2c5be3ea5863c8d1438c29dc72`
- exit code: 0

The builder reproduced the model-free feasibility counts exactly.

## Frozen population cohorts

| Outcome | Observable stays | Cases | Controls | Event prevalence | Note coverage | Case note coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Invasive ventilation | 28,699 | 282 | 28,417 | 0.9826% | 67.69% | 43.97% |
| Renal-replacement therapy | 48,831 | 391 | 48,440 | 0.8007% | 69.29% | 39.64% |
| ICU death | 49,555 | 537 | 49,018 | 1.0836% | 68.10% | 56.24% |

No case-control sampling was performed.

## Note-availability implication

Prospective note availability is substantially lower among future cases than controls for ventilation and RRT. Therefore any full-population text/semantic model must preserve the entire observable population and represent absence of an eligible note explicitly.

Analyses restricted to note-available rows may be reported only as conditional sensitivity analyses. They must not be used for population calibration, absolute-risk claims, or primary decision-curve analysis.

## Next-stage rule

Before semantic inference, build structured physiology/laboratory features at the 12-hour landmark for all observable stays using the same frozen feature definitions as the matched benchmark:

- vital lookback: 6 hours
- laboratory lookback: 24 hours
- same MIMIC item-id mappings
- no future measurements
- no model scoring during extraction

Patient identifiers and row-level features remain local. Only aggregate counts and missingness summaries may be shared.
