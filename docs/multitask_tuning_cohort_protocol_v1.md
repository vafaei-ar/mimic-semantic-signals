# Post-freeze multitask tuning cohort protocol v1

This protocol is separate from the frozen zero-shot benchmark in `docs/multitask_zero_shot_freeze_v1.md`.

It is frozen before any supervised tuning performance is examined.

## Purpose

Create patient-disjoint development and final-test cohorts for post-zero-shot supervised model development without altering or overwriting the original zero-shot cohorts or results.

## Why the original matched sets are not split directly

A read-only feasibility audit showed substantial cross-outcome patient reuse. Linking the original matched sets whenever they share any patient produced one connected component containing 986 matched sets and 2,830 patients. Preserving those original sets therefore cannot yield a balanced 70/15/15 patient-disjoint split.

The tuning phase will instead split patients before outcome matching and then rebuild matched risk sets separately inside each partition.

## Global patient partition

All MIMIC-III ICU patients are assigned once to one of three partitions using a deterministic SHA-256 hash of:

`multitask_tuning_v1|20260924|subject_id`

Thresholds:

- train: 70%
- validation: 15%
- test: 15%

The same patient partition is used for ventilation, RRT, and ICU-death cohorts. No subject may appear in more than one partition.

Source patient identifiers remain local and are never declared as RunRelay artifacts.

## Cohort reconstruction inside each partition

For each split independently, rerun the frozen benchmark construction logic with the same:

- MIMIC-III source tables
- 6-hour incident washout
- 12-hour prediction horizon for the three new outcomes
- endpoint definitions
- endpoint-specific note-language exclusions
- prospective note availability based on max(CHARTTIME, STORETIME), with CHARTTIME fallback
- empty-note exclusion
- contemporaneous structured feature extraction
- 1:3 risk-set control matching without replacement
- same-dbsource requirement
- note-category priority
- ICU elapsed-time matching limits
- controls free of prior endpoint evidence and endpoint/disqualifying evidence through the prediction horizon

Matching is performed only among patients assigned to the same split.

The original frozen zero-shot cohorts are not modified.

## Development discipline

- Train split: model parameter fitting only.
- Validation split: hyperparameter selection, early stopping, and model selection only.
- Test split: locked until the model architecture, training objective, hyperparameters, and checkpoint-selection rule are frozen.
- The final test set is evaluated once per prespecified tuned model.
- No test-set result may be used to alter tuning choices.

## Tuning interpretation

Any tuned model is a post-freeze supervised development result. It must not be described as zero-shot and must not replace the frozen zero-shot findings.

Because no independent human labels exist for the eight semantic constructs, direct outcome-supervised fine-tuning cannot automatically be claimed to preserve semantic meaning. Any outcome-supervised encoder model will therefore be treated as a predictive upper-bound/comparator unless semantic preservation is separately validated.

## Next gate

First build and audit the split-specific cohorts. Freeze their counts and integrity before specifying or running any supervised tuning objective.
