# Zigong DiffusionGemma external narrative transport protocol v1

This protocol is frozen before any DiffusionGemma score is evaluated against Zigong outcome labels.

## Scientific role

This is a secondary external **site + language + temporal-horizon transport** analysis.

It tests whether the eight frozen DiffusionGemma semantic scores, combined using coefficients learned only in the frozen MIMIC invasive-ventilation cohort, retain discrimination in the independent Chinese Zigong nursing-note cohort.

It is not an exact replication because:

- MIMIC outcome horizon is 12 hours;
- Zigong outcome horizon is 24 hours because the nursing narrative cadence is approximately daily;
- Zigong event timing is restricted to within-table nursing chronology because cross-table clocks are inconsistent.

These differences must be reported explicitly.

## Frozen Zigong cohort

Protocol: `docs/zigong_ventilation_external_protocol_v1.md`

Manifest artifact from `Z7R4K9M3`:

- 85 cases
- 255 controls
- 340 total notes
- 85 matched sets
- patient unique across all 340 notes
- 1:3 case-control sampling
- zero blank predictor notes
- zero direct ventilation leakage-term hits after screening
- case predictor lead time approximately 24 hours

## Eligible model

Only DiffusionGemma is eligible under `docs/zigong_direct_chinese_model_eligibility_freeze.md`.

Frozen model:

- `google/diffusiongemma-26B-A4B-it`
- official local checkpoint
- native Hugging Face block-diffusion backend
- BF16
- fully offline
- same eight semantic constructs and prompt as the frozen MIMIC arm
- score definition: prompted 0-1 support scores, not Jev noul probabilities
- chunk size 977 tokenizer tokens
- overlap 97
- maximum 8 chunks
- concern constructs aggregated by maximum across chunks
- reassuring stability aggregated by minimum across chunks
- parse retries: 2

## Inference

Run DiffusionGemma on all 340 frozen Zigong notes without using labels during inference.

Row-level semantic scores remain local and are not declared as RunRelay artifacts.

The shared inference artifact contains only:

- expected/completed/failed note counts
- chunking and truncation diagnostics
- parse-retry counts
- score-resolution summaries
- confirmation that labels were not read or used

## Primary transported predictor

Fit one final strict semantic-only logistic model using the **full frozen MIMIC invasive-ventilation cohort**:

- inputs: the eight frozen DiffusionGemma semantic scores only
- no physiology
- no note category
- no dbsource
- no note timing/context covariates
- median imputation with missing indicators
- standard scaling
- logistic regression
- solver: `liblinear`
- C=1.0
- max_iter=3000

This exactly follows the semantic-only model family used in the frozen MIMIC DiffusionGemma evaluation.

Fit coefficients using MIMIC labels only.

Apply the fitted pipeline to Zigong scores without refitting, recalibration, threshold selection, or coefficient modification.

## Primary metric

Zigong AUROC of the transported MIMIC-trained semantic predictor.

## Secondary metrics

- AUPRC
- Brier score, descriptive only
- 95% matched-set bootstrap confidence intervals for AUROC, AUPRC, and Brier
- 2,000 bootstrap replicates
- resampling unit: Zigong matched set
- seed: 20260924

Because the Zigong analytic cohort has artificial 25% prevalence, AUPRC is conditional on the sampled cohort and Brier score is not population calibration.

## Exploratory construct-level transport

Report univariate Zigong AUROC for each semantic construct:

- positive concern constructs use the score directly;
- `reassuring_stability` is oriented as `1 - score` so higher values consistently indicate greater risk.

These construct-level results are descriptive and do not alter the primary transported model.

## Guardrails

- no model is fitted on Zigong labels;
- no coefficients are changed after seeing Zigong performance;
- no calibration or decision-curve claims are made;
- no Open-Jev or Laya outcome scoring is performed;
- no translation analysis is introduced post hoc;
- no structured cross-table comparator is used because the Zigong cross-table timing defect is frozen as unresolved;
- row-level patient predictions and notes remain local.

Once the final artifact is produced, the external result is frozen regardless of performance.
