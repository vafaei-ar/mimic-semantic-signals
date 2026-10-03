# 01 - Read this first

Updated: 2026-10-03

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
10. docs/10_POSTREGISTRATION_EXECUTION_AND_EXTENSION_PLAN_2026-09-30.md - authoritative registered forward execution order.
11. docs/11_POSTREGISTRATION_DECISION_MODEL_EXTENSION_PLAN_2026-10-01.md - detailed post-registration exploratory decision-model plan.
12. docs/12_MINIMAL_SUBMISSION_PLAN_2026-10-03.md - current authoritative minimal submission path and scope stop.

Current aggregate result summaries are indexed in docs/results/README.md.

## Which documents are authoritative?

The numbered reports are the navigation and synthesis layer.

For exact cohort definitions, item IDs, model settings, seeds, bootstrap rules, artifact hashes, and prespecified interpretation rules, detailed frozen protocol/result documents remain authoritative.

Documents 06 and 07 intentionally preserve the state of the project at the correction and preregistration gates. They should not be rewritten to look like live status reports. When they conflict with later status, use the newest applicable frozen protocol/result plus docs/02, docs/03, and docs/10. Docs/11 preserves a deferred exploratory decision-model plan but is not active for Paper 1. For current publication priority, remaining analyses, deviations, and stopping rules, use docs/12.

## Current manuscript rule

The v1 integrity hold remains in force for affected historical numerical estimates.

The manuscript-facing lineage is the corrected v2.1 registered analysis. OSF registration ahxn9 is approved/public with DOI 10.17605/OSF.IO/AHXN9.

## Current live gate

Completed:

- H1-H3 primary stripped-note Open-Jev analyses;
- H4 six-construct analyses;
- H5 common-logistic lexical comparisons;
- the full registered H6 sensitivity program, including unstripped notes, Laya, DiffusionGemma, broad respiratory-support endpoint, CHARTEVENTS storetime, 1-hour/2-hour laboratory lag, note-availability identity sensitivity, and the separate CareVue ICU-death replication;
- H7 patient-shuffled negative controls for ventilation, RRT, MetaVision ICU death, and CareVue ICU death;
- a post-registration modified DiffusionGemma-only Zigong transport run using the legacy frozen 24-hour cohort, AUROC 0.5546 with 95% matched-set bootstrap interval 0.4796 to 0.6308; this is descriptive only under the dated H9 deviation;
- H8 design/sample freeze: 200 uniformly sampled stripped MetaVision ICU-death notes and three blinded local rater packets were frozen before any rating, but H8 will not be performed under the dated resource deviation.

Current gate:

- H8 is formally not performed for Paper 1 because independent qualified raters/resources are unavailable;
- H9 external validation was only partially executed as registered and the existing DiffusionGemma legacy-cohort result is descriptive rather than central evidence;
- the only remaining computational work is the label-free semantic-alignment audit, semantic-only exploratory discrimination, and four-level HGB comparator decomposition;
- after those checks, complete the OSF text-level attachment comparison, freeze the manuscript provenance index, and write.

No new model panel, missingness-resilience study, OPUS workstream, external dataset, or additional sensitivity is on the Paper 1 critical path.

## Current interpretation guardrail

The corrected primary Open-Jev estimates are near zero after the rich structured comparator. H5 shows small positive TF-IDF increments and negative Open-Jev increments within the same logistic family. H6 alternative-instrument results so far do not justify selecting a preferred semantic instrument post hoc.

Do not lock the manuscript claim until H8 human construct validation is complete and the final H1-H9 provenance index is frozen.

## Naming convention

High-level reports use numbered filenames so directory listings communicate reading order. Detailed protocols and freeze documents keep descriptive filenames because they are referenced by code, jobs, historical commits, and other frozen documents.
