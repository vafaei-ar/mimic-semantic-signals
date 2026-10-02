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
| CHARTEVENTS storetime + Open-Jev | Invasive ventilation | +0.00668 | -0.02079 to +0.02286 |
| CHARTEVENTS storetime + Open-Jev | RRT | +0.00053 | -0.00307 to +0.00261 |
| CHARTEVENTS storetime + Open-Jev | ICU death, MetaVision | -0.00207 | -0.00923 to +0.00689 |

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

CHARTEVENTS storetime preparation Y6Z3R8M4 completed without fitting predictive models. Of 2,588,698 in-window CHARTEVENTS rows, 127,617 (4.93%) lacked storetime, 187,322 (7.24%) were stored after the landmark, and 2,273,759 (87.83%) were retained. At least one CHARTEVENTS-derived feature changed versus primary in 56.18% of ventilation rows, 53.24% of RRT rows, and 45.33% of all-source ICU-death preparation rows. Preparation artifact SHA-256: 9cf9de723239481a0b42604482a0186885520c7dc56df6640ac08e80d9a12901.

Ventilation storetime evaluation Z7B4R9M5 completed with comparator AUROC 0.71690, augmented AUROC 0.72358, delta AUROC +0.00668, 95% refit-bootstrap interval -0.02079 to +0.02286, primary delta AUPRC -0.00605, five frozen-partition delta-AUROCs +0.00668, -0.01056, -0.00523, -0.00220, and +0.00336, and 500/500 valid bootstrap replicates with zero replacements. Artifact SHA-256: ee34846501989672c7a4e3fc2dcfb2536f0ed086fce7af9c4357b9f723bbcca4.

RRT storetime evaluation A8C5R2M9 completed with comparator AUROC 0.97401, augmented AUROC 0.97453, delta AUROC +0.00053, 95% refit-bootstrap interval -0.00307 to +0.00261, primary delta AUPRC +0.00329, five frozen-partition delta-AUROCs +0.00053, -0.00002, +0.00137, +0.00009, and +0.00342, and 500/500 valid bootstrap replicates with zero replacements. Artifact SHA-256: 07b9dc303cdab37737274a7759fe6c098813d423b2b28b3ddbd8c0aa1510f839. One copied guardrail sentence says “ventilation population,” but the artifact outcome, cohort size, case count, semantic count, hashes, and executed task are correctly RRT.

MetaVision ICU-death storetime evaluation B9D6R3M2 completed with comparator AUROC 0.93367, augmented AUROC 0.93160, delta AUROC -0.00207, 95% refit-bootstrap interval -0.00923 to +0.00689, primary delta AUPRC -0.01119, five frozen-partition delta-AUROCs -0.00207, -0.00191, -0.00221, +0.00217, and -0.00231, and 500/500 valid bootstrap replicates with zero replacements. Artifact SHA-256: 9b826a21bb6e382b6024870b7080eaf2a0d21c9f899010a8486a6d0c20a644ee.

The complete three-outcome CHARTEVENTS storetime sensitivity does not show a consistent positive Open-Jev increment. Initial lab-lag preparation D3G8V5N2 failed before predictive evaluation on a structured lab-column naming mismatch (`lactate` versus `lactate_last` and analogous fields), with no shared artifact. E4H9W6P3 validated the correction and a synthetic naming assertion. Current job F5J2X7N4 is rerunning the registered 1-hour and 2-hour laboratory-result lag preparation at corrected commit 1ec1ed7d7b6117463b0ec5627eee918ff7ea22af.
