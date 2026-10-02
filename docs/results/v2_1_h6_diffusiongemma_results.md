# v2.1 registered H6 DiffusionGemma alternative-instrument results

Updated: 2026-10-01

This document records the registered H6 sensitivity in which the primary rich-comparator HGB comparison is repeated with stripped-note DiffusionGemma semantic scores. The registered cohorts, rich comparator, five frozen patient-grouped partitions, HGB specification, eight semantic constructs, and 500-valid-replicate patient-cluster refit-bootstrap procedure are otherwise unchanged.

## Frozen model and inference configuration

- model: google/diffusiongemma-26B-A4B-it
- local model revision: f7f5b7f5fa82ffc52addd066915886d497f5517b
- backend: native Transformers BF16 prompted semantic scoring
- score definition: prompted zero-shot 0-1 support scores, not Jev noul probabilities
- note chunk size: 977 tokenizer tokens
- chunk overlap: 97
- maximum chunks: 8
- aggregation: maximum for seven concern constructs, minimum for reassuring stability
- inference: fully offline
- row-level scores: local only

Environment validation and preflight were completed at project commit 097bf046a1c7eceb50d71d75e82e79f3993acb00.

## Invasive ventilation

Inference job 9HN4R7T9 completed:

- expected notes: 4,499;
- successful notes: 4,499;
- failures: 0;
- outcome labels read or used during inference: no;
- declared aggregate artifact SHA-256: 2dc2e741695c2d567952f34d987d047713d36f9903ba2090ad26e963fcf9e236.

Evaluation job B7Q2M9RK completed:

| N | Cases | Notes scored | Comparator AUROC | + DiffusionGemma AUROC | Delta AUROC | 95% refit-bootstrap interval | Delta AUPRC |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 11,116 | 279 | 4,499 | 0.72468 | 0.71657 | -0.00811 | -0.02030 to +0.01445 | +0.00026 |

Five frozen-partition delta-AUROC estimates:

- -0.00811;
- -0.00892;
- -0.00108;
- -0.00478;
- +0.00423.

The primary refit bootstrap completed 500/500 valid replicates with zero replacements.

Evaluation artifact SHA-256: 126be5aa7b0af9302e39485dabdd64c291fab60c6b9abfccbf1dae553a464431.

## RRT

Inference job D4M8Q2VN completed:

- expected notes: 7,709;
- successful notes: 7,709;
- failures: 0;
- outcome labels read or used during inference: no;
- max-chunk truncations: 0;
- declared aggregate artifact SHA-256: 763056a90bbf2e5b59e86268bba624d50826689dfb2e5eb0beec3033f74f7182.

Evaluation job F7K3Q9MV completed:

| N | Cases | Notes scored | Comparator AUROC | + DiffusionGemma AUROC | Delta AUROC | 95% refit-bootstrap interval | Delta AUPRC |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 19,395 | 314 | 7,709 | 0.97394 | 0.97310 | -0.00083 | -0.00283 to +0.00244 | +0.01231 |

Five frozen-partition delta-AUROC estimates:

- -0.00083;
- -0.00037;
- +0.00047;
- -0.00038;
- +0.00324.

The primary refit bootstrap completed 500/500 valid replicates with zero replacements.

Evaluation artifact SHA-256: 179b0e6ea1ab6e4f60eeeb4027ae7c291eec51599597ce7dbcead318e884ef9a.

## MetaVision ICU death

Inference job G8M4Q2VN completed:

- expected notes: 7,889;
- successful notes: 7,889;
- failures: 0;
- outcome labels read or used during inference: no;
- max-chunk truncations: 0;
- declared aggregate artifact SHA-256: 605d5c39bec34bb36f49b7f0cc17b54bb72172e77445c91bed8433e71b32690d.

Evaluation job H9Q4M2VK is running using the frozen rich-comparator HGB procedure and 500 patient-cluster refit-bootstrap replicates. No MetaVision ICU-death DiffusionGemma outcome-performance result is available until that job is terminal and its declared aggregate artifact is read.

## Interpretation

The completed ventilation estimate does not show a clear positive incremental-discrimination gain from DiffusionGemma beyond the rich structured comparator. RRT is also essentially null: delta AUROC -0.00083 with a narrow interval spanning zero. Together, the completed DiffusionGemma outcomes do not currently support a consistent positive incremental-discrimination pattern.

This is a registered H6 sensitivity result. It does not replace the stripped-note Open-Jev H1 primary result and should not be used to select a preferred semantic instrument post hoc.

## Canonical RunRelay provenance

- environment audit: 8GN4R7T9, project commit 097bf046a1c7eceb50d71d75e82e79f3993acb00;
- ventilation inference: 9HN4R7T9, artifact SHA-256 2dc2e741695c2d567952f34d987d047713d36f9903ba2090ad26e963fcf9e236;
- ventilation evaluation: B7Q2M9RK, artifact SHA-256 126be5aa7b0af9302e39485dabdd64c291fab60c6b9abfccbf1dae553a464431;
- RRT inference: D4M8Q2VN, artifact SHA-256 763056a90bbf2e5b59e86268bba624d50826689dfb2e5eb0beec3033f74f7182;
- RRT evaluation: F7K3Q9MV, artifact SHA-256 179b0e6ea1ab6e4f60eeeb4027ae7c291eec51599597ce7dbcead318e884ef9a;
- MetaVision ICU-death inference: G8M4Q2VN, artifact SHA-256 605d5c39bec34bb36f49b7f0cc17b54bb72172e77445c91bed8433e71b32690d;
- MetaVision ICU-death evaluation: H9Q4M2VK, running at this documentation checkpoint.

Update this document only from canonical RunRelay artifacts after each terminal registered job.
