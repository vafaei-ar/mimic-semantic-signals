# v2.1 semantic model and construct roster freeze

Updated: 2026-09-25

## Status

**Frozen before any v2.1 semantic or lexical inference.**

This document fixes the role of each text representation for the post-review v2.1 analysis. The roles are chosen for measurement and transport purposes, not by selecting the best v1 discrimination result.

## Primary semantic instrument

### Open-Jev

Open-Jev is the prespecified primary semantic instrument.

Reason for designation:

- it directly operationalizes the project's eight predefined typed clinical constructs;
- its outputs have a stable 0-1 typed semantic interpretation across outcomes;
- it is the project's original low-dimensional interpretable measurement instrument.

This designation is made after v1 results were already known and must be described that way in the registration. It is **not** justified by claiming Open-Jev was the best-performing v1 text model. It was not uniformly the largest v1 increment.

Primary use:

- stripped fixed-note corpus;
- eight semantic scores;
- full eligible confirmatory cohort;
- added to the richest frozen structured/treatment/documentation comparator.

## Prespecified semantic sensitivity

### Laya

Laya is a prespecified semantic-method sensitivity using the same eight constructs.

It is not a co-primary instrument and does not create a second confirmatory test family.

## Robustness and external-transport instrument

### DiffusionGemma

DiffusionGemma remains a prespecified robustness representation and the native-Chinese external-transport instrument where it has passed the prior label-free bilingual eligibility gate.

Its score semantics differ from Open-Jev typed probabilities. It therefore does not replace Open-Jev as the primary internal measurement instrument.

The prior fact that DiffusionGemma showed larger matched v1 increments for some outcomes and was the only model eligible for direct-Chinese Zigong scoring is disclosed as known background, not used to redefine it as co-primary.

## Lexical reference

### TF-IDF

TF-IDF is the prespecified high-dimensional lexical reference.

For the primary hierarchy:

- fit only within each training fold;
- use the same frozen **stripped** corpus as Open-Jev;
- unigrams + bigrams;
- lowercase;
- Unicode accent stripping;
- min_df = 5;
- max_df = 0.98;
- max_features = 10,000;
- sublinear_tf = true.

The full-note TF-IDF analysis belongs only to the full-note sensitivity.

TF-IDF is described as a lexical reference/baseline, not as a theoretical upper bound.

## Models not in the primary hierarchy

### Supervised text encoder

The supervised encoder is demoted from the primary manuscript hierarchy. Any v2.1 supervised encoder analysis would be supplementary and requires its own frozen protocol before execution.

### Historical vasopressor analysis

The earlier vasopressor work remains supplementary provenance. It is not mixed with the corrected v2.1 confirmatory results unless rebuilt under the v2.1 population and feature rules.

## Eight frozen semantic constructs

1. `overall_clinician_concern`
2. `worsening_trajectory`
3. `respiratory_concern`
4. `hemodynamic_concern`
5. `poor_treatment_response`
6. `escalation_considered`
7. `diagnostic_uncertainty`
8. `reassuring_stability`

The canonical construct wording remains in `src/semantic_schema.py`.

## State-dominant secondary analysis

A prespecified six-construct **state-dominant** analysis retains:

- overall clinician concern;
- worsening trajectory;
- respiratory concern;
- hemodynamic concern;
- diagnostic uncertainty;
- reassuring stability.

It excludes:

- poor treatment response;
- escalation considered.

The term *state-dominant* is deliberate. Respiratory and hemodynamic concern prompts can still mention support needs, so the six-score subset is not described as treatment-free or intent-free.

This is a secondary analysis. It does not replace the eight-score primary Open-Jev comparison.

## No-note handling

For the nonlinear confirmatory learner:

- `has_note` is already included in the frozen comparator;
- when `has_note = 0`, all eight semantic scores remain NaN;
- when `has_note = 1`, all eight semantic scores must be present or the analysis fails;
- no explicit semantic-by-`has_note` interaction terms are added;
- semantic NaNs are passed directly to HistGradientBoostingClassifier rather than median-imputed.

## Interpretation

The semantic layer is evaluated as low-dimensional, clinically interpretable compression of note content. A positive increment is not interpreted as proof that semantics contain information inaccessible to lexical text. The stripped TF-IDF comparison and state-dominant ablation are required to separate those claims.
