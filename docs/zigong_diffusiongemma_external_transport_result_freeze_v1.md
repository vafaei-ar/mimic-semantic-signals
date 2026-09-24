# Frozen Zigong DiffusionGemma external transport result v1

This document freezes the external narrative transport result exactly as observed. No model, prompt, threshold, translation rule, coefficient, endpoint definition, or cohort definition may be changed in response to these results.

## Canonical run

- RunRelay job: `N8V3Q6K2`
- task: `evaluate_zigong_diffusiongemma_transport`
- exact project commit: `4b2125dbf3389686ddc596681f44fe38ed5ad80d`
- artifact: `outputs/zigong_external/diffusiongemma_external_transport_v1.json`
- artifact SHA-256: `9e4d17cabde272a583147bd415643e3df4a3f01a8cf2e6b2b093f5b691177d3e`

## Frozen design

Training data:

- MIMIC-III invasive ventilation benchmark
- 365 cases, 1,095 controls, 1,460 total
- 12-hour prediction horizon
- eight DiffusionGemma semantic scores only

External data:

- Zigong 24-hour nursing-note ventilation risk-set cohort
- 85 cases, 255 controls, 340 total
- 85 complete 1:3 matched sets
- no Zigong fitting, recalibration, or threshold selection

Transport model:

- median imputation with missing indicators
- standard scaling
- logistic regression
- liblinear, C=1.0, max_iter=3000
- coefficients fitted on MIMIC only
- applied unchanged to Zigong

## Primary external result

- AUROC: **0.5906**
- 95% matched-set bootstrap CI: **0.5140 to 0.6679**
- AUPRC: **0.3738**
- 95% CI: **0.2995 to 0.4657**
- Brier score: **0.1943**
- 95% CI: **0.1860 to 0.2019**

Because the analytic cohort has artificial 25% prevalence, AUPRC is conditional on the sampled cohort and Brier score is descriptive rather than population calibration.

## Construct-level exploratory discrimination

| Construct | Zigong AUROC |
| --- | ---: |
| Respiratory concern | 0.5779 |
| Hemodynamic concern | 0.5379 |
| Poor treatment response | 0.5319 |
| Overall clinician concern | 0.5290 |
| Worsening trajectory | 0.5149 |
| Escalation considered | 0.5114 |
| Diagnostic uncertainty | 0.4903 |
| Reassuring stability, risk-oriented as 1-score | 0.4479 |

## Frozen interpretation

The MIMIC-trained semantic predictor retains **limited but non-zero discrimination** when transported to a different hospital, language, documentation system, and longer 24-hour horizon.

The confidence interval excludes 0.50 only narrowly. This is not evidence of robust cross-site equivalence, language invariance, or clinical deployment readiness.

The result is consistent with the broader project pattern:

- semantic representations capture real prospective clinical signal;
- transport is task- and setting-dependent;
- strong within-dataset discrimination does not guarantee strong external transport;
- compact semantics should be framed as interpretable compression rather than a universally sufficient representation.

## Guardrails

- DiffusionGemma was the only model eligible for direct-Chinese scoring under the frozen label-free bilingual gate.
- Open-Jev and Laya remain ineligible for direct-Chinese Zigong outcome analysis.
- No post-hoc translation, prompt adaptation, semantic threshold tuning, or Zigong-specific model fitting is permitted.
- Any future external narrative study must define its endpoint, language gate, and adaptation strategy before examining outcome performance.
