# 05 — External validation status

Updated: 2026-09-24

This report distinguishes **available external datasets**, **historical v1 external results**, and **what must be corrected before manuscript use**.

## Current status summary

| Dataset | Narrative available | Current role | Manuscript status |
| --- | --- | --- | --- |
| eICU | no comparable bedside narrative | structured transport | v1 affected by lab-window bug; rerun required |
| NWICU | no comparable bedside narrative | structured transport | v1 provenance; should be aligned to corrected v2 baseline |
| Zigong | Chinese nursing narratives | external narrative transport | v1 affected by leakage-regex bug; rebuild required |
| MIMIC-BR | no comparable narrative | structured cross-country validation | pending/contributor access |
| HiRID | no comparable narrative | high-frequency structured validation | pending/contributor access |
| SICdb | no comparable narrative | European structured validation | pending/contributor access |
| AmsterdamUMCdb | no comparable narrative progress notes | structured validation | separate access path |

## eICU

The integrity audit showed that the v1 eICU implementation clipped laboratory lookback at ICU-relative hour zero.

Among selected snapshots:

- 92,616 relevant laboratory rows were inside the intended 24-hour pre-anchor window;
- 37,330 had negative ICU-relative offsets;
- those 37,330 rows were excluded solely by the lower-bound clip;
- this is 40.3% of the intended relevant lab rows.

Therefore the old eICU transport estimate cannot be used as final manuscript evidence.

A corrected external structured pipeline should:

- include the full intended pre-anchor laboratory window;
- use the corrected v2 structured feature definitions where cross-dataset mapping permits;
- freeze any dataset-specific mapping before examining transported performance.

## NWICU

The specific eICU zero-hour clipping bug does not establish that NWICU is wrong.

However, the old NWICU result belongs to the v1 structured feature lineage and should be treated as provenance until it is aligned with the corrected v2 feature/model definition.

## Zigong

The v1 Zigong narrative result is not manuscript-ready.

The integrity audit found:

- the current regex did not match literal `ETT`;
- broad `气管` matching removed some `支气管`/bronchus contexts;
- generic `拔除` removed thousands of rows without another specific airway/ventilation term.

The previous DiffusionGemma transport AUROC is therefore historical provenance only.

A corrected Zigong rerun must:

- freeze a narrower leakage filter;
- preserve the corrected cohort before opening model performance;
- keep the bilingual/direct-Chinese eligibility gate separate from outcome performance;
- clearly acknowledge the 24-hour Zigong horizon versus the 12-hour MIMIC v2 horizon if that mismatch remains.

## Planned structured external datasets

### MIMIC-BR

Role:

- cross-country structured validation;
- endpoint/physiology transport.

Current state: planned/pending access or contributor approval.

### HiRID

Role:

- high-frequency physiology validation;
- useful for circulatory/organ-support endpoints.

Current state: planned/pending access or contributor approval.

### SICdb

Role:

- European ICU structured validation.

Current state: planned/pending access or contributor approval.

### AmsterdamUMCdb

Role:

- additional European structured validation.

Current state: separate access path; released free-text-style tables are not equivalent to bedside narrative progress notes.

## External narrative evidence needed

Even after correcting Zigong, the project would still benefit substantially from a second independent narrative cohort.

Structured datasets can strengthen transport/calibration claims, but they cannot establish narrative semantic transport if they lack comparable clinician-authored notes.

## Next external-analysis order

1. finish corrected MIMIC v2 primary analysis;
2. freeze corrected eICU/NWICU structured mappings;
3. rerun structured transport;
4. freeze corrected Zigong leakage/cohort protocol;
5. rerun Zigong narrative transport;
6. add MIMIC-BR/HiRID/SICdb as access permits;
7. seek another external narrative dataset.
