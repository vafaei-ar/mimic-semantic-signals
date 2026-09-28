# Post-registration execution deviation: legacy structured-only ventilation run

Date identified: 2026-09-28

## What happened

After the final OSF gate was validated, RunRelay job `X6M2R9Q4 — Run Ventilation Structured v2.1` executed task `evaluate_enhanced_structured_v2_1_ventilation` on commit `e22b17938101b504fee6579e2a8b52b5d780e760`.

The job completed successfully and its aggregate artifact was opened before the mismatch below was recognized.

## Mismatch

The task is a legacy enhanced-structured baseline evaluator. It does **not** implement the registered rich comparator.

Specifically, it:

- uses only the 34 structured physiology/laboratory features;
- excludes the registered treatment/support context, documentation-behavior variables, and note-context variables;
- compares a linear model with a nonlinear HGB model, rather than fitting the registered rich comparator for later pairing with the semantic augmented model;
- uses 1,000 patient-cluster bootstrap replicates applied to fixed repeat-averaged out-of-fold predictions without model refitting.

The frozen OSF registration instead defines the H1-H3 comparator as 34 structured features plus treatment/support context, documentation behavior, and note context (plus code status for ICU death). The primary uncertainty procedure for the later semantic delta-AUROC comparison is a 500-replicate patient-cluster **refit** bootstrap in which comparator and augmented models are refit together within the five primary folds.

## What was seen

The `X6M2R9Q4` aggregate artifact was opened during workflow review. It contains structured-only model performance. It contains no semantic or lexical predictors and therefore cannot estimate any registered H1-H3 semantic increment.

No RRT or ICU-death v2.1 predictive run was started after this mismatch was identified.

## Classification and handling

This is logged as a **post-registration procedural execution deviation**, not as a change to the registered estimand or model specification.

The `X6M2R9Q4` output will be retained for audit provenance but will not be used as the registered comparator result, will not determine model or feature choices, and will not modify the preregistered analysis.

Before any further real-label outcome analysis:

1. implement a rich-comparator-only evaluator that exactly matches the OSF comparator feature block and frozen five patient-grouped partitions;
2. do not use an inferential bootstrap in that preparatory comparator-only run;
3. validate the corrected code without reading additional outcome results;
4. run the rich comparator for ventilation first;
5. preserve the registered 500-replicate paired refit bootstrap for the later comparator-versus-semantic H1-H3 analysis.

The previously frozen scientific plan remains unchanged.
