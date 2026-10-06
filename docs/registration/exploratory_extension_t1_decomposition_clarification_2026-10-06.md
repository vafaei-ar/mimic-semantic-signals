# Exploratory extension implementation clarification: T1.5 supervised-text decomposition

Date frozen: 2026-10-06  
Branch: `extension-v2_1`  
Parent protocol: `docs/registration/exploratory_extension_protocol_v2_1_2026-10-04.md`

This clarification freezes implementation details for T1.5 before any T1.5 result is computed.

## Point-estimate decomposition

For each outcome and each of the five already frozen outer partitions:

1. reconstruct comparator levels A, B, C, and D exactly as in the existing post-registration Open-Jev decomposition;
2. within each outer training fold, regenerate the T1.1 TF-IDF training scores by five-fold patient-grouped inner cross-fitting and refit the frozen TF-IDF/logistic model on the full outer training fold for the held-out scores;
3. within the same outer training fold, regenerate the T1.2 embedding training scores by the frozen patient-grouped inner-CV procedure, including re-selection of logistic `C`, and refit on the full outer training fold for held-out scores;
4. at each comparator level, fit:
   - comparator only;
   - comparator + one TF-IDF log-odds feature;
   - comparator + one embedding log-odds feature.

No overall OOF text score generated using other outer folds is reused as an HGB training feature. This avoids allowing a text model trained with the current HGB held-out fold to generate training-row features.

## Bootstrap uncertainty

The parent protocol requests primary-partition refit-bootstrap intervals at comparator levels A and D.

One patient-cluster bootstrap replicate jointly computes all four T1.5 primary contrasts:

- TF-IDF increment at A;
- TF-IDF increment at D;
- embedding increment at A;
- embedding increment at D.

Within every replicate and outer fold, both supervised text representations and all relevant HGB models are refit from the resampled training patients.

The same mechanical Tier-1 runtime rule is used:

- time the first 10 valid frozen-seed replicates without using their performance estimates;
- median wall time x 500 <= 72 hours -> 500 valid replicates;
- median wall time x 500 > 72 hours -> 200 valid replicates;
- the final run restarts the deterministic seed sequence so those first 10 seed positions are included in the final set.

Only single-class held-out evaluations may be replaced, subject to the existing 5% replacement cap.

## Reporting

For every A-D level and frozen partition, report comparator AUROC plus TF-IDF and embedding delta AUROC. Also report delta AUPRC descriptively.

For levels A and D in the primary partition, report the refit-bootstrap 95% percentile intervals for both supervised text representations.

T1.5 remains post-registration exploratory. The decomposition is descriptive evidence about comparator richness, not causal mediation.
