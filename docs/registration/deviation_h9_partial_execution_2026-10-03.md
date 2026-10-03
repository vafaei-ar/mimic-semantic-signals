# Registered H9 deviation: partial external-validation execution

Date: 2026-10-03  
Registration: OSF ahxn9, DOI 10.17605/OSF.IO/AHXN9

## Registered plan

The v2.1 SAP prespecified two Zigong external narrative arms:

1. a Chinese-to-English translation arm followed by Open-Jev, Laya, and English TF-IDF;
2. a separate native-Chinese DiffusionGemma transport arm.

The registration also required implementation/data-integrity departures to be documented without changing the scientific interpretation in response to observed performance.

## What was executed

RunRelay job `F2N7Q5K9` fit the frozen eight-score DiffusionGemma semantic-only logistic pipeline on the full corrected v2.1 MIMIC ventilation cohort and applied it unchanged to the existing 340-note Zigong 24-hour cohort.

The observed descriptive result was:

- AUROC 0.5546;
- 95% matched-set bootstrap interval 0.4796 to 0.6308;
- AUPRC 0.3030;
- descriptive Brier score 0.2390.

Canonical artifact:

- `outputs/zigong_external/h9_diffusiongemma_external_transport_v2_1.json`
- SHA-256 `14191cbef81c49dfe266500ec9eddb322254a10d17d9d82f75a1b39bf363f57f`.

No Zigong refitting, recalibration, threshold selection, coefficient modification, prompt adaptation, or post-hoc translation was performed in that run.

## Deviations identified during the 2026-10-03 external review

### 1. The registered translated arm was not performed

The Open-Jev, Laya, and TF-IDF translated-text arm prespecified in the SAP was not executed.

A later post-registration direct-Chinese eligibility freeze excluded direct Chinese Open-Jev/Laya scoring and prohibited introducing translation after outcome evaluation, but it did not erase the original registered translated arm. The translated arm is therefore reported as not performed.

### 2. The Zigong cohort was not rebuilt after the legacy leakage-screen problem was recognized

The H9 runner used:

`data/real_zigong_local/ventilation24_v1`

including the existing 340-note cohort and DiffusionGemma inference.

The cohort builder `src/82_build_zigong_ventilation24_cohort.py` contains the legacy leakage regex:

`插管|气管|气切|呼吸机|机械通气|拔管|拔除|intubat|endotracheal|tracheost|ventilat|extubat|\\bETT\\b`

This has known specification problems relevant to note exclusion, including an overbroad bare `气管` term, a generic `拔除` term, and an escaped ETT word-boundary expression that does not implement the intended regex boundary.

Repository documentation had already recognized the original Zigong leakage regex as defective. Nevertheless, the 2026-10-03 H9 evaluator reused the legacy 24-hour cohort instead of rebuilding it under a corrected screen.

This inconsistency was confirmed during external review after the H9 performance result had been opened. The result is therefore retained in the audit trail and is not relabeled as a clean confirmatory external validation.

### 3. Text-selection policy was not made fully symmetric with the corrected MIMIC corpus

The MIMIC transport model used corrected v2.1 stripped-note DiffusionGemma scores, whereas Zigong note selection came from the legacy external cohort exclusion policy above.

## Manuscript status

The existing result should be described as:

> Post-registration modified DiffusionGemma-only transport analysis using the legacy frozen Zigong 24-hour cohort.

It is descriptive supporting evidence only. It does not establish registered H9 external validation, above-chance external discrimination, language invariance, or deployment readiness.

The 95% interval includes 0.50.

## Resource decision

The Zigong cohort will not be rebuilt and the translated arm will not be run for Paper 1 because the study is single-author and unfunded and the primary registered internal analyses already provide the manuscript's evidentiary core.

The manuscript will state that external narrative transport was not completed as registered and will not rely on Zigong for its central claim.
