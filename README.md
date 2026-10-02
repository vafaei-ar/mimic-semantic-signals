# MIMIC Semantic Signals

This repository studies whether prospectively available ICU narrative documentation contains reusable information about near-term deterioration beyond structured physiology, and whether a small set of clinically interpretable semantic scores can provide useful low-dimensional compression of that narrative signal.

## Start here

The repository contains a corrected v2.1 manuscript-facing lineage and an intentionally preserved v1 provenance archive.

Read these reports in order:

1. [01 - Read this first](docs/01_READ_FIRST.md)
2. [02 - Current scientific status](docs/02_CURRENT_SCIENTIFIC_STATUS.md)
3. [03 - Corrected v2/v2.1 analysis lineage](docs/03_V2_ANALYSIS_LINEAGE.md)
4. [04 - v1 provenance and integrity hold](docs/04_V1_PROVENANCE_AND_HOLD.md)
5. [05 - External validation status](docs/05_EXTERNAL_VALIDATION_STATUS.md)
6. [06 - Post-review v2.1 correction gate](docs/06_POSTREVIEW_V2_1_CORRECTIONS.md)
7. [07 - Preregistration readiness checkpoint](docs/07_PREREGISTRATION_READINESS_2026-09-25.md)
8. [08 - Lancet Digital Health roadmap](docs/08_LANCET_DIGITAL_HEALTH_ROADMAP_2026-09-25.md)
9. [09 - OPUS synthetic construct-validity plan](docs/09_OPUS_SYNTHETIC_CONSTRUCT_VALIDITY_PLAN_2026-09-26.md)
10. [10 - Post-registration execution and extension plan](docs/10_POSTREGISTRATION_EXECUTION_AND_EXTENSION_PLAN_2026-09-30.md)
11. [11 - Exploratory decision-model extension plan](docs/11_POSTREGISTRATION_DECISION_MODEL_EXTENSION_PLAN_2026-10-01.md)

Current aggregate result documents are indexed in [docs/results/README.md](docs/results/README.md).

Detailed frozen protocols and result documents remain authoritative for exact cohort definitions, model settings, hashes, and prespecified interpretation rules.

## Current stage

Updated: 2026-10-02.

OSF registration ahxn9 is approved/public with DOI 10.17605/OSF.IO/AHXN9. Registered v2.1 real-label analysis is underway.

Completed registered work:

- H1-H3 primary stripped-note Open-Jev analyses for invasive ventilation, RRT, and MetaVision ICU death;
- H4 six-construct analyses for all three outcomes;
- H5 common-logistic lexical comparisons for all three outcomes;
- H6 unstripped-note Open-Jev sensitivity for all three outcomes;
- H6 Laya alternative-instrument sensitivity for all three outcomes;
- H6 DiffusionGemma invasive-ventilation inference/evaluation;
- H6 DiffusionGemma RRT inference/evaluation, with delta AUROC -0.00083 and 95% refit-bootstrap interval -0.00283 to +0.00244;
- H6 DiffusionGemma MetaVision ICU-death inference/evaluation, with delta AUROC +0.00499 and 95% refit-bootstrap interval -0.00654 to +0.00652;
- H6 ventilation endpoint audit: explicit-intubation is empirically identical to H1; broad respiratory support freezes 11,380 stays, 543 cases, 10,837 unchanged controls, and 4,590 note-available rows;
- H6 broad respiratory-support endpoint evaluation: delta AUROC -0.00643 with 95% refit-bootstrap interval -0.01879 to +0.01046.

Current registered execution:

- F5J2X7N4 - corrected preparation of the registered 1-hour and 2-hour laboratory-result lag sensitivities after the initial preparation failed on a structured lab-column naming bug; aggregate availability only, no predictive evaluation.

Broad-endpoint preparation T2X6P4N8 and label-free Open-Jev inference V3X7P5N9 completed cleanly at project commit a96f721f1fcf76195301575110c4e5023f7511f1. Evaluation W4Y8P6N2 completed with comparator AUROC 0.70385, augmented AUROC 0.69741, delta AUROC -0.00643, 95% refit-bootstrap interval -0.01879 to +0.01046, and 500/500 valid replicates with zero replacements. Storetime preparation Y6Z3R8M4 completed at validated commit 27a061c25d88e56a155c93c83514a7a63b6cb298. Among 2,588,698 in-window CHARTEVENTS rows, 4.93% lacked storetime, 7.24% were stored after the landmark, and 87.83% were retained. Ventilation evaluation Z7B4R9M5 completed with comparator AUROC 0.71690, augmented AUROC 0.72358, delta AUROC +0.00668, 95% refit-bootstrap interval -0.02079 to +0.02286, and 500/500 valid replicates with zero replacements. RRT evaluation A8C5R2M9 completed with comparator AUROC 0.97401, augmented AUROC 0.97453, delta AUROC +0.00053, 95% refit-bootstrap interval -0.00307 to +0.00261, and 500/500 valid replicates with zero replacements. MetaVision ICU-death evaluation B9D6R3M2 completed with comparator AUROC 0.93367, augmented AUROC 0.93160, delta AUROC -0.00207, 95% refit-bootstrap interval -0.00923 to +0.00689, and 500/500 valid replicates with zero replacements. The complete storetime sensitivity therefore does not show a consistent positive semantic increment. Initial lab-lag preparation D3G8V5N2 failed before predictive evaluation because the preparation comparison referenced `lactate`-style names instead of the actual `lactate_last` structured columns. The fix and a dedicated static assertion were validated by E4H9W6P3. Current corrected preparation F5J2X7N4 is pinned to commit 1ec1ed7d7b6117463b0ec5627eee918ff7ea22af.

The authoritative registered execution order is in [10 - Post-registration execution and extension plan](docs/10_POSTREGISTRATION_EXECUTION_AND_EXTENSION_PLAN_2026-09-30.md). The detailed post-registration decision-model extension, including Clef-Flash 9B, Clef 27B, Nimble 9B, and Tev1 4B, is frozen separately in [11 - Exploratory decision-model extension plan](docs/11_POSTREGISTRATION_DECISION_MODEL_EXTENSION_PLAN_2026-10-01.md).

## Current result direction

The corrected evidence so far does not support a clear incremental-AUROC gain from the eight Open-Jev semantic scores beyond the rich structured comparator. In the common logistic H5 comparison, TF-IDF adds small positive AUROC increments while Open-Jev adds negative increments in all three primary partitions. Registered H6 instrument sensitivities have not yet overturned that overall pattern.

The paper should therefore remain open to a framing centered on the value and limits of interpretable semantic compression rather than assuming unique predictive information beyond physiology.

## Scientific framing

The study is not a model leaderboard. Open-Jev, Laya, and DiffusionGemma are semantic measurement instruments. The scientific questions are:

- whether narrative contains prospective information beyond strong structured physiology;
- whether a small interpretable semantic representation preserves useful parts of that information;
- how much is lost relative to high-dimensional lexical text;
- whether the semantic constructs have clinician-validated meaning;
- whether the representation transports across sites and languages;
- whether compression provides practical advantages in dimensionality, runtime, stability, interpretability, or auditability.

## Data governance

Credentialed MIMIC and other restricted clinical data remain local.

The hosted Jev vendor enabled Zero Data Retention for the organization on 2026-10-01 and stated that only operational telemetry is retained under ZDR. This resolves the vendor-side retention clarification but does not by itself establish institutional or data-use permission to send restricted MIMIC notes to a third-party hosted service. Hosted Jev therefore remains outside the current restricted-data execution path unless that separate governance gate is cleared.

Do not commit or transmit raw note text, patient identifiers, row-level restricted clinical data, credentials, secrets, or unrestricted project directories containing sensitive material.

RunRelay jobs declare only safe aggregate artifacts for sharing.

## Repository organization

- docs/01_*.md through docs/11_*.md: navigation, status, historical checkpoints, registered forward plan, and exploratory extension plan.
- docs/results/: aggregate manuscript-facing registered result summaries.
- docs/*protocol*.md: frozen prespecified analysis protocols.
- docs/*freeze*.md: frozen cohort, mapping, audit, and result documents.
- src/: analysis and cohort code.
- scripts/: bounded execution wrappers.
- .runrelay/project.yaml: authoritative named RunRelay tasks.
- data/real_mimic_local/: local restricted and derived row-level data; never committed.
- outputs/: aggregate derived outputs; only explicitly declared safe artifacts may leave the workstation.

## Historical material

Early reconnaissance, v1 matched cohorts, v1 population analyses, model-tuning experiments, and v1 external validation code are intentionally retained for provenance.

Do not infer current manuscript status from old filenames or scripts. Use the numbered status documents and docs/results/README.md.
