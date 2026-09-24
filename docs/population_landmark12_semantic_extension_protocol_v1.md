# Population-representative semantic extension protocol v1

This protocol is frozen before Open-Jev or Laya semantic scores are evaluated against population-landmark outcome labels.

## Source population

Use the frozen 12-hour landmark prevalence-preserving cohorts:

- `docs/population_landmark12_cohort_freeze_v1.md`
- structured result freeze: `docs/population_landmark12_structured_calibration_result_freeze_v1.md`

No landmark, endpoint, horizon, or structured-feature definition may change.

## Narrative corpus

The model-free workload audit `V4R8K2Q7` identified:

- 87,009 outcome-specific note rows;
- 36,117 unique exact note texts after deduplication;
- 58.49% deduplication across outcome-specific note rows.

Inference is performed once per unique exact note text and mapped back locally to every outcome row that selected that note.

No outcome label is read or used during semantic inference.

## Frozen semantic representations

### Open-Jev

Reuse `src/22_run_open_jev_real_local.py` unchanged:

- model: `com-kotobalabs/open-jev-deberta-v3-large`
- offline local execution
- chunk size 220 tokens
- overlap 40
- maximum 8 chunks
- automatic context-safe question packing
- concern constructs aggregated by maximum across chunks
- reassuring stability aggregated by minimum across chunks

### Laya

Reuse `src/37_run_laya_real_local.py` unchanged:

- pinned local checkpoint `laya-typed-decisions-f9ab0b2`
- offline local execution
- chunk size 600 tokens
- overlap 100
- maximum 8 chunks
- concern constructs aggregated by maximum across chunks
- reassuring stability aggregated by minimum across chunks

Both use the same frozen eight semantic constructs.

## Full-population modeling rule

All outcome-observable rows remain in the analysis, including rows without an eligible note.

For no-note rows:

- `has_note = 0`;
- note category and dbsource use explicit `NO_NOTE` levels;
- note age is missing;
- semantic scores are missing;
- lexical text is the empty string.

Training-fold imputation and missingness indicators are used for missing numeric/semantic values.

## Prespecified model families

For each outcome, use the same 5 patient-grouped cross-validation folds as the frozen structured analysis.

1. **Structured**
   - the frozen 11 structured features.

2. **Structured + note context**
   - structured features;
   - note availability;
   - note category;
   - dbsource;
   - note age at landmark.

3. **Structured + note context + Open-Jev**
   - model 2 plus eight Open-Jev scores.

4. **Structured + note context + Laya**
   - model 2 plus eight Laya scores.

5. **Structured + note context + TF-IDF**
   - model 2 plus train-fold-fitted unigram+bigram TF-IDF;
   - lowercase;
   - strip accents = unicode;
   - min_df = 5;
   - max_df = 0.98;
   - max_features = 10,000;
   - sublinear_tf = true.

6. **Structured + note context + TF-IDF + Open-Jev**
   - model 5 plus eight Open-Jev scores.

7. **Structured + note context + TF-IDF + Laya**
   - model 5 plus eight Laya scores.

All classifiers use unweighted logistic regression, liblinear, C=1.0, max_iter=3000.

## Primary semantic comparisons

Primary:

- model 3 versus model 2;
- model 4 versus model 2.

Lexical-independence robustness:

- model 6 versus model 5;
- model 7 versus model 5.

The note-context baseline is required so semantic gains cannot be attributed merely to whether a note was documented or to basic note timing/category/source context.

## Metrics

Use pooled patient-grouped out-of-fold predictions.

For every model:

- AUROC
- AUPRC
- Brier score
- log loss
- calibration intercept
- calibration slope
- ECE with 10 equal-frequency bins
- the same frozen decision-curve thresholds: 0.25%, 0.5%, 0.75%, 1%, 1.5%, 2%, 3%, 5%

For the four prespecified semantic comparisons, use paired 1,000-replicate patient-cluster bootstrap confidence intervals for:

- AUROC difference;
- AUPRC difference;
- Brier difference;
- net-benefit difference at each frozen threshold.

Seed: 20260924.

## Conditional sensitivity analysis

A note-available-only analysis may be reported as a secondary sensitivity analysis, but it is not population calibration and must not replace the full-population analysis.

## Guardrails

- no semantic model is selected or discarded based on population performance;
- no threshold or landmark is changed after outcome results;
- Open-Jev and Laya inference remains fully offline;
- raw note text, source identifiers, semantic row-level scores, lexical matrices, and patient-level predictions remain local;
- only aggregate inference diagnostics and aggregate population metrics are shared.
