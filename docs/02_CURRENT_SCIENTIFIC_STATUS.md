# 02 — Current scientific status

Updated: 2026-09-24

## Current scientific question

The study asks whether prospectively available ICU narrative documentation contains reusable information about near-term deterioration that is not fully represented by structured physiology, and whether a small set of clinically interpretable semantic scores can provide useful low-dimensional compression of that narrative information.

The project is **not** a model leaderboard. Open-Jev, Laya, and DiffusionGemma are measurement instruments. The scientific objects are the narrative signal, its incremental value, its interpretability, and its transport.

## Why the analysis was rebuilt

An external code review identified several issues in the original v1 lineage. The aggregate integrity audit confirmed the major concerns:

- ventilation outcome observability was strongly tied to MIMIC source system;
- `dbsource` could therefore act as an endpoint-observability proxy;
- outcome-language filtering changed which note was selected or whether a note existed;
- Physician and Respiratory note categories were excluded because MIMIC-III stores them with trailing spaces;
- numeric `ISERROR=1.0` rows were missed by the string filter;
- several Open-Jev/Laya evaluators averaged chunk scores even though inference stored max/min aggregation;
- 40.3% of intended eICU pre-anchor lab rows were removed by a zero-hour clipping implementation;
- the Zigong leakage regex was over-broad and its ETT boundary was broken.

The authoritative audit is `docs/external_review_integrity_audit_result_freeze_v1.md`.

All affected v1 results remain preserved for provenance but are not final manuscript evidence.

## Corrected v2 cohort

The new primary analysis uses a fixed 12-hour ICU landmark and a 12-hour prediction horizon.

| Outcome | Source rule | Rows | Cases | Prevalence | Note coverage |
| --- | --- | ---: | ---: | ---: | ---: |
| Invasive ventilation | MetaVision only | 11,126 | 280 | 2.517% | 40.47% |
| RRT | MetaVision only | 19,414 | 314 | 1.617% | 39.75% |
| ICU death | all sources | 49,546 | 537 | 1.084% | 70.91% |

Key v2 corrections:

- ventilation and RRT use source-compatible MetaVision risk sets;
- `dbsource` is not a predictor;
- note categories are whitespace-normalized;
- note error flags are parsed numerically;
- the predictor note is selected **before** any treatment-language sensitivity;
- note availability therefore no longer depends on deleting outcome-language notes;
- matched case-control sampling is no longer the primary multi-outcome design.

## Direct treatment/outcome language remains an important sensitivity

The corrected predictor note is genuinely prospective and is no longer deleted based on its text. This means some notes contain direct treatment/outcome terminology.

Among note-available rows, direct outcome-language prevalence in cases is approximately:

- ventilation: 27.4%;
- RRT: 81.8%;
- ICU death: 39.2%.

This is real prospective information, but it can make intervention prediction tautological. Therefore manuscript-facing narrative results must include a **fixed-note language-stripped sensitivity** in which the same note identity/time/category is retained and only prespecified language spans are removed.

For RRT especially, unstripped text performance cannot be interpreted as latent semantic deterioration signal.

## Stronger structured baseline

The v1 11-feature physiology baseline was too thin for the final incremental-value claim.

The corrected v2 structured comparator now contains 34 frozen raw features:

- age and sex;
- latest and 6-hour change for HR, SBP, DBP, MAP, respiratory rate, SpO2, and temperature;
- GCS eye, verbal, and motor components;
- lactate, creatinine, BUN, WBC, hemoglobin, platelets, sodium, potassium, bicarbonate, chloride, glucose, total bilirubin, INR, and blood pH;
- 6-hour net urine output.

Feature extraction completed successfully:

| Outcome | Numeric missing fraction | All-numeric-missing rows |
| --- | ---: | ---: |
| Ventilation | 9.10% | 0 |
| RRT | 7.82% | 0 |
| ICU death | 14.47% | 0 |

The exact mapping and extraction freeze are:

- `docs/enhanced_structured_baseline_mapping_freeze_v2.md`
- `docs/enhanced_structured_baseline_feature_result_freeze_v2.md`

## Active analysis

The current gate is the structured-only predictive evaluation:

**`E8R7Q5M3 — Evaluate Enhanced Structured V2`**

It uses:

- five repeats of five patient-grouped folds;
- fixed reusable split assignments;
- regularized logistic regression;
- a nonlinear histogram-gradient-boosting comparator;
- 1,000 paired patient-cluster bootstrap replicates;
- AUROC, AUPRC, Brier score, log loss, calibration, and exploratory decision-curve metrics.

No semantic, TF-IDF, note-context, or source-system feature is included.

The structured result must be frozen before corrected v2 semantic/text inference begins.

## What the older v1 results still tell us

The v1 program remains scientifically useful as **exploratory provenance**:

- narrative text clearly contains prospective information for some deterioration outcomes;
- outcome dependence is substantial;
- TF-IDF often outperforms the eight compact semantic scores;
- the eight semantic constructs are better motivated as interpretable compression than as uniquely predictive information;
- RRT is a useful example of an outcome where structured physiology can dominate;
- external transport is imperfect.

However, the numerical v1 increments should not be carried forward as manuscript headline estimates.

## Current manuscript claim status

The central claim is **not yet locked**.

A defensible candidate, if it survives the corrected v2 analyses, is:

> Low-dimensional clinically interpretable semantic measurements recover an outcome-dependent share of prospective narrative information beyond strong structured physiology, with a tradeoff between compression/interpretability and the higher predictive capacity of high-dimensional lexical text.

That claim must still survive:

1. corrected structured-only evaluation;
2. corrected semantic and TF-IDF evaluation on the same fixed patient-grouped splits;
3. fixed-note treatment-language sensitivity;
4. clinician construct validation;
5. corrected external validation.

## Lancet Digital Health readiness

The project is not yet ready for submission.

The most important remaining scientific gates are:

1. finish and freeze the corrected structured v2 baseline;
2. rerun corrected semantic and lexical comparisons using identical v2 splits;
3. quantify whether any semantic increment survives the nonlinear structured comparator;
4. perform blinded clinician construct validation with multiple raters;
5. correct/repeat affected eICU and Zigong external analyses;
6. obtain a second external narrative cohort if feasible;
7. quantify the practical value of compression: dimensionality, stability, compute, interpretability, and transport.

If corrected semantic effects become small or disappear against the nonlinear structured baseline, the paper should pivot toward **interpretable semantic compression of lexical signal** rather than “information beyond physiology.”

## Claim guardrails

Do not claim that:

- JEV/Open-Jev/Laya outperform raw text generally;
- the eight constructs contain information unavailable to lexical models;
- v1 matched-cohort or context-model estimates are current primary evidence;
- external transport is strong or deployment-ready;
- note-availability/context effects are causal;
- the supervised encoder is a semantic-preserving JEV model.

Use `docs/03_V2_ANALYSIS_LINEAGE.md` for the exact current provenance chain.


## Second-review v2.1 correction gate

A second independent code review found two additional primary corrections before the structured result can be opened:

- the current ICU-death cohort does not restrict to adults/NICU-excluded stays;
- GCS verbal currently treats ETT/tracheostomy-coded verbal responses as numeric 1.

It also confirmed a ventilation endpoint asymmetry, treatment-language regex ambiguity, split-freeze weaknesses, and important treatment/timing sensitivity needs.

These are now frozen in `docs/06_POSTREVIEW_V2_1_CORRECTIONS.md`.

Therefore `E8R7Q5M3` is no longer the manuscript-facing structured gate. Its output, if terminal, should remain unopened/unpromoted until the v2.1 cohort and feature corrections are complete and a fresh structured evaluation is run.
