# v2.1 pre-analysis implementation clarifications

Date: 2026-09-25

Status: frozen after OSF submission and before any v2.1 real-label predictive performance.

These choices fill implementation details that the submitted registration left open. They do not change the registered populations, outcomes, predictor blocks, estimands, model roles, cross-validation partitions, or primary uncertainty target. They are clarifications, not deviations.

## H5 sparse-logistic settings

The H5 semantic-versus-lexical comparison uses binary logistic regression with:

- L2 penalty;
- `C = 1.0`;
- `solver = liblinear`;
- `max_iter = 5000`;
- `tol = 1e-4`;
- intercept enabled;
- no class weighting.

All preprocessing is fitted within the training fold only.

For dense continuous rich-comparator variables and semantic scores, training-fold medians are used for missing-value imputation where required by logistic regression, followed by training-fold standardization to zero mean and unit variance. Binary indicators are not standardized. Categorical variables use training-fold one-hot encoding with unknown held-out categories ignored. TF-IDF remains in its prespecified sparse representation and is not re-standardized beyond the vectorizer's own normalization.

## Expected calibration error

Expected calibration error (ECE) uses 10 equal-width probability bins spanning [0,1]. Bins are left-closed and right-open except the final bin, which includes 1. Empty bins contribute zero. ECE is the sample-size-weighted mean absolute difference between observed event frequency and mean predicted probability across non-empty bins.

## Decision-curve thresholds

Decision-curve analysis uses the fixed risk thresholds:

`0.25%, 0.5%, 0.75%, 1%, 1.5%, 2%, 3%, 5%`.

These thresholds were chosen before v2.1 outcome performance and match the previously frozen population-calibration range used in this project.

## Failed bootstrap replicate rule

The primary interval targets 500 valid patient-cluster refit-bootstrap replicates.

A replicate is replaced only when AUROC is mathematically undefined because the bootstrap sample produces a held-out evaluation set with a single outcome class. Replacement uses the next deterministic child seed from the same predeclared seed sequence. The analysis records the number and reason for every replacement.

A model-fitting error, non-finite prediction, contract mismatch, unexpected exception, or other implementation failure is not silently replaced. The analysis stops and the problem is logged before any corrected result is inspected.

If more than 5% of attempted replicates require replacement for one-class degeneracy, the analysis stops for review rather than continuing automatically.

## Registration boundary

No real-label v2.1 analysis may run until the OSF record is approved, the OSF-hosted registration files have been re-downloaded and hash-verified, the DOI is recorded, and the verbatim submitted OSF form text has been imported into the repository.
