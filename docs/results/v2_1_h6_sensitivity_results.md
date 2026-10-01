# v2.1 registered H6 sensitivity results

Updated: 2026-10-01

H6 is a registered non-directional sensitivity family. Results are reported descriptively and do not modify the frozen primary Open-Jev estimand or model specification.

## Summary

| Instrument/sensitivity | Outcome | Delta AUROC | 95% refit-bootstrap interval |
|---|---|---:|---:|
| Unstripped Open-Jev | Invasive ventilation | -0.01043 | -0.02177 to +0.01773 |
| Unstripped Open-Jev | RRT | -0.00034 | -0.00308 to +0.00310 |
| Unstripped Open-Jev | ICU death, MetaVision | +0.00108 | -0.00911 to +0.00602 |
| Laya | Invasive ventilation | +0.01031 | -0.01595 to +0.02519 |
| Laya | RRT | -0.00079 | -0.00278 to +0.00302 |
| Laya | ICU death, MetaVision | +0.00141 | -0.00660 to +0.00728 |
| DiffusionGemma | Invasive ventilation | -0.00811 | -0.02030 to +0.01445 |
| DiffusionGemma | RRT | pending | pending |
| DiffusionGemma | ICU death, MetaVision | pending | pending |

All completed H6 evaluations shown above used 500 valid patient-cluster refit-bootstrap replicates with zero replacements.

## Unstripped-note Open-Jev

The full unstripped note does not reveal a consistently larger positive semantic increment than the stripped-note primary analyses.

Canonical evaluation jobs:

- ventilation N5N7T9V2;
- RRT R8N4T9V2;
- MetaVision ICU death T4N7R9V2.

Read docs/results/v2_1_h6_unstripped_results.md.

## Laya alternative instrument

All three outcomes are complete.

The ventilation point estimate is positive but uncertain. RRT and MetaVision ICU death remain close to zero. Instrument differences are descriptive H6 sensitivity evidence and should not be used to select a preferred semantic instrument post hoc.

Canonical evaluation jobs:

- ventilation Y8N4R9T2;
- RRT 2AN4R7T9;
- MetaVision ICU death 4CN4R7T9.

Read docs/results/v2_1_h6_laya_results.md.

## DiffusionGemma alternative instrument

Frozen local model revision: f7f5b7f5fa82ffc52addd066915886d497f5517b.

Frozen context policy:

- 977-token note chunks;
- 97-token overlap;
- maximum 8 chunks;
- maximum aggregation for seven concern constructs;
- minimum aggregation for reassuring stability.

Ventilation inference job 9HN4R7T9 completed 4,499/4,499 notes with zero failures and without reading outcome labels.

Ventilation evaluation job B7Q2M9RK:

- comparator AUROC 0.72468;
- augmented AUROC 0.71657;
- delta AUROC -0.00811;
- 95% refit-bootstrap interval -0.02030 to +0.01445;
- primary delta AUPRC +0.00026;
- five frozen-partition delta-AUROCs -0.00811, -0.00892, -0.00108, -0.00478, +0.00423;
- 500/500 valid bootstrap replicates, zero replacements.

RRT inference job D4M8Q2VN completed 7,709/7,709 frozen notes with zero failures, zero label access, and zero max-chunk truncations. Aggregate artifact SHA-256: 763056a90bbf2e5b59e86268bba624d50826689dfb2e5eb0beec3033f74f7182. RRT evaluation job F7K3Q9MV is running. No RRT outcome estimate is available until that evaluation is terminal and its declared artifact is read.

Read docs/results/v2_1_h6_diffusiongemma_results.md.

## Current H6 interpretation

Completed H6 results do not establish a consistent positive semantic increment beyond the rich structured comparator.

- removing language stripping does not reveal a hidden positive effect;
- Laya shows a positive ventilation point estimate but with substantial uncertainty;
- DiffusionGemma ventilation is negative on the primary partition with an interval spanning negative and positive values.

H6 is intentionally a sensitivity family. These estimates should be carried forward together rather than converted into post hoc instrument selection.

## Next registered H6 step

Finish F7K3Q9MV and inspect its canonical aggregate evaluation artifact. If clean, freeze the RRT DiffusionGemma result, then complete the MetaVision ICU-death DiffusionGemma arm before endpoint, timing, note-availability, and CareVue sensitivities.
