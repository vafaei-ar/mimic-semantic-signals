# Enhanced structured baseline predictive evaluation protocol v2

Status: **frozen before any v2 structured predictive performance is examined**.

Inputs:

- corrected v2 landmark cohorts: `docs/corrected_landmark12_v2_cohort_result_freeze.md`;
- exact 34-feature structured mapping: `docs/enhanced_structured_baseline_mapping_freeze_v2.md`;
- extraction result: `docs/enhanced_structured_baseline_feature_result_freeze_v2.md`.

No semantic, TF-IDF, or language-model score may be used in this evaluation.

## Scientific purpose

This analysis establishes the performance, calibration, and decision-curve behavior of a substantially stronger prospective structured baseline before any corrected v2 narrative model is evaluated.

The structured-only result is a gate. Semantic/text claims must later be assessed against both the linear structured baseline and the stronger nonlinear structured comparator defined here.

## Outcomes

All outcomes use the corrected 12-hour landmark cohorts with a 12-hour prediction horizon:

1. invasive ventilation, MetaVision-only;
2. renal-replacement therapy, MetaVision-only;
3. ICU death, all source systems.

## Frozen input features

Use exactly the 34 raw features frozen in `docs/enhanced_structured_baseline_mapping_freeze_v2.md`.

Encoding:

- sex is encoded as a binary indicator (male=1, female=0);
- all other features remain numeric;
- no `dbsource`, note variable, semantic score, lexical feature, treatment-language indicator, or outcome-specific engineered variable is allowed.

## Missing data

All missing-data handling occurs inside each training fold.

For both models:

1. median imputation is learned on the training fold only;
2. explicit missingness indicators are added for features with missing values in the training fold.

No global imputation is allowed.

## Structured models

### Model A: regularized linear structured baseline

Pipeline:

1. training-fold median imputation + missingness indicators;
2. standardization learned on the training fold;
3. logistic regression:
   - solver: `liblinear`;
   - C = 1.0;
   - L2 penalty;
   - class_weight = None;
   - max_iter = 5000.

This is the primary calibration-oriented structured model.

### Model B: nonlinear structured comparator

Pipeline:

1. training-fold median imputation + missingness indicators;
2. histogram gradient boosting classifier:
   - loss = log loss;
   - learning_rate = 0.05;
   - max_iter = 300;
   - max_leaf_nodes = 15;
   - min_samples_leaf = 50;
   - l2_regularization = 1.0;
   - class_weight = None;
   - random_state fixed by repeat/fold.

No hyperparameter is selected using v2 outcome performance.

## Repeated patient-grouped cross-fitting

Use 5 repeats of 5-fold `StratifiedGroupKFold`.

- group: source patient;
- shuffle: true;
- repeat seeds: 20260924, 20260925, 20260926, 20260927, 20260928;
- identical splits are used for Model A and Model B within each repeat.

Every row therefore receives exactly five out-of-fold predictions from each model.

The repeat/fold assignment for every row is saved locally as a protected analysis file. Later v2 semantic and lexical models must reuse these exact assignments for the same outcome unless a separately frozen protocol explicitly justifies a different split.

The primary point prediction for each model is the mean of its five out-of-fold predictions.

Report:

- metrics from the averaged out-of-fold prediction;
- each repeat's metrics separately;
- mean, SD, minimum, and maximum across the five repeat-level metrics as a model-training/split variability diagnostic.

The repeat range is descriptive and is not presented as a confidence interval.

## Metrics

For each model and outcome:

- AUROC;
- AUPRC;
- Brier score;
- log loss;
- calibration intercept;
- calibration slope;
- expected calibration error using 10 quantile bins.

Decision-curve net benefit is reported at threshold probabilities:

- 0.25%;
- 0.5%;
- 0.75%;
- 1.0%;
- 1.5%;
- 2.0%;
- 3.0%;
- 5.0%.

Decision curves are exploratory and do not define treatment thresholds.

## Patient-cluster bootstrap

Use 1,000 paired patient-cluster bootstrap replicates on the repeat-averaged out-of-fold predictions.

Report 95% percentile intervals for each model's:

- AUROC;
- AUPRC;
- Brier score;
- log loss;
- calibration intercept;
- calibration slope;
- decision-curve net benefit.

Also report paired bootstrap intervals for Model B minus Model A in:

- AUROC;
- AUPRC;
- Brier score;
- log loss.

This bootstrap conditions on the repeated cross-fitted prediction matrices. It does not fully refit all models inside every bootstrap replicate. That limitation must be stated explicitly. The five repeated cross-fits provide a separate training/split variability diagnostic.

A full refit bootstrap may be added later only if the final semantic increment is small enough that training variability could change interpretation.

## Interpretation rule

No semantic inference begins until this structured-only result is frozen.

Later manuscript-facing semantic claims must report incremental performance against:

- Model A, for continuity/calibration;
- Model B, as the stronger nonlinear structured control.

If a semantic increment appears only against Model A but disappears against Model B, it may not be described as information beyond structured physiology in the primary claim.

## Guardrails

- preserve v1 outputs unchanged;
- prevalence-preserving cohorts only;
- no case-control sampling;
- no class weighting;
- no note/documentation variables;
- no semantic/text variables;
- no post hoc model or hyperparameter selection;
- patient grouping for every fold and bootstrap;
- row-level predictions remain local and are not declared as RunRelay artifacts.
