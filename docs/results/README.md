# Registered v2.1 result documents

Updated: 2026-10-02

This directory contains aggregate manuscript-facing result summaries. Row-level restricted data and patient-level predictions remain local.

## Current result index

| Analysis | Status | Document |
|---|---|---|
| H1-H3 primary stripped-note Open-Jev | Complete | v2_1_primary_openjev_results.md |
| H4 six-construct analysis | Complete | v2_1_h4_six_construct_results.md |
| H5 common-logistic lexical comparison | Complete | v2_1_h5_lexical_results.md |
| H6 unstripped-note Open-Jev | Complete | v2_1_h6_unstripped_results.md |
| H6 Laya alternative instrument | Complete | v2_1_h6_laya_results.md |
| H6 DiffusionGemma alternative instrument | Complete | v2_1_h6_diffusiongemma_results.md |
| H6 aggregate sensitivity index | In progress | v2_1_h6_sensitivity_results.md |

## Current live registered job

The registered DiffusionGemma arm is complete for all three outcomes: ventilation delta AUROC -0.00811 (95% interval -0.02030 to +0.01445), RRT -0.00083 (-0.00283 to +0.00244), and MetaVision ICU death +0.00499 (-0.00654 to +0.00652).

The broad respiratory-support endpoint arm is complete. W4Y8P6N2 reported comparator AUROC 0.70385, augmented AUROC 0.69741, delta AUROC -0.00643, and 95% refit-bootstrap interval -0.01879 to +0.01046, with 500/500 valid bootstrap replicates and zero replacements. Artifact SHA-256: 824114f7217a3a5af6806ce6b4e413e4ec070edd865f21ee2bb60e68c3c2ea80.

Y6Z3R8M4 completed the registered CHARTEVENTS storetime preparation at validated project commit 27a061c25d88e56a155c93c83514a7a63b6cb298. Of 2,588,698 in-window CHARTEVENTS rows, 87.83% were retained after requiring nonmissing storetime at or before the landmark; 4.93% lacked storetime and 7.24% were stored after the landmark. Preparation artifact SHA-256: 9cf9de723239481a0b42604482a0186885520c7dc56df6640ac08e80d9a12901.

Z7B4R9M5 completed the invasive-ventilation storetime evaluation: comparator AUROC 0.71690, augmented AUROC 0.72358, delta AUROC +0.00668, 95% refit-bootstrap interval -0.02079 to +0.02286, with 500/500 valid bootstrap replicates and zero replacements. Artifact SHA-256: ee34846501989672c7a4e3fc2dcfb2536f0ed086fce7af9c4357b9f723bbcca4.

A8C5R2M9 is now running the RRT storetime evaluation at the same validated project commit.

The currently running job is not changed by documentation-only commits.

## Interpretation rule

Use canonical RunRelay aggregate artifacts and exact provenance for every numerical update. Do not populate a pending result from job progress, logs, or expectations.

H6 alternative instruments are sensitivities. Do not use point-estimate differences to select a preferred instrument post hoc.

The authoritative registered forward sequence is docs/10_POSTREGISTRATION_EXECUTION_AND_EXTENSION_PLAN_2026-09-30.md. The separate post-registration exploratory decision-model plan is docs/11_POSTREGISTRATION_DECISION_MODEL_EXTENSION_PLAN_2026-10-01.md.
