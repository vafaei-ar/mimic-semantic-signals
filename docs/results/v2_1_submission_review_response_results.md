# Paper 1 mock-review response metrics

Updated: 2026-10-04

This document records two bounded analyses added during pre-submission mock review.

## 1. Registered secondary metrics recovered from H1-H3

No model was rerun for this section. Brier score, log loss, calibration measures, expected calibration error, and decision-curve net benefit were already computed by the registered H1-H3 analysis code and stored in the canonical aggregate artifacts.

| Outcome | Delta Brier | 95% refit-bootstrap interval | Delta log loss | 95% refit-bootstrap interval | Calibration slope, comparator -> augmented |
|---|---:|---:|---:|---:|---:|
| Ventilation | -0.00004 | -0.00020 to +0.00024 | -0.00029 | -0.00124 to +0.00387 | 0.615 -> 0.634 |
| RRT | +0.00011 | -0.00047 to +0.00038 | +0.00073 | -0.00154 to +0.00181 | 0.713 -> 0.699 |
| ICU death, MetaVision | -0.00001 | -0.00023 to +0.00019 | +0.00074 | -0.00097 to +0.00167 | 0.762 -> 0.748 |

The 95% refit-bootstrap interval for incremental decision-curve net benefit spans zero at every prespecified threshold for all three outcomes.

These registered secondary metrics do not reveal a benefit hidden by AUROC.

## 2. Note-available frozen-prediction subgroup

This is post-registration exploratory.

The analysis restricts the already-generated full-cohort out-of-fold predictions to rows with `has_note=1`. The comparator and augmented models are not refit within the subgroup.

| Outcome | Note-available n | Cases | Repeat-1 comparator AUROC | Repeat-1 augmented AUROC | Repeat-1 delta AUROC | Five-partition delta-AUROC range |
|---|---:|---:|---:|---:|---:|---:|
| Ventilation | 4,499 | 135 | 0.697 | 0.708 | +0.0109 | -0.0158 to +0.0279 |
| RRT | 7,709 | 143 | 0.976 | 0.974 | -0.0012 | -0.0012 to +0.0043 |
| ICU death, MetaVision | 7,889 | 83 | 0.947 | 0.940 | -0.0076 | -0.0076 to +0.0068 |

The ventilation primary-partition subgroup estimate is positive, but direction is not stable across the five frozen partitions. RRT and ICU death likewise show no stable positive pattern.

This analysis therefore does not support the claim that the primary full-cohort null is explained simply by dilution from rows without an eligible note.

## Additional interpretation guardrails

- The subgroup result is exploratory and must not be presented as preregistered.
- Models were trained in the full registered cohort; this is a subgroup evaluation of frozen predictions, not subgroup refitting.
- The RRT semantic-only AUROC below 0.5 is reported without post-hoc inversion because positive-outcome orientation was frozen.
- Negative Open-Jev increments in the common-logistic H5 comparison are valid held-out results; adding predictors to a fixed regularized learner does not guarantee improved held-out discrimination.

## Provenance

- RunRelay job: `R4M8K2Q7`
- exact project commit: `88a37e1157c12360c14aa392bb434fd89dcf092c`
- artifact: `outputs/multitask_benchmark/submission_review_metrics_v2_1.json`
- artifact SHA-256: `9b22334207c7afbd6193b22acb87335f795c0d140b2a25627990d6247d3cb39b`
