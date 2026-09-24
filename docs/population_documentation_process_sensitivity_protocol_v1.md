# Population documentation-process sensitivity protocol v1

Status: **post-result sensitivity protocol**, frozen after the primary population semantic result and before this sensitivity is executed.

The primary population semantic result is already frozen in:

- `docs/population_landmark12_semantic_extension_result_freeze_v1.md`

This sensitivity was motivated by the unexpectedly large predictive effect of note context, especially for invasive ventilation. It is not a new primary hypothesis and must not be used to redefine the frozen population result.

## Questions

1. Which documentation-process components explain the gain from the population note-context model?
2. Among patients who actually have an eligible prospective note, do Open-Jev or Laya semantic scores retain discrimination beyond structured physiology and note context?
3. Within that note-available conditional population, do semantic scores add anything after TF-IDF?

## Source data

Use the same frozen 12-hour population landmark cohorts, structured features, selected notes, deduplicated note mapping, Open-Jev scores, and Laya scores used by `H8M3Q7V2`.

No endpoint, landmark, note-selection rule, semantic score, or structured feature may change.

## A. Full-population documentation-context decomposition

Retain every outcome-observable row, including no-note rows.

Use the same 5-fold patient-grouped cross-validation framework and logistic regression specification as the frozen primary population semantic analysis.

Evaluate sequential models:

1. **Structured**
   - frozen 11 structured variables.

2. **Structured + note availability**
   - model 1 plus `has_note`.

3. **Structured + availability + category/source**
   - model 2 plus note category and database source with explicit `NO_NOTE` levels.

4. **Structured + full note context**
   - model 3 plus note age at the 12-hour landmark.

Report AUROC, AUPRC, Brier score, calibration intercept/slope, and paired patient-cluster bootstrap differences for:

- model 2 minus model 1;
- model 3 minus model 2;
- model 4 minus model 3;
- model 4 minus model 1.

Also report note coverage separately among cases and controls.

This decomposition is descriptive/diagnostic. It quantifies documentation-process signal and does not establish causal clinical information.

## B. Note-available-only conditional sensitivity

Restrict to rows with `has_note = 1`.

This restriction changes the target population. These results must be labeled **conditional on eligible note availability** and must not replace full-population calibration or decision-curve results.

Within this subset, use patient-grouped 5-fold cross-validation and the same unweighted logistic-regression settings.

Evaluate:

1. structured;
2. structured + note category/source/age;
3. model 2 + Open-Jev;
4. model 2 + Laya;
5. model 2 + fold-fitted TF-IDF;
6. model 5 + Open-Jev;
7. model 5 + Laya.

TF-IDF settings remain identical to the frozen primary semantic protocol:

- unigrams + bigrams;
- lowercase;
- unicode accent stripping;
- min_df = 5;
- max_df = 0.98;
- max_features = 10,000;
- sublinear_tf = true;
- fitted inside the training fold only.

Primary conditional comparisons:

- Open-Jev versus note context;
- Laya versus note context;
- Open-Jev after TF-IDF;
- Laya after TF-IDF.

Use 1,000 paired patient-cluster bootstrap replicates for AUROC, AUPRC, and Brier differences.

## Interpretation guardrails

- This analysis is post-result sensitivity work.
- No model selection or semantic tuning is allowed.
- No-note rows remain part of the frozen primary population analysis.
- The note-available subset is not the population estimand.
- Documentation-process variables may reflect workflow, severity, staffing, timing, source system, or measurement processes; predictive value must not be interpreted causally.
- Row-level predictions, note text, semantic scores, and patient identifiers remain local.
- Only aggregate metrics may be shared.
