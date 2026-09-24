# One-time supervised text-encoder v2 locked-test protocol

This protocol is frozen before the locked test split is opened.

## Frozen development lineage

Development result:

- RunRelay job: `Y8R4K2M7`
- development artifact: `outputs/multitask_benchmark/supervised_text_encoder_development_v2.json`
- development artifact SHA-256: `755dcdd4cfbb695cb6f2d52101e0256c3ee30d4b70cd04fd2cb2e9765ebfa99f`
- selected epoch: 4

Checkpoint freeze audit:

- RunRelay job: `C7R4K9M2`
- audit artifact: `outputs/multitask_benchmark/supervised_text_encoder_v2_checkpoint_audit.json`
- audit artifact SHA-256: `73c4a80251e9d36e3eda55ea1c59f35b1e414740a76358ab8647d12401d66ac9`
- selected local checkpoint SHA-256: `563b21c8a53cf5c61c46677f1ee634592bd06a711e3da52616a10b2b6f9826a6`
- checkpoint size: 1,736,227,398 bytes

The final evaluator must verify the checkpoint SHA-256 before opening any test file. A mismatch aborts the run.

## Locked test cohorts

Frozen in `docs/multitask_tuning_cohort_freeze_v1.md`.

| Outcome | Cases | Controls | Total |
| --- | ---: | ---: | ---: |
| Invasive ventilation | 55 | 165 | 220 |
| Renal-replacement therapy | 74 | 222 | 296 |
| ICU death | 326 | 978 | 1,304 |

Patients are disjoint from train and validation by construction.

## Models evaluated

No model or hyperparameter selection occurs on test.

### 1. Supervised encoder v2

- selected epoch-4 checkpoint only
- Open-Jev DeBERTa-v3-large initialization
- shared encoder with three binary outcome heads
- CLS chunk representation
- chunk size 384 tokens
- overlap 64
- maximum 5 chunks
- note logit = maximum assigned-outcome chunk logit

### 2. Structured-only logistic baseline

Fit separately for each outcome using train only.

Features follow the frozen benchmark conventions:

- numerical physiology/labs plus hours since ICU
- median imputation with missing indicators
- standard scaling
- one-hot encoding for note category and dbsource
- logistic regression, `liblinear`, C=1.0, max_iter=3000

### 3. Context + TF-IDF lexical baseline

Fit separately for each outcome using train only.

- note text unigram + bigram TF-IDF
- lowercase
- Unicode accent stripping
- min_df=5
- max_df=0.98
- max_features=10,000
- sublinear_tf=true
- vocabulary fit on train only
- combined with hours since ICU, note category, and dbsource
- logistic regression, `liblinear`, C=1.0, max_iter=3000

This is the same lexical-control family used in the frozen zero-shot benchmark.

### 4. Structured + TF-IDF baseline

Same structured features and TF-IDF representation, fit on train only and concatenated before logistic regression.

This provides the strongest simple high-dimensional comparator.

## Primary test metrics

Reported separately for each outcome:

- AUROC
- AUPRC
- Brier score

Because the locked cohorts are 1:3 matched case-control samples, Brier score is descriptive only and is not interpreted as population calibration.

## Uncertainty

Use 2,000 matched-set cluster bootstrap replicates per outcome with seed 20260924.

Report bootstrap 95% percentile intervals for AUROC and AUPRC for each model.

Prespecified paired AUROC differences:

1. supervised encoder v2 minus context + TF-IDF
2. supervised encoder v2 minus structured-only
3. structured + TF-IDF minus structured-only

All differences use the same sampled matched sets within each bootstrap replicate.

## Reporting guardrails

- no patient-level predictions are shared;
- no note text is shared;
- no source patient identifiers are shared;
- only aggregate metrics and bootstrap intervals are declared artifacts;
- the test result does not alter the zero-shot benchmark;
- the supervised encoder remains an outcome-supervised predictive upper-bound/comparator, not a semantic-preserving JEV model;
- no calibration or decision-curve claim is made from the matched 25% prevalence cohort.

## One-time rule

The locked test split is opened once under this protocol.

If execution fails before producing test predictions because of an operational error, the same code/commit may be rerun only after diagnosing the operational failure. If a complete test artifact is produced, no model, checkpoint, hyperparameter, comparator, or metric definition may be changed in response to the observed test performance.
