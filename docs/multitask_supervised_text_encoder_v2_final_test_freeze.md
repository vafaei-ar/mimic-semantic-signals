# Frozen supervised text-encoder v2 final-test result

This document freezes the one-time locked-test result. No model, checkpoint, hyperparameter, comparator, metric definition, or test cohort may be changed in response to these results.

## Canonical final-test run

- RunRelay job: `E9R4K2M6`
- task: `evaluate_supervised_text_encoder_v2_final_test`
- exact project commit: `404633f1896a21d291045c9e330b99ee2c714472`
- aggregate artifact: `outputs/multitask_benchmark/supervised_text_encoder_v2_final_test.json`
- artifact SHA-256: `a4b7d75b15d1dc00d954500019e2262de07b71f89054cf91336902ebf4bc5102`
- selected checkpoint SHA-256: `563b21c8a53cf5c61c46677f1ee634592bd06a711e3da52616a10b2b6f9826a6`
- selected epoch: 4
- bootstrap: 2,000 matched-set cluster replicates, seed 20260924

The run completed successfully, exit code 0, with only aggregate metrics shared.

## One-time locked-test results

### Invasive ventilation

| Model | AUROC (95% CI) | AUPRC (95% CI) |
| --- | --- | --- |
| Supervised encoder v2 | 0.721 (0.651–0.789) | 0.459 (0.380–0.588) |
| Structured only | 0.628 (0.530–0.719) | 0.389 (0.303–0.518) |
| Context + TF-IDF | 0.770 (0.693–0.842) | 0.552 (0.457–0.683) |
| Structured + TF-IDF | 0.702 (0.617–0.780) | 0.462 (0.364–0.590) |

Paired AUROC differences:

- supervised encoder minus context + TF-IDF: -0.049 (95% CI -0.125 to 0.034)
- supervised encoder minus structured only: +0.093 (95% CI -0.002 to 0.193)
- structured + TF-IDF minus structured only: +0.074 (95% CI 0.033 to 0.114)

### Renal-replacement therapy

| Model | AUROC (95% CI) | AUPRC (95% CI) |
| --- | --- | --- |
| Supervised encoder v2 | 0.808 (0.755–0.857) | 0.569 (0.489–0.667) |
| Structured only | 0.961 (0.938–0.982) | 0.858 (0.776–0.938) |
| Context + TF-IDF | 0.863 (0.816–0.903) | 0.638 (0.551–0.748) |
| Structured + TF-IDF | 0.964 (0.943–0.983) | 0.866 (0.782–0.943) |

Paired AUROC differences:

- supervised encoder minus context + TF-IDF: -0.054 (95% CI -0.102 to -0.009)
- supervised encoder minus structured only: -0.152 (95% CI -0.205 to -0.108)
- structured + TF-IDF minus structured only: +0.003 (95% CI -0.0005 to 0.0085)

### ICU death

| Model | AUROC (95% CI) | AUPRC (95% CI) |
| --- | --- | --- |
| Supervised encoder v2 | 0.922 (0.904–0.937) | 0.840 (0.809–0.870) |
| Structured only | 0.875 (0.850–0.899) | 0.797 (0.760–0.833) |
| Context + TF-IDF | 0.924 (0.907–0.939) | 0.841 (0.810–0.870) |
| Structured + TF-IDF | 0.938 (0.922–0.953) | 0.877 (0.844–0.905) |

Paired AUROC differences:

- supervised encoder minus context + TF-IDF: -0.002 (95% CI -0.015 to 0.009)
- supervised encoder minus structured only: +0.047 (95% CI 0.021 to 0.073)
- structured + TF-IDF minus structured only: +0.063 (95% CI 0.048 to 0.080)

## Frozen interpretation

The supervised encoder v2 is a successful outcome-supervised predictive comparator, but it does not establish a superior general text representation.

Across the three locked outcomes:

- ICU death: the supervised encoder adds clear discrimination beyond structured data and performs essentially the same as context + TF-IDF by AUROC.
- Invasive ventilation: the supervised encoder is directionally better than structured-only prediction, but the confidence interval includes zero; context + TF-IDF has the highest lexical-only AUROC among the prespecified comparators.
- RRT: structured physiology remains dominant. The supervised encoder is materially worse than both structured-only and context + TF-IDF prediction.

These results reinforce the project-wide conclusion that note text contains reusable prospective information, but whether a learned text representation adds useful information depends strongly on how completely the endpoint is already encoded in structured clinical measurements.

The result does not overturn the frozen zero-shot conclusion that compact semantic scores are interpretable low-dimensional compression rather than uniquely predictive hidden information beyond lexical text.

## Guardrails

- The final test has been opened and evaluated once. No further model or hyperparameter tuning may use it.
- Brier scores from the 1:3 matched cohorts are descriptive only because the sampled prevalence is artificially 25%.
- The supervised encoder is not a semantic-preserving JEV model.
- Any future external validation must use models and analysis definitions frozen independently of those external results.
