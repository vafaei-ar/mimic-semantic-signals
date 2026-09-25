# v2.1 preregistration readiness checkpoint

Updated: 2026-09-25

## Status

**Preregistration-ready candidate pending final repository validation, human review of the OSF-facing prose, and external OSF submission. Real-label v2.1 predictive performance remains locked.**

No v2.1 clinical outcome performance, semantic inference, or TF-IDF performance has been opened.

## Frozen confirmatory populations

All three confirmatory analyses are MetaVision-only:

- invasive ventilation: 11,116 rows, 279 cases, 8,982 patients;
- RRT: 19,395 rows, 314 cases, 15,080 patients;
- ICU death: 19,811 rows, 214 cases, 15,312 patients.

CareVue ICU death is a separate prespecified replication/sensitivity:

- 25,632 rows, 306 cases, 19,736 patients.

See `config/v2_1_analysis_population_contract.json`.

## Frozen structured and context features

The corrected 34-feature physiology/laboratory/urine comparator is frozen.

The richer comparator adds:

- source-compatible respiratory support;
- vasoactive and sedative/analgesic state;
- death-only code status;
- documentation-behavior metadata;
- ordinary note context.

The final context feature layer was frozen by `G8R6Q4M2` after FiO2 normalization and note-timing deduplication.

See:

- `config/v2_1_context_feature_freeze.json`;
- `config/v2_1_context_feature_result_contract.json`.

## Corrected fixed-note corpus

The primary text corpus is the corrected language-stripped fixed note; the full prospective note is secondary.

Canonical corrected corpus job:

- `P7R4Q9V2 — Refreeze Corrected Note Corpus`;
- exact project commit: `c1d862bd76c8bb4baea61d6c48b9109b0dbae669`;
- status: completed, exit 0;
- artifact SHA-256: `b6ace04ec469261d0c25b6c685c3c027c1b5bd8154b9dc028c7baa95e1edb4a0`.

The preregistration review broadened stripping before any text inference by adding standalone `vent` and RRT-specific `ultrafiltration` plus context-limited hemodialysis `HD` expressions.

Corrected changed-note counts:

- ventilation: 646 notes, 28 more than the earlier vocabulary;
- RRT: 465 notes, 118 more than the earlier vocabulary;
- MetaVision death: 797 notes, unchanged;
- CareVue death: 1,159 notes, unchanged.

Frozen corrected stripped hashes:

- ventilation: `42ea0a0c220c9cf21354451acd621a4e8ce90494a9498082abd2197920c7fa33`;
- RRT: `3b6637762e716f8318d0c1d7b38981a6fd3cbbaf2e6b4e95d5047ac5b280c715`;
- MetaVision death: `8e60221c0c5db1074c0f14f5bd39b78252d0e5388bec8c3ca90b992c5a1a4aba`;
- CareVue death: `b322015403eb2717919b153036e0f8ce97d872ecd67c9265632e485b3ff1c6e9`.

The earlier R8 corpus contract is superseded provenance only.

See:

- `config/v2_1_language_stripping_freeze.json`;
- `config/v2_1_fixed_note_corpus_result_contract.json`;
- `docs/fixed_note_corpus_result_freeze_v2_1.md`.

## Frozen patient-grouped splits

Canonical split-freeze job: `T9R6M4N2`.

Five repeats, five folds, grouped by source patient, seeds 20260924-20260928.

Split SHA-256 values:

- ventilation: `30d6d4e591bfe3ff0dc736d8619dcead94f1c3880b160dbfed7efbffce727b35`;
- RRT: `1a2b8e23045ac79429bcb65b6ff3c382226be1fbab5a9460f2d8c1ca49bb5ee0`;
- MetaVision death: `444a0dac02358d1d4eafe83b96d3804df30134de00e4b54509beb7bbbe411658`;
- CareVue death replication: `490c70902518a9620a9f3c0808f2275f56652e423e8820c78a8fa4d7dca30a2f`.

See `config/v2_1_cv_split_result_contract.json`.

## Precision planning

Canonical planning job: `V9R6M4N2`.

At assumed paired prediction correlation 0.90, the approximate 80% detectable full-cohort delta-AUROC under the earlier conservative alpha=0.0167 planning grid was:

- ventilation: 0.0233;
- RRT: 0.0113;
- MetaVision death: 0.0241.

For note-available-only analyses:

- ventilation: 0.0334;
- RRT: 0.0170;
- MetaVision death: 0.0385.

This is planning context only. There are no operative confirmatory p-values or Holm tests.

See `config/v2_1_preregistration_power_result_contract.json`.

## Primary inference and runtime contract

The primary estimand for each confirmatory outcome is repeat-1 out-of-fold delta-AUROC:

`AUROC(rich comparator + stripped Open-Jev) - AUROC(rich comparator)`.

The primary interval is a 500-replicate patient-cluster **refit bootstrap** of the full repeat-1 five-fold cross-fitting procedure.

Each bootstrap replicate:

- samples source patients with replacement;
- duplicates all ICU rows according to patient multiplicity;
- retains the frozen repeat-1 fold assignment;
- refits both comparator and augmented HGB models in all five folds;
- retains bootstrap multiplicity in held-out AUROC calculation.

The interval is the two-sided 95% percentile interval. Repeats 2-5 provide separate refit/fold-partition stability estimates.

No confirmatory p-values are calculated, no Holm adjustment is applied, and interval crossing zero is not a binary success/failure rule.

### Runtime correction

The initial benchmark `Y5R7M2Q8` reported 5,470.3 seconds for one exact ventilation refit replicate. Synthetic-only re-audit `B6R9M4Q2` showed that this was an OpenMP/BLAS oversubscription artifact:

- library-default one-fold/two-fit audit: did not complete within 90 seconds;
- explicit one thread: 3.56 seconds for the fit work;
- explicit four threads: 2.18 seconds;
- exact five-fold four-thread replicate: 11.21 seconds;
- projected 500-replicate ventilation runtime: about 1.56 serial hours.

The HGB execution contract therefore fixes:

- `OMP_NUM_THREADS=4`;
- `OPENBLAS_NUM_THREADS=4`;
- `MKL_NUM_THREADS=4`;
- `NUMEXPR_NUM_THREADS=4`.

The interim fixed-prediction inference amendment is superseded before registration.

See `config/v2_1_primary_inference_freeze.json`.

## Important failed/superseded lineage

The following failures are retained as preregistration audit provenance and do not represent clinical result failures:

- `W9R6M4N2`: synthetic combined refit benchmark timed out; no artifact.
- `C7R4M9Q2` and `D7R4M9Q2`: validation failures while reconciling the restored refit plan and corrected stripping vocabulary.
- `G7R4M9Q2` and `J7R4M9Q2`: corrected-corpus attempts failed before completion; the artifact path collected the pre-existing R8 JSON and is **not** a new successful corpus result.
- `K7R4M9Q2`: validation failed because the still-superseded R8 result contract did not yet match the new contract schema.
- `M7R4Q9V2`: completed successfully and validated the explicit pending-refreeze state.
- `P7R4Q9V2`: completed successfully and is the canonical corrected corpus refreeze.

## OSF-facing documents

Current review candidates:

- `docs/postreview_confirmatory_sap_v2_1_draft.md`;
- `docs/postreview_confirmatory_sap_technical_appendix_v2_1_draft.md`.

They now describe:

- the corrected stripped corpus;
- the MetaVision-only confirmatory death population;
- the frozen rich comparator;
- the 500-replicate refit-bootstrap primary interval;
- the explicit four-thread HGB execution contract;
- the absence of confirmatory p-values/Holm testing;
- the known v1 results that preceded these choices;
- the deviation procedure and minimum first-paper scope.

The registration is explicitly a **prospective registration of the remaining post-review v2.1 analyses**, not an inception-stage preregistration.

## Hard stop

Real-label evaluators still fail closed unless:

`docs/registration/osf_registration.json`

exists with:

- `status: registered`;
- a valid OSF registration ID;
- a registration timestamp.

The external OSF submission is public/consequential and is not performed automatically.

## Remaining actions before predictive execution

1. Run one final synthetic/static preregistration validation on the current registration-candidate commit.
2. Human-review the main SAP and technical appendix, including prose and metadata.
3. Submit the post-review analysis plan to OSF.
4. Add the actual registration record at `docs/registration/osf_registration.json`.
5. Validate the exact post-registration commit.
6. Only then begin real-label structured, semantic, and lexical analyses.
