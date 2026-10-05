# Exploratory extension implementation clarification: T1 inner cross-fitting

Date frozen: 2026-10-05  
Branch: `extension-v2_1`  
Parent protocol: `docs/registration/exploratory_extension_protocol_v2_1_2026-10-04.md`

This implementation clarification was frozen before T1.1 outcome results were computed. It does not change the estimand, representation, model family, or predeclared interpretation table.

## Inner patient-grouped cross-fitting

For T1.1 and the scalar supervised-text component of T1.2:

- use exactly five inner folds within each outer training fold;
- construct them with scikit-learn `StratifiedGroupKFold(n_splits=5, shuffle=True)`;
- `subject_id` is the group, so no patient can appear in more than one inner fold;
- deterministic inner random state is `20261005 + 100 * outer_repeat + outer_fold` for ordinary five-partition estimation;
- for the primary-partition patient-cluster bootstrap, deterministic inner random state is `20261005 + outer_fold`; duplicated copies of a resampled patient retain the same `subject_id` and therefore remain in one inner fold;
- if any inner training split contains only one outcome class, halt. Do not replace it silently.

T1.1 uses the exact H5 TF-IDF specification and the exact H5 L2-logistic specification with fixed `C=1`; there is no T1.1 hyperparameter search.

No-note stays receive text log-odds score 0. The registered `has_note` feature remains in comparator D.

## T1.1 bootstrap seed and runtime gate

The patient-cluster refit bootstrap uses `numpy.random.SeedSequence(20260924)`, matching the registered refit-bootstrap seed lineage.

The first 10 child-seed replicates are run for wall-time measurement without reporting or inspecting their performance estimates. Their median wall time is multiplied by 500:

- projected total >72 hours -> exactly 200 valid replicates;
- otherwise -> 500 valid replicates.

The final bootstrap reruns the deterministic sequence from the first child seed, so those same first 10 frozen-seed replicates are included in the final set.

Only single-class held-out evaluations may be replaced using the next deterministic child seed, subject to the existing 5% replacement cap. Any text-model fitting error, empty vocabulary, non-finite prediction, fold-contract failure, or other non-degenerate error halts the run.
