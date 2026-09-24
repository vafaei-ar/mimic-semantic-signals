# Frozen post-zero-shot tuning cohorts v1

These cohorts are frozen for supervised post-zero-shot development. They are separate from the original zero-shot benchmark and do not alter any zero-shot result.

## Source and integrity

Protocol: `docs/multitask_tuning_cohort_protocol_v1.md`

Canonical build:

- RunRelay job: `T9V4K2M7`
- task: `build_multitask_tuning_cohorts`
- exact project commit: `fea2b028cfff041ad2678c33d5b7eff40220fa33`
- aggregate manifest: `outputs/multitask_benchmark/tuning_cohort_manifest_v1.json`
- SHA-256: `3d31bf04bd5f4a334af8ee272edda1b35675fc2a56c58e43a48bc5548058295e`

The build completed before any tuning performance was examined.

## Patient partition

Patients were assigned before outcome matching by deterministic SHA-256 subject-level partition:

- train: 70%
- validation: 15%
- test: 15%
- seed: 20260924
- namespace: `multitask_tuning_v1`

Selected-cohort patient overlap is exactly zero for:

- train vs validation
- train vs test
- validation vs test

Matching was then rebuilt independently inside each split.

## Frozen counts

| Split | Outcome | Cases | Controls | Total |
| --- | --- | ---: | ---: | ---: |
| Train | Ventilation | 259 | 777 | 1,036 |
| Train | RRT | 432 | 1,296 | 1,728 |
| Train | ICU death | 1,435 | 4,305 | 5,740 |
| Validation | Ventilation | 50 | 150 | 200 |
| Validation | RRT | 75 | 225 | 300 |
| Validation | ICU death | 289 | 867 | 1,156 |
| Test | Ventilation | 55 | 165 | 220 |
| Test | RRT | 74 | 222 | 296 |
| Test | ICU death | 326 | 978 | 1,304 |

Total development notes:

- train: 8,504
- validation: 1,656
- locked test: 1,820

All outcome/split cohorts retain exact 1:3 case-control matching. There are zero blank notes. Exact note-category agreement within matched sets ranges from 98.65% to 100%.

## Locked-test rule

The test split is not to be read by training, hyperparameter search, model selection, threshold selection, or exploratory evaluation.

It may be opened only after all of the following are frozen:

1. model architecture;
2. training objective;
3. preprocessing and chunking;
4. optimization hyperparameters;
5. validation-based checkpoint-selection rule;
6. planned comparators and final test metrics.

Final test evaluation is a separate one-time phase.

## Interpretation rule

Any model developed on these cohorts is post-freeze supervised development.

Outcome-supervised encoder tuning is a predictive upper-bound/comparator and must not be described as preserving or improving the original eight semantic constructs unless semantic preservation is separately demonstrated.
