# Registered v2.1 result documents

Updated: 2026-10-01

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

The current registered continuation is T2X6P4N8, which is preparing/fixing the broad respiratory-support ventilation endpoint sensitivity inputs at project commit a96f721f1fcf76195301575110c4e5023f7511f1. No broad-endpoint semantic or predictive performance is opened by that preparation task.

The currently running job is not changed by documentation-only commits.

## Interpretation rule

Use canonical RunRelay aggregate artifacts and exact provenance for every numerical update. Do not populate a pending result from job progress, logs, or expectations.

H6 alternative instruments are sensitivities. Do not use point-estimate differences to select a preferred instrument post hoc.

The authoritative registered forward sequence is docs/10_POSTREGISTRATION_EXECUTION_AND_EXTENSION_PLAN_2026-09-30.md. The separate post-registration exploratory decision-model plan is docs/11_POSTREGISTRATION_DECISION_MODEL_EXTENSION_PLAN_2026-10-01.md.
