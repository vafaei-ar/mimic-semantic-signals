# Enhanced structured evaluation addendum v2.1

Updated: 2026-09-24

This addendum supersedes the split-freeze and calibration-reporting details of:

- `docs/enhanced_structured_baseline_evaluation_protocol_v2.md`

It does not change the prespecified linear/nonlinear model hyperparameters.

## Inputs

The v2.1 evaluation may begin only after:

1. corrected adult v2.1 cohort build;
2. v2.1 GCS-verbal-corrected structured feature extraction;
3. exact patient-grouped CV split freeze.

## Exact split freeze

The five repeated five-fold patient-grouped assignments are generated in a separate no-performance step.

For each outcome, the split-freeze step writes a local protected file containing:

- `case_id`;
- `subject_id`;
- `repeat_1_fold` through `repeat_5_fold`.

Rules:

- group = source patient;
- `StratifiedGroupKFold`;
- repeat seeds = 20260924–20260928;
- five folds per repeat;
- every patient must occupy exactly one fold within each repeat;
- existing split files may be reused only if they are byte-for-byte/deterministically identical to the frozen assignment;
- the aggregate split manifest records SHA-256 for every local split file.

The predictive evaluator **loads** these split files. It does not regenerate or overwrite them.

Later semantic/TF-IDF analyses must load the same split files and verify the same hashes.

## Expected-count assertions

The split-freeze manifest records, for each outcome:

- row count;
- case count;
- control count;
- unique-patient count;
- split-file SHA-256.

The v2.1 structured evaluator must assert those counts and hashes before fitting any model.

Once the corrected v2.1 cohort result is frozen, those counts become the downstream expected-count contract.

## Calibration terminology

Report three distinct calibration quantities:

1. **calibration-in-the-large (CITL)**
   - intercept-only recalibration with the prediction logit used as an offset;
   - ideal value 0.

2. **joint recalibration intercept**
   - intercept from logistic recalibration `logit(Y) = alpha + beta * logit(p)`;
   - interpreted jointly with slope.

3. **calibration slope**
   - beta from the same joint recalibration model;
   - ideal value 1.

Do not label the joint recalibration intercept as calibration-in-the-large.

## Bootstrap

The paired patient-cluster bootstrap remains conditional on the repeat-averaged out-of-fold predictions and does not refit models.

Report this limitation explicitly.

The bootstrap should include:

- CITL;
- joint recalibration intercept;
- calibration slope;
- AUROC;
- AUPRC;
- Brier;
- log loss;
- decision-curve net benefit.

## Result status

The pre-v2.1 job `E8R7Q5M3` is not the manuscript-facing structured result and should not be opened/frozen as such.


## Runtime hardening after pre-v2.1 timeout

The pre-v2.1 all-outcome evaluation job \`E8R7Q5M3\` reached the 240-minute RunRelay timeout after completing the ventilation outcome and entering the first RRT fold. No scientific traceback occurred, and no aggregate artifact was emitted because the evaluator wrote its output only at the very end.

The v2.1 evaluator therefore changes execution mechanics without changing the prespecified models or 1,000-bootstrap target:

- ventilation, RRT, and ICU death are separate named RunRelay tasks;
- each task uses four deterministic bootstrap workers;
- every bootstrap replicate receives a deterministic child seed derived from the frozen master seed;
- the evaluator writes a safe aggregate checkpoint after each completed outcome;
- each outcome task has a 360-minute upper bound.

These changes are operational/reproducibility fixes, not post-result model selection. The pre-v2.1 job produced no performance artifact and the v2.1 predictive performance has not been opened.


## Preregistration inferential lock

No real-label v2.1 predictive evaluator may run until `docs/registration/osf_registration.json` exists and validates as a submitted registration record. The executable runners enforce this condition.

For the eventual confirmatory semantic comparison, the planned patient-cluster refit bootstrap uses explicit duplicated patient rows rather than sample weights:

- source patients are resampled with replacement;
- all ICU rows from a resampled patient are duplicated by that patient's bootstrap multiplicity;
- each patient retains its frozen primary fold;
- within each bootstrap replicate, models are refit in each of the five primary folds;
- duplicated patients therefore cannot cross from training into testing;
- this captures patient-sampling and model-refit variability conditional on the primary fold assignment;
- it does not capture uncertainty from choosing a different fold partition, so frozen repeats 2–5 are reported separately as split-stability analyses.

The planned one-sided test is for (H_0: \Delta AUROC \le 0) against (H_1: \Delta AUROC > 0). The null-centered bootstrap p-value is

`p = (1 + count((delta_b - delta_observed) >= delta_observed)) / (B + 1)`.

Its behavior must be checked on synthetic null data before the SAP is registered. The three outcome-level primary tests will be treated as one confirmatory family with Holm multiplicity control.

The refit-bootstrap replicate count will be frozen only after the synthetic runtime benchmark. The current planning target is 500 replicates.

## Death source-proxy diagnostic before registration

For ICU death, note categories are collapsed to groups shared across CareVue and MetaVision:

- Nursing and Nursing/other -> nursing;
- Physician and Consult -> physician;
- Respiratory -> respiratory;
- General and all remaining eligible categories -> other.

A label-free diagnostic predicts CareVue versus MetaVision from the planned comparator feature matrix. AUROC above 0.80 is treated as evidence that source-system information remains strongly recoverable and blocks registration until the comparator or stratification strategy is revised.

Device-driven measurement density is not classified as documentation behavior; such variables belong to treatment/device context.
