# v2.1 registered primary Open-Jev results

Date updated: 2026-09-29

These are the registered H1-H3 results after OSF approval. All three analyses use the registered MetaVision confirmatory populations, the rich comparator, eight stripped-note Open-Jev semantic scores, five frozen patient-grouped partitions, and a 500-valid-replicate patient-cluster refit bootstrap on the primary partition. No p-values or multiplicity-adjusted decisions are used.

| Outcome | N | Cases | Notes scored | Comparator AUROC | + Open-Jev AUROC | Delta AUROC | 95% refit-bootstrap interval |
|---|---:|---:|---:|---:|---:|---:|---:|
| Invasive ventilation (H1) | 11,116 | 279 | 4,499 | 0.72468 | 0.72463 | -0.00005 | -0.02173 to 0.01910 |
| RRT (H2) | 19,395 | 314 | 7,709 | 0.97394 | 0.97315 | -0.00079 | -0.00323 to 0.00275 |
| ICU death, MetaVision (H3) | 19,811 | 214 | 7,889 | 0.93338 | 0.93126 | -0.00212 | -0.00802 to 0.00531 |

The five frozen-partition Delta AUROC estimates were:

- ventilation: -0.00005, -0.00551, -0.00505, -0.00537, +0.00922;
- RRT: -0.00079, +0.00071, +0.00003, -0.00024, +0.00332;
- ICU death: -0.00212, +0.00390, -0.00327, +0.00103, -0.00042.

All three primary refit bootstraps completed 500/500 valid replicates with zero replacement replicates.

Primary-partition AUPRC differences were +0.00387 for ventilation, -0.00048 for RRT, and +0.00087 for ICU death. These are secondary descriptive metrics.

## Interpretation

The registered point estimates for incremental AUROC are close to zero for all three outcomes after the rich comparator, source restriction, direct-language stripping, and corrected pipeline are applied. The ventilation interval remains relatively wide. RRT and MetaVision ICU-death intervals are narrower and also centered near zero. These results should be described using the registered estimation-first framework, not as binary hypothesis-test outcomes.

## Canonical RunRelay provenance

- H1 ventilation: job `T7V8M2K5`; artifact SHA-256 `238c02d25a37cd4f0238d062f70b3e58ef6653181470cfefc62895035d7b5baa`.
- H2 RRT: job `Y8M2R5K7`; artifact SHA-256 `cb8ae6d23138e03da4495998e5e2973f0f32169d513668cdd1863d82d53637d2`.
- H3 MetaVision ICU death: job `3CM7R5K9`; artifact SHA-256 `e971eae985087a40b25c164228e6d36bce90bbfb3a207b60846df50832a52a47`.

The OSF registration remains `ahxn9`, DOI `10.17605/OSF.IO/AHXN9`. The registered analysis plan and deviations/clarifications remain authoritative for interpretation and downstream analyses.
