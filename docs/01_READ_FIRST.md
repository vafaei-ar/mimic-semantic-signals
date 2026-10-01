# 01 - Read this first

Updated: 2026-10-01

This repository contains both the current corrected v2.1 manuscript-facing analysis and a substantial v1 provenance archive. The v1 files are intentionally retained because they document how the study evolved, but affected v1 numerical results are not final manuscript evidence.

## Recommended reading order

1. docs/01_READ_FIRST.md - navigation and document-status rules.
2. docs/02_CURRENT_SCIENTIFIC_STATUS.md - current scientific state and latest registered results.
3. docs/03_V2_ANALYSIS_LINEAGE.md - ordered corrected provenance from integrity audit through the current registered execution.
4. docs/04_V1_PROVENANCE_AND_HOLD.md - historical v1 evidence and why it is not manuscript-final.
5. docs/05_EXTERNAL_VALIDATION_STATUS.md - current external-validation status, including the corrected Zigong route.
6. docs/06_POSTREVIEW_V2_1_CORRECTIONS.md - historical second-review correction gate.
7. docs/07_PREREGISTRATION_READINESS_2026-09-25.md - historical preregistration checkpoint.
8. docs/08_LANCET_DIGITAL_HEALTH_ROADMAP_2026-09-25.md - current manuscript roadmap.
9. docs/09_OPUS_SYNTHETIC_CONSTRUCT_VALIDITY_PLAN_2026-09-26.md - supplementary synthetic plan.
10. docs/10_POSTREGISTRATION_EXECUTION_AND_EXTENSION_PLAN_2026-09-30.md - authoritative forward execution order.

Current aggregate result summaries are indexed in docs/results/README.md.

## Which documents are authoritative?

The numbered reports are the navigation and synthesis layer.

For exact cohort definitions, item IDs, model settings, seeds, bootstrap rules, artifact hashes, and prespecified interpretation rules, detailed frozen protocol/result documents remain authoritative.

Documents 06 and 07 intentionally preserve the state of the project at the correction and preregistration gates. They should not be rewritten to look like live status reports. When they conflict with later status, use the newest applicable frozen protocol/result plus docs/02, docs/03, and docs/10.

## Current manuscript rule

The v1 integrity hold remains in force for affected historical numerical estimates.

The manuscript-facing lineage is the corrected v2.1 registered analysis. OSF registration ahxn9 is approved/public with DOI 10.17605/OSF.IO/AHXN9.

## Current live gate

Completed:

- H1-H3 primary stripped-note Open-Jev analyses;
- H4 six-construct analyses;
- H5 common-logistic lexical comparisons;
- H6 unstripped-note Open-Jev sensitivity for all three outcomes;
- H6 Laya alternative-instrument sensitivity for all three outcomes;
- H6 DiffusionGemma invasive-ventilation inference/evaluation;
- H6 DiffusionGemma RRT inference, 7,709/7,709 notes with zero failures and zero label access.

Current execution:

- F7K3Q9MV - H6 DiffusionGemma RRT evaluation using the frozen rich-comparator HGB procedure and 500 patient-cluster refit-bootstrap replicates.

The active job is pinned to project commit 097bf046a1c7eceb50d71d75e82e79f3993acb00. Later documentation-only commits do not alter that execution.

After the DiffusionGemma RRT arm, the registered sequence continues with DiffusionGemma MetaVision ICU death, remaining H6 endpoint/timing/CareVue sensitivities, H7 shuffled negative control, H8 blinded clinician construct validation, and H9 corrected Zigong external validation.

## Current interpretation guardrail

The corrected primary Open-Jev estimates are near zero after the rich structured comparator. H5 shows small positive TF-IDF increments and negative Open-Jev increments within the same logistic family. H6 alternative-instrument results so far do not justify selecting a preferred semantic instrument post hoc.

Do not lock the manuscript claim until H6-H9 are complete.

## Naming convention

High-level reports use numbered filenames so directory listings communicate reading order. Detailed protocols and freeze documents keep descriptive filenames because they are referenced by code, jobs, historical commits, and other frozen documents.
