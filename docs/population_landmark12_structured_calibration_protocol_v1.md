# Population-representative structured calibration and decision-curve protocol v1

This protocol is frozen before any population-level predictive performance is examined.

## Source cohort and features

Cohort freeze:

- `docs/population_landmark12_cohort_freeze_v1.md`
- cohort manifest SHA-256: `c629dd0e51bfe83a76db451b2ff4e05883880d2c5be3ea5863c8d1438c29dc72`

Structured feature extraction:

- RunRelay job: `V4M7R2Q8`
- artifact: `outputs/multitask_benchmark/population_landmark12_structured_features_v1.json`
- artifact SHA-256: `74a5a75ae8e371c9700902f6e416ffcd1ab7e02ee888216c942fe23ccdec3c3b`

The feature set is exactly:

- heart rate last and delta
- mean arterial pressure last and delta
- respiratory rate last and delta
- SpO2 last and delta
- lactate last
- creatinine last
- white blood-cell count last

Vitals use the 6 hours before the fixed 12-hour ICU landmark. Laboratory values use the 24 hours before the landmark, naturally truncated by ICU/hospital chronology. No future measurements are permitted.

## Scientific purpose

Estimate discrimination, population calibration, and decision-curve net benefit in a prevalence-preserving cohort before introducing semantic scores.

This stage evaluates the structured model only. It does not select or tune semantic models.

## Cross-fitting

For each outcome separately:

- 5-fold `StratifiedGroupKFold`
- shuffle = true
- random state = 20260924 + outcome index × 100
- grouping variable = source patient identifier
- all ICU stays from a patient remain in the same fold

Each row receives exactly one out-of-fold predicted probability.

No class balancing, undersampling, oversampling, or class weighting is used.

## Structured model

For each training fold:

1. median-impute every numeric feature using the training fold only;
2. add missingness indicators through `SimpleImputer(add_indicator=True)`;
3. standardize numeric/imputation outputs using training-fold parameters only;
4. fit logistic regression:
   - solver = `liblinear`
   - C = 1.0
   - max_iter = 3000
   - no class weighting

This is deliberately the same simple logistic family used throughout the benchmark, now fit under the true population prevalence.

## Primary metrics

Using pooled out-of-fold predictions for each outcome:

- AUROC
- AUPRC
- Brier score
- log loss
- calibration intercept and slope from logistic recalibration on logit(predicted probability)
- expected calibration error using 10 equal-frequency bins

Also report a 10-bin calibration table with:

- bin size
- mean predicted probability
- observed event probability

## Decision-curve analysis

Prespecified risk thresholds:

- 0.25%
- 0.50%
- 0.75%
- 1.00%
- 1.50%
- 2.00%
- 3.00%
- 5.00%

At each threshold, report:

- model net benefit
- treat-all net benefit
- treat-none net benefit = 0
- number and fraction classified above threshold
- true positives and false positives

Net benefit:

`TP / N - FP / N × threshold / (1 - threshold)`

The decision curve is exploratory clinical-utility evidence, not a treatment recommendation.

## Uncertainty

Use 1,000 patient-cluster bootstrap replicates with seed 20260924.

For every bootstrap replicate:

- sample unique patients with replacement;
- include all landmark rows belonging to every sampled patient, preserving multiplicity;
- do not refit the cross-fitted model;
- recompute AUROC, AUPRC, Brier, calibration slope/intercept, and net benefit at each threshold.

Report percentile 95% confidence intervals.

This bootstrap quantifies uncertainty in the out-of-fold prediction set and does not include additional model-training variability.

## Guardrails

- population prevalence is preserved;
- patient grouping prevents within-patient train/test leakage;
- no semantic scores are used;
- no performance-driven landmark or threshold changes are permitted;
- row-level predictions and patient identifiers remain local;
- only aggregate metrics, calibration bins, and decision-curve summaries are shared.

After this structured benchmark is frozen, a separately prespecified two-phase semantic analysis may be added without altering this result.
