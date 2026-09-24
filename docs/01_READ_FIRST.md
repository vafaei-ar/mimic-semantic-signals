# 01 — Read this first

Updated: 2026-09-24

This repository contains both the **current corrected v2 analysis** and a substantial **v1 provenance archive**. The v1 files are intentionally retained because they document how the study evolved, but several v1 headline results are no longer manuscript-ready after an external integrity review.

## Recommended reading order

Read these numbered reports first:

1. **`docs/01_READ_FIRST.md`** — navigation and document-status rules.
2. **`docs/02_CURRENT_SCIENTIFIC_STATUS.md`** — the current scientific state, corrected cohorts, what is known, what is on hold, and the next manuscript gates.
3. **`docs/03_V2_ANALYSIS_LINEAGE.md`** — ordered v2 provenance from integrity audit through the currently running structured evaluation.
4. **`docs/04_V1_PROVENANCE_AND_HOLD.md`** — what the older v1 analyses showed, which parts remain useful as exploratory provenance, and why they cannot be used as final manuscript evidence.
5. **`docs/05_EXTERNAL_VALIDATION_STATUS.md`** — current status of eICU, NWICU, Zigong, and planned external datasets.
6. **`docs/06_POSTREVIEW_V2_1_CORRECTIONS.md`** — the second-review corrections that now gate all manuscript-facing predictive results.

After the numbered reports, read the detailed protocol/result-freeze documents linked from `03_V2_ANALYSIS_LINEAGE.md`.

## Which documents are authoritative?

The numbered reports are the **navigation and synthesis layer**.

For exact cohort definitions, item IDs, model settings, seeds, bootstrap rules, artifact hashes, and prespecified interpretation rules, the detailed frozen protocol/result documents remain authoritative.

If a numbered synthesis and a detailed frozen document appear to conflict, use the **newest applicable v2 freeze/protocol** and treat the older text as superseded provenance.

## Current manuscript rule

The project is under a **v1 integrity hold**.

Do **not** use the older matched-cohort, population-context, eICU-v1, or Zigong-v1 estimates as final manuscript headline results.

The current manuscript-facing lineage begins with the completed integrity audit and corrected v2 cohort.

## Current live gate

The manuscript-facing gate is now the **v2.1 correction**, not the pre-v2.1 performance run.

The already-running `E8R7Q5M3` job was launched before the second review. Its result should remain unopened/unpromoted for manuscript use.

Before any structured result is frozen, the analysis must rebuild the adult v2.1 cohort, correct GCS-verbal airway handling, freeze exact split hashes, and rerun the structured evaluation.

## Naming convention going forward

New high-level reports use numbered filenames so that GitHub directory listings communicate reading order.

Detailed protocols and result freezes keep descriptive filenames because they are referenced by code, jobs, historical commits, and other freeze documents. They should not be renamed merely for aesthetics.


## Post-review v2.1 gate

A second code review identified two primary corrections that must be made before any structured-only result is opened: adult/NICU eligibility and GCS-verbal ETT handling. Additional endpoint, language, timing, split-freeze, and treatment-context sensitivities are also prespecified.

Read next:

- `docs/06_POSTREVIEW_V2_1_CORRECTIONS.md`

The current `E8R7Q5M3` output is not manuscript-facing and should not be read/frozen before the v2.1 correction is completed.
