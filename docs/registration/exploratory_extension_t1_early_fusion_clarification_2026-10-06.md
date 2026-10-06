# Exploratory extension implementation clarification: T1.2b early fusion

Date frozen: 2026-10-06  
Branch: `extension-v2_1`  
Parent protocol: `docs/registration/exploratory_extension_protocol_v2_1_2026-10-04.md`

This clarification freezes implementation details for T1.2b before any T1.2b outcome result is computed. It does not change the predeclared 32-component embedding early-fusion analysis.

## PCA

Within every outer training sample:

- use the already frozen 1024-dimensional BGE document embeddings;
- fit PCA only on note-available rows in that outer training sample;
- use exactly 32 components;
- use scikit-learn `PCA(n_components=32, svd_solver="full")`;
- do not whiten;
- do not select the number of components from labels or performance;
- transform note-available outer-training and held-out rows with that fitted PCA.

The PCA is label-free but is refit within each outer training sample and within every patient-cluster bootstrap replicate.

## No-note rows

Rows without an eligible note receive 32 zeros for the PCA component block. Comparator D retains the already registered `has_note` and note-context features. No synthetic or imputed embedding is created for a missing note.

## HGB augmentation

The 32 PCA components are appended directly to the same comparator level D used in T1.1/T1.2 and fitted with the same frozen HGB hyperparameters.

T1.2b has no standalone text score. Its interpretation uses the T1.2 standalone embedding-score AUROC, exactly as stated in the parent protocol.

## Guardrails

- no alternative PCA dimension, solver, whitening rule, or missing-note encoding is compared;
- PCA never sees held-out rows;
- row-level PCA scores and predictions remain local;
- all five frozen partitions are reported regardless of direction;
- the timing gate and 200/500 bootstrap rule are unchanged.
