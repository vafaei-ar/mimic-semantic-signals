# v2.1 registered H6 Laya alternative-instrument results

Date updated: 2026-10-01

This document records the registered H6 sensitivity in which the primary rich-comparator HGB comparison is repeated with stripped-note Laya scores instead of Open-Jev scores. The registered cohorts, rich comparator, five frozen patient-grouped partitions, HGB specification, semantic constructs, and 500-valid-replicate patient-cluster refit-bootstrap procedure are otherwise unchanged.

The Laya preflight verified package version 0.3.4, model repository `convaiinnovations/laya-typed-decisions`, local model revision `f9ab0b228f0fc0f14d873dbc99038f135c2da1b2`, the registered semantic-schema SHA-256 `72763082c314a4542817ccfcd42d2b10d9446fc8e84c3391a2140790b2483623`, 600-token chunks, 100-token overlap, and a maximum of 8 chunks.

| Outcome | N | Cases | Notes scored | Comparator AUROC | + Laya AUROC | Delta AUROC | 95% refit-bootstrap interval | Delta AUPRC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Invasive ventilation | 11,116 | 279 | 4,499 | 0.72468 | 0.73499 | +0.01031 | -0.01595 to +0.02519 | +0.00299 |
| RRT | 19,395 | 314 | 7,709 | 0.97394 | 0.97315 | -0.00079 | -0.00278 to +0.00302 | +0.00438 |
| ICU death, MetaVision | 19,811 | 214 | 7,889 | 0.93338 | 0.93479 | +0.00141 | -0.00660 to +0.00728 | +0.02129 |

Five frozen-partition Delta AUROC estimates:

- invasive ventilation: +0.01031, -0.00048, +0.01376, +0.00414, +0.00729;
- RRT: -0.00079, +0.00205, +0.00052, +0.00048, +0.00173;
- ICU death, MetaVision: +0.00141, +0.00073, -0.00054, +0.00259, +0.00260.

All three refit bootstraps completed 500/500 valid replicates with zero replacement replicates.

## Interpretation

H6 is a non-directional sensitivity analysis. Laya produces a positive primary-partition point estimate for ventilation and a small positive point estimate for MetaVision ICU death, while RRT remains close to zero. The frozen-partition estimates show that the magnitude is not uniformly stable across partitions, especially for ventilation. These results should therefore be reported as an alternative-instrument sensitivity rather than as a separate success/failure determination.

The contrast with Open-Jev is scientifically relevant because H6 asks whether conclusions materially depend on the semantic instrument. Any instrument differences should be interpreted descriptively and alongside the registered DiffusionGemma sensitivity rather than used to select a preferred instrument post hoc.

## Canonical RunRelay provenance

- validation: `V5N7R9T2`, exact project commit `6ad99424ba7df7849c0b98154d87b8d41d8ed243`;
- Laya environment preflight: `W6N7R9T2`, artifact SHA-256 `c80df5c823c52ffdca170dbc170bf185ef9b01d8291014e24a9f2b546c9a934a`;
- ventilation inference: `X7N4R9T2`, artifact SHA-256 `da82e74714b0c768d44080ae90347ae15db4f5fbff4daebf148effc2070ecde1`;
- ventilation evaluation: `Y8N4R9T2`, artifact SHA-256 `0dc443a57a2b69063a126b4dc56bef81d9faf6bd89e867321fc31b2222e9b3fc`;
- RRT inference: `Z9N4R7T2`, artifact SHA-256 `4b472319c1b202de3839cdb5a7d13af6c3846633f330bcb62acbe0fd409eb8bd`;
- RRT evaluation: `2AN4R7T9`, artifact SHA-256 `7a3c4448a63502cc71043da215efad0e51c3e428dd4583775da4b1936c59cd73`;
- MetaVision ICU-death inference: `3BN4R7T9`, artifact SHA-256 `4ad07ba32508faf42bb6fc133fa4bb1e5c70ccb4172acef26c2f4ae40e31989d`;
- MetaVision ICU-death evaluation: `4CN4R7T9`, artifact SHA-256 `a4c7ab502b880071dbd3f0cbbb35284765d4d410b835045971fef2072460d992`.

The stripped-note Open-Jev H1-H3 analyses remain primary. This document is a registered H6 sensitivity result.
