# v2.1 registered H6 sensitivity results

Updated: 2026-10-02

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
| DiffusionGemma | RRT | -0.00083 | -0.00283 to +0.00244 |
| DiffusionGemma | ICU death, MetaVision | +0.00499 | -0.00654 to +0.00652 |
| Broad respiratory-support endpoint + Open-Jev | Invasive ventilation | -0.00643 | -0.01879 to +0.01046 |

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

RRT inference job D4M8Q2VN completed 7,709/7,709 frozen notes with zero failures, zero label access, and zero max-chunk truncations. RRT evaluation job F7K3Q9MV completed with comparator AUROC 0.97394, augmented AUROC 0.97310, delta AUROC -0.00083, 95% refit-bootstrap interval -0.00283 to +0.00244, primary delta AUPRC +0.01231, five frozen-partition delta-AUROCs -0.00083, -0.00037, +0.00047, -0.00038, +0.00324, and 500/500 valid bootstrap replicates with zero replacements. Evaluation artifact SHA-256: 179b0e6ea1ab6e4f60eeeb4027ae7c291eec51599597ce7dbcead318e884ef9a.

MetaVision ICU-death inference job G8M4Q2VN completed 7,889/7,889 notes with zero failures and no label access. Evaluation job H9Q4M2VK completed with comparator AUROC 0.93338, augmented AUROC 0.93837, delta AUROC +0.00499, 95% refit-bootstrap interval -0.00654 to +0.00652, primary delta AUPRC +0.00882, and 500/500 valid bootstrap replicates with zero replacements. Evaluation artifact SHA-256: b12f961687c67c2ed25a689cd5f79d492b2db89010a8fc9c543cabbd19e0dc23.

Read docs/results/v2_1_h6_diffusiongemma_results.md.

## Current H6 interpretation

Completed H6 results do not establish a consistent positive semantic increment beyond the rich structured comparator.

- removing language stripping does not reveal a hidden positive effect;
- Laya shows a positive ventilation point estimate but with substantial uncertainty;
- DiffusionGemma ventilation is negative on the primary partition with an interval spanning negative and positive values;
- DiffusionGemma RRT remains essentially null, with a narrow interval around zero;
- DiffusionGemma MetaVision ICU death has a small positive point estimate, but its interval spans negative and positive values.

H6 is intentionally a sensitivity family. These estimates should be carried forward together rather than converted into post hoc instrument selection.

## Next registered H6 step

The three-outcome DiffusionGemma arm is complete. The explicit-intubation ventilation sensitivity is empirically identical to primary H1 and does not require a separate predictive rerun. The broad respiratory-support endpoint arm is also complete: W4Y8P6N2 reported comparator AUROC 0.70385, augmented AUROC 0.69741, delta AUROC -0.00643, 95% refit-bootstrap interval -0.01879 to +0.01046, primary delta AUPRC -0.00296, five frozen-partition delta-AUROCs -0.00643, +0.00160, -0.01098, -0.00698, and -0.00634, and 500/500 valid bootstrap replicates with zero replacements. Artifact SHA-256: 824114f7217a3a5af6806ce6b4e413e4ec070edd865f21ee2bb60e68c3c2ea80.

Current job Y6Z3R8M4 is preparing the registered CHARTEVENTS storetime sensitivity before any timing-matched predictive result is opened.
