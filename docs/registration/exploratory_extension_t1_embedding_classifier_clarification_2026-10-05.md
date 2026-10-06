# Exploratory extension implementation clarification: T1.2 embedding classifier selection

Date frozen: 2026-10-05  
Branch: `extension-v2_1`  
Parent protocol: `docs/registration/exploratory_extension_protocol_v2_1_2026-10-04.md`

The parent protocol prespecified L2-logistic regression on the frozen embeddings with `C` chosen by inner patient-grouped cross-validation, but did not enumerate the candidate grid, optimization metric, or deterministic tie rule. This implementation clarification freezes those details before any T1.2 or T1.2b outcome evaluation and before any outcome-dependent embedding score is computed. No embedding outcome result was inspected to choose these settings.

## Candidate grid and selection metric

For every outer training sample, use exactly:

`C in {0.01, 0.1, 1, 10, 100}`.

All candidates use:

- penalty: L2;
- solver: `liblinear`;
- fit intercept: yes;
- class weight: none;
- maximum iterations: 5000;
- tolerance: `1e-4`.

Select the `C` with the highest mean AUROC across the already-frozen five inner `StratifiedGroupKFold` splits of the outer training sample. `subject_id` is the grouping variable. If multiple candidates have mean AUROC equal within `1e-12`, choose the smallest `C` (strongest regularization).

The held-out outer fold is never used for `C` selection.

## Cross-fitted training scores

After choosing one `C` for the outer training sample, regenerate the five inner-fold out-of-fold embedding log-odds using that selected `C`. Those cross-fitted scores are the only embedding-score values supplied to HGB for outer-training rows.

Then refit the same L2-logistic model with the selected `C` on all note-available rows in the outer training sample and score note-available rows in the held-out outer fold.

No-note stays receive embedding log-odds 0 while the registered `has_note` feature remains in comparator D.

This procedure intentionally performs hyperparameter selection only inside each outer training sample. The final outer-fold performance remains fully held out. No additional model family, dimensionality, calibration, threshold, or alternative embedding representation is searched.

## Bootstrap

Within every patient-cluster bootstrap replicate, repeat the same `C` selection independently inside each bootstrap outer-training sample using the same five-fold patient-grouped rule. Do not carry a `C` selected on the original sample into bootstrap replicates.

Duplicated copies of a resampled patient retain the same `subject_id` and therefore remain in one inner fold.

Any one-class inner training or validation fold, non-finite score, optimizer failure, or fold-contract violation halts the run rather than triggering an adaptive fallback.
