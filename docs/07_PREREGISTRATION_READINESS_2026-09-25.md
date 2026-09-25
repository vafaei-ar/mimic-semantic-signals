# v2.1 preregistration readiness checkpoint

Updated: 2026-09-25

## Status

**Temporary preregistration hold pending a synthetic HGB threading/runtime re-audit and corrected fixed-note corpus re-freeze. Real-label v2.1 predictive performance remains locked.**

Current review-candidate commit:

- project commit: `c21b8db2f214e95b8f5b6e46e0e79e23426a9035`;
- final validation job: `Z7M4Q8R2 — Validate OSF Review Candidate`;
- validation status: completed, exit 0;
- validation runtime: 3.734 seconds;
- declared validation artifact: `outputs/integrity/v2_1_preregistration_synthetic_checks.json`;
- validation artifact SHA-256: `ec869f504570d7abfea8ddc662c2caae79e9aa158f34ffc92c2e2c291a1762a3`.

No v2.1 clinical outcome performance has been opened.

## Frozen preregistration components

### Analysis populations

Confirmatory analyses are MetaVision-only:

- invasive ventilation: 11,116 rows, 279 cases;
- RRT: 19,395 rows, 314 cases;
- ICU death: 19,811 rows, 214 cases.

CareVue ICU death is a separate prespecified replication/sensitivity:

- 25,632 rows, 306 cases.

See `config/v2_1_analysis_population_contract.json`.

### Structured and context features

The corrected 34-feature physiology/laboratory/urine comparator is frozen.

The richer context comparator adds:

- source-compatible respiratory support;
- vasoactive and sedative/analgesic state;
- death-only code status;
- documentation-behavior metadata;
- ordinary note context.

The final context feature result is frozen by `G8R6Q4M2` after FiO2 normalization and note-timing deduplication.

See:

- `config/v2_1_context_feature_freeze.json`;
- `config/v2_1_context_feature_result_contract.json`.

### Fixed-note corpus

The primary corpus is the frozen language-stripped note; the full prospective note is secondary.

Canonical corpus job: `R8Q6M4N2`.

The corpus build verified that changed-note counts exactly matched the corrected direct-language flags:

- ventilation: 618;
- RRT: 347;
- MetaVision death: 797;
- CareVue death: 1,159.

See `config/v2_1_fixed_note_corpus_result_contract.json`.

### Frozen patient-grouped splits

Canonical split-freeze job: `T9R6M4N2`.

Five repeats, five folds, grouped by source patient, seeds 20260924-20260928.

Split SHA-256 values:

- ventilation: `30d6d4e591bfe3ff0dc736d8619dcead94f1c3880b160dbfed7efbffce727b35`;
- RRT: `1a2b8e23045ac79429bcb65b6ff3c382226be1fbab5a9460f2d8c1ca49bb5ee0`;
- MetaVision death: `444a0dac02358d1d4eafe83b96d3804df30134de00e4b54509beb7bbbe411658`;
- CareVue death: `490c70902518a9620a9f3c0808f2275f56652e423e8820c78a8fa4d7dca30a2f`.

See `config/v2_1_cv_split_result_contract.json`.

### Precision planning

Canonical job: `V9R6M4N2`.

At assumed paired prediction correlation 0.90, the approximate 80% detectable full-cohort delta-AUROC under the earlier conservative alpha=0.0167 planning grid was:

- ventilation: 0.0233;
- RRT: 0.0113;
- MetaVision death: 0.0241.

For note-available-only analyses:

- ventilation: 0.0334;
- RRT: 0.0170;
- MetaVision death: 0.0385.

The power calculation is planning context only; it is not the operative inferential test.

See `config/v2_1_preregistration_power_result_contract.json`.

## Exact refit-bootstrap feasibility amendment

The initial combined synthetic benchmark `W9R6M4N2` timed out after 14,401.6 seconds before producing an artifact.

The redesigned benchmark was validated by `X4R7M2Q8` and completed as `Y5R7M2Q8`.

One exact full-size ventilation five-fold patient-cluster HGB refit replicate required:

- 5,470.3 seconds (~91.2 minutes).

At that rate:

- 500 serial refit replicates would require approximately 759.8 hours for ventilation alone.

The cheap synthetic null calibration of the previously proposed one-sided bootstrap p-value rule behaved as expected:

- 2,000 null trials;
- 500 bootstrap draws per trial;
- rejection rate at alpha 0.05: 0.052;
- rejection rate at 0.05/3: 0.0155.

Because no v2.1 predictive performance had been opened, the inferential plan was amended before registration.

The superseded exact-refit plan remains in:

- `config/v2_1_refit_bootstrap_inference_freeze.json`.

The operative plan is:

- `config/v2_1_primary_inference_freeze.json`.

It uses:

- repeat-1 out-of-fold delta-AUROC as the primary estimand;
- 5,000 patient-cluster bootstrap replicates of paired frozen repeat-1 predictions for the primary conditional interval;
- repeats 2-5 as explicit refit/fold-partition stability analyses;
- no confirmatory p-values;
- no Holm testing;
- no binary success/failure rule based on interval crossing zero.

## Superseded / failed benchmark lineage

### W9R6M4N2

- failed by timeout;
- exit code 124;
- no artifact;
- superseded by the redesigned runtime benchmark.

### Y5K8R2M7

- workflow-level failure;
- no project result or artifact;
- the one-time dispatch authorization returned HTTP 409 after the same benchmark purpose had already been fulfilled by `Y5R7M2Q8`;
- no retry is needed.

### X4R7M2Q8

- completed, exit 0;
- validated the redesigned benchmark code.

### Y5R7M2Q8

- completed, exit 0;
- canonical runtime benchmark;
- artifact SHA-256: `7a2e2aadf5b26f8abe49b71f1e77a4a61d5cb9cd79568c56370121a309d422fe`.

### Z6R8M2Q4

- completed successfully;
- validated the estimation-first inference amendment;
- no clinical outcome performance.

### Z7M4Q8R2

- completed, exit 0;
- final OSF-review-candidate validation;
- 33 integrity/static tests passed;
- no clinical data or outcome performance.

## OSF-facing documents

Review candidates:

- `docs/postreview_confirmatory_sap_v2_1_draft.md`;
- `docs/postreview_confirmatory_sap_technical_appendix_v2_1_draft.md`.

The registration is explicitly described as a **post-review prospective registration of remaining v2.1 analyses**, not an inception-stage preregistration.

Previously known v1 results and their relationship to the v2.1 design choices are disclosed.

## Hard stop

The repository still fails closed before real-label evaluation.

Real-label evaluators require:

`docs/registration/osf_registration.json`

with:

- `status: registered`;
- a valid OSF registration ID;
- registration timestamp.

The example schema is:

- `docs/registration/osf_registration.example.json`.

The external OSF submission itself is a public/consequential action and is **not performed automatically by this workflow**.

## Remaining actions before predictive execution

1. Complete the synthetic-only workstation HGB threading/runtime audit and decide the final registered uncertainty procedure before OSF submission.
2. Re-materialize the fixed-note corpora after the corrected `vent`, contextual `HD`, and `ultrafiltration` stripping rules; freeze the new aggregate hashes/counts.
3. Human-review the OSF-facing SAP and technical appendix, including the final uncertainty procedure and updated corpus hashes.
4. Submit the post-review analysis plan to OSF.
5. Add the actual registration record at `docs/registration/osf_registration.json`.
6. Re-run the preregistration validation on the exact post-registration commit.
7. Only then begin real-label structured and semantic/lexical analyses.
