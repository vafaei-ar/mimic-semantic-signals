# v2.1 preregistration power / detectable-effect planning freeze

Updated: 2026-09-25

## Status

**Frozen as a planning calculation before v2.1 predictive performance is opened.**

Canonical RunRelay job:

- job: `V9R6M4N2 — Simulate v2.1 Power Grid`
- project commit: `2d74f4d6c327dc1ec7698db98c3d67258e033bb0`
- task: `simulate_preregistration_power_v2_1`
- status: completed
- exit code: 0
- runtime: 1.764 seconds
- aggregate artifact: `outputs/multitask_benchmark/preregistration_power_v2_1.json`
- artifact SHA-256: `2dcc4c23fc222f5db6aa123cfd2b33e96278ce46ae4e478adacaefb9f89ee08a`

No v2.1 predictions or real outcome labels were read.

## Purpose and limitations

This is an approximate **planning** calculation, not the confirmatory inferential method.

Inputs:

- frozen source-specific v2.1 cohort counts;
- exact note-available case/control counts;
- v1 structured AUROCs used only as disclosed planning anchors:
  - ventilation 0.707;
  - RRT 0.948;
  - ICU death 0.793;
- assumed paired prediction correlations 0.80, 0.90, and 0.95;
- one-sided normal approximation using Hanley-McNeil AUC variance;
- alpha 0.05 and the Holm first-step threshold 0.05/3 = 0.0167.

The power grid was frozen before the later synthetic runtime benchmark. After that benchmark showed the 500-replicate exact refit bootstrap was operationally infeasible, the primary inference was amended before OSF registration to estimation-first conditional patient-cluster bootstrap uncertainty plus explicit repeat-to-repeat refit/split stability. The power grid itself is unchanged.

## Full-cohort 80% detectable delta-AUROC

At the Holm first-step threshold:

| Outcome | rho=0.80 | rho=0.90 | rho=0.95 |
| --- | ---: | ---: | ---: |
| Ventilation | 0.0328 | 0.0233 | 0.0165 |
| RRT | 0.0156 | 0.0113 | 0.0081 |
| MetaVision ICU death | 0.0338 | 0.0241 | 0.0172 |

At the midrange rho=0.90 assumption, the approximate 80% detectable effects are therefore about **0.023**, **0.011**, and **0.024** for ventilation, RRT, and death respectively.

## Note-available conditional 80% detectable delta-AUROC

At the Holm first-step threshold:

| Outcome | Cases with note | Controls with note | rho=0.80 | rho=0.90 | rho=0.95 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Ventilation | 135 | 4,364 | 0.0469 | 0.0334 | 0.0237 |
| RRT | 143 | 7,566 | 0.0232 | 0.0170 | 0.0123 |
| MetaVision ICU death | 83 | 7,806 | 0.0536 | 0.0385 | 0.0275 |

The note-available conditional analyses are therefore prospectively labeled **descriptive / lower-power sensitivity analyses**, especially for ventilation and ICU death.

## Interpretation for the SAP

The planning grid makes two points explicit before results:

1. Small effects in the range of the previously observed v1 ventilation/death increments may not be confirmatorily detectable after Holm correction, depending on paired-score correlation.
2. A null or non-significant result must not be interpreted as evidence of zero semantic increment when the confidence interval remains compatible with clinically relevant small effects.

The SAP should report point estimates, the frozen primary conditional patient-cluster intervals, and split/refit stability across repeats, without reducing interpretation to a binary significance label.
