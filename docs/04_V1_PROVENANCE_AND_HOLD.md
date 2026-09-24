# 04 — v1 provenance and integrity hold

Updated: 2026-09-24

The v1 analysis history is retained because it documents the scientific development of the study. It should be read as **exploratory provenance**, not as the current manuscript result set.

## Why v1 is on hold

The integrity audit confirmed implementation/cohort issues that can materially change headline estimates.

The most important are:

1. ventilation source-system observability and `dbsource` leakage;
2. note identity/availability altered by outcome-language deletion;
3. trailing-space note-category exclusion;
4. numeric note-error rows missed;
5. inconsistent Open-Jev/Laya chunk aggregation in several evaluators;
6. asymmetric matched case/control logic;
7. eICU pre-admission lab-window clipping;
8. Zigong leakage-regex errors.

Read `docs/external_review_integrity_audit_result_freeze_v1.md` for exact counts.

## v1 analyses that remain useful for scientific context

### Original vasopressor work

Useful lessons:

- prospective narrative can contain risk information;
- semantic compression can show small incremental discrimination;
- TF-IDF often contains substantially more predictive information;
- the semantic layer should be framed as compression/interpretability rather than uniquely hidden information.

Do not use the old AUROC increments as final manuscript estimates until a corrected vasopressor lineage is explicitly rebuilt.

### Multi-outcome zero-shot work

Key historical document:

- `docs/multitask_zero_shot_freeze_v1.md`

Useful lessons:

- outcome dependence is real;
- RRT is structurally easy in the old design;
- death appeared more favorable to semantic features;
- DiffusionGemma, Open-Jev, and Laya can all function as semantic measurement instruments.

Do not treat the exact v1 increments as current evidence.

### Supervised text encoder

Key historical document:

- `docs/multitask_supervised_text_encoder_v2_final_test_freeze.md`

The locked-test result remains useful as a historical upper-bound comparison, but the cohorts belong to the v1 lineage and are not directly comparable to the corrected v2 cohort.

### Population v1 branch

Key documents:

- `docs/population_landmark12_cohort_freeze_v1.md`
- `docs/population_landmark12_structured_calibration_result_freeze_v1.md`
- `docs/population_landmark12_semantic_extension_result_freeze_v1.md`
- `docs/population_documentation_process_sensitivity_protocol_v1.md`

The large ventilation “documentation context” gain should **not** be interpreted as a real documentation-process effect. The post-result decomposition showed that category/source drove most of the jump, and the integrity audit established that source system encoded endpoint observability.

### External v1 analyses

Key documents:

- `docs/zigong_diffusiongemma_external_transport_result_freeze_v1.md`
- structured eICU/NWICU transport files/results in the repository history

These are provenance only until the affected code paths are corrected.

## What should not be resurrected without a new protocol

Do not simply rerun old scripts and call the result corrected.

A corrected analysis must use the new v2 principles:

- source-compatible outcome ascertainment;
- normalized note hygiene;
- fixed-note selection before language sensitivity;
- consistent max/min semantic aggregation;
- stronger structured comparator;
- patient-grouped repeated cross-fitting;
- corrected external feature windows/regexes.

## Historical planning documents

The following files describe earlier planning phases and should not be read as the current execution plan:

- `docs/model_tuning_plan.md`
- `docs/model_robustness_plan.md`
- old multitask tuning protocols;
- old population v1 protocols;
- old Zigong v1 protocol chain.

They remain useful for provenance and rationale.

For current work, return to:

- `docs/01_READ_FIRST.md`
- `docs/02_CURRENT_SCIENTIFIC_STATUS.md`
- `docs/03_V2_ANALYSIS_LINEAGE.md`
