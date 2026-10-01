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

Updated: 2026-10-01.

OSF registration ahxn9 is approved/public with DOI 10.17605/OSF.IO/AHXN9. Registered v2.1 real-label analysis is underway.

Completed registered work:

- H1-H3 primary stripped-note Open-Jev analyses for invasive ventilation, RRT, and MetaVision ICU death;
- H4 six-construct analyses for all three outcomes;
- H5 common-logistic lexical comparisons for all three outcomes;
- H6 unstripped-note Open-Jev sensitivity for all three outcomes;
- H6 Laya alternative-instrument sensitivity for all three outcomes;
- H6 DiffusionGemma invasive-ventilation inference/evaluation;
- H6 DiffusionGemma RRT inference, 7,709/7,709 notes with zero failures and zero label access.

Current registered execution:

- F7K3Q9MV - H6 DiffusionGemma RRT evaluation using the frozen rich-comparator HGB procedure and 500 patient-cluster refit-bootstrap replicates.

The running scientific job remains pinned to project commit 097bf046a1c7eceb50d71d75e82e79f3993acb00. Documentation-only commits made while it runs do not change that execution.

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
