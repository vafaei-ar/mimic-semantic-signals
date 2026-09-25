# Post-review confirmatory statistical analysis plan for v2.1

**Draft status:** the scientific design is frozen before OSF registration. The original 500-replicate exact refit-bootstrap plan was superseded before any v2.1 predictive performance was examined after a synthetic exact-runtime benchmark showed it was not operationally feasible. The primary analysis is now estimation-first, with a frozen patient-cluster bootstrap of paired out-of-fold predictions and separate cross-validation repeat stability.

## Purpose and study status

This is a prospectively registered **post-review confirmatory analysis plan**, not an inception-stage preregistration. Earlier MIMIC-III analyses were already available when v2.1 was designed. The confirmatory question is whether semantic information measured from prospective ICU notes improves 12-hour deterioration discrimination after accounting for structured physiology, treatment/support state, and documentation behavior.

The three confirmatory outcomes are invasive ventilation, renal-replacement therapy (RRT), and ICU death. All confirmatory analyses use MetaVision stays. CareVue ICU death is a separate replication/sensitivity analysis because label-free audits showed strong CareVue/MetaVision differences in documentation behavior and structured missingness.

## Information known before registration

The team had seen v1 results. In the earlier prevalence-preserving population analysis, the Open-Jev increment over structured physiology plus note context was +0.00338 AUROC for ventilation, -0.00075 for RRT, and +0.01332 for ICU death. The corresponding Laya increments were -0.00469, -0.00033, and +0.00720. Open-Jev added +0.00537 AUROC after TF-IDF for ICU death. Documentation context itself had a large association with ventilation risk: AUROC increased from 0.7071 with the structured model to 0.8596 after note context was added. A separate matched zero-shot benchmark also showed larger ventilation and death increments for DiffusionGemma than for Open-Jev.

These observations preceded several v2.1 choices, including use of stripped text as the primary corpus and stronger treatment/documentation comparators. Open-Jev is nevertheless the primary semantic instrument because it directly measures the eight predefined typed clinical constructs on a common interpretable scale, not because it produced the largest earlier increment.

## Populations, text, and comparator

The frozen confirmatory populations are:

| Outcome | Rows | Cases | Controls | Patients | Eligible notes |
| --- | ---: | ---: | ---: | ---: | ---: |
| Invasive ventilation | 11,116 | 279 | 10,837 | 8,982 | 4,499 |
| RRT | 19,395 | 314 | 19,081 | 15,080 | 7,709 |
| ICU death, MetaVision | 19,811 | 214 | 19,597 | 15,312 | 7,889 |

CareVue ICU death contains 25,632 rows and 306 cases.

For every row, note identity, note time, note category, and note availability are fixed before text processing. The primary corpus removes prespecified direct endpoint/treatment expressions from the selected note and performs no other normalization. The full prospective note is a secondary sensitivity. The primary TF-IDF reference uses the same stripped corpus.

The richest comparator contains the frozen 34-feature physiology/laboratory/urine block; pre-landmark respiratory, vasoactive, sedative, and death-only code-status context; note-documentation metadata over the prior 12 hours; and ordinary note context (availability, selected-note age, and collapsed category). No source-system variable or endpoint-defining invasive-ventilation variable is included.

The primary learner is HistGradientBoostingClassifier with learning rate 0.05, 300 iterations, at most 15 leaf nodes, minimum 50 samples per leaf, L2 regularization 1.0, and early stopping disabled. Hyperparameters are not tuned on v2.1 results. For patients without an eligible note, the eight semantic inputs remain NaN and `has_note` remains in the comparator. For note-available rows, all eight scores are required.

## Primary comparison and interpretation

Open-Jev on the stripped note is the primary semantic instrument. The augmented model is identical to the rich comparator except for addition of the eight Open-Jev scores.

For each outcome,

[
\Delta AUROC =
AUROC_{rich\ comparator + Open\text{-}Jev}
-
AUROC_{rich\ comparator}.
]

The primary point estimate uses the first frozen five-fold patient-grouped partition (seed 20260924). Four additional frozen partitions assess split and refit stability.

The three outcomes are prespecified co-primary **estimands**, not three binary hypothesis tests. No confirmatory p-values are calculated and no Holm decision rule is applied. The paper reports each outcome-specific effect estimate, its frozen primary uncertainty interval, and the estimates from repeats 2–5. An outcome is not labeled a confirmatory “win” or “loss” according to whether an interval crosses zero.

## Primary uncertainty analysis

The primary uncertainty interval is a 5,000-replicate patient-cluster bootstrap of the **paired repeat-1 out-of-fold predictions without model refitting**. Source patients are sampled with replacement; every ICU row from a sampled patient is retained with that patient’s bootstrap multiplicity in both the rich-comparator and augmented prediction vectors. Each replicate recomputes the paired delta-AUROC from those resampled predictions.

Bootstrap patient samples use deterministic child seeds generated by `numpy.random.SeedSequence(20260924).spawn(5000)`. The reported primary interval is the two-sided 95% percentile interval from this distribution.

This interval is explicitly conditional on the frozen repeat-1 cross-fitted prediction functions. It quantifies patient-sampling variability of the observed discrimination contrast; it does not claim to include the full variance that would arise from retraining the models on an independently sampled cohort.

Model-refit and fold-partition sensitivity are therefore reported separately. Repeats 2–5 refit both models under four additional frozen patient-grouped partitions, and the four additional delta-AUROC estimates plus their range are reported alongside the primary estimate. This separation is deliberate: the synthetic exact-runtime benchmark showed that a 500-replicate exact refit bootstrap would require about 760 serial hours for ventilation alone with the frozen HGB specification.

## Power and interpretation

Power planning used only frozen counts, exact note-available counts, and previously known v1 structured AUROCs as planning anchors. At Holm's first-step alpha and assumed paired-prediction correlation 0.90, the approximate 80% detectable full-cohort increments are 0.0233 for ventilation, 0.0113 for RRT, and 0.0241 for ICU death. The note-available-only values are 0.0334, 0.0170, and 0.0385.

The power grid is retained as a planning and interpretation aid, not as a test-design calculation. Ventilation and MetaVision death are poorly powered for small increments in the range previously seen in v1 under many plausible paired-score correlations. The confirmatory report is therefore estimation-first: small or interval-overlapping effects are described by magnitude and uncertainty rather than as evidence of absence. Note-available-only analyses are secondary and descriptive.

## Secondary analyses

Prespecified secondary analyses include ΔAUPRC, Brier score, log loss, calibration and decision curves; Laya; DiffusionGemma; stripped-text TF-IDF; the six-construct state-dominant Open-Jev subset; full-note text; the broad respiratory-support ventilation endpoint; timing sensitivities; and CareVue death replication. These secondary analyses do not create additional co-primary estimands and are not used to redefine the primary outcome-specific estimates.

The high-dimensional lexical comparison uses a separate fixed sparse-logistic analysis family because 10,000-dimensional TF-IDF is not passed to HistGradientBoostingClassifier. Within each training fold, the same encoded rich comparator is evaluated with sparse logistic regression as comparator-only, comparator + Open-Jev, comparator + TF-IDF, and comparator + TF-IDF + Open-Jev. Direct semantic-versus-lexical conclusions are drawn within this common logistic family. The primary HGB Open-Jev comparison remains unchanged.

The state-dominant subset excludes poor treatment response and escalation considered. It is not described as treatment-free because respiratory and hemodynamic concern can still refer to support needs.

The patient-shuffled semantic negative control uses repeat-1 out-of-fold rich-comparator risk deciles. Within each outcome/source analysis, complete eight-score vectors are permuted among note-available patients within decile using seed 20260929; no-note rows remain unchanged.

## Construct and external validation

Clinician construct validation is separate from the primary predictive estimation analysis. Blinded raters will score the eight constructs and estimate 12-hour deterioration probability. Inter-rater reliability, same-construct agreement across methods, cross-construct discrimination, and model-human association will be reported.

Zigong will have two prespecified external arms. A local Chinese-to-English translation pipeline will be frozen without access to Zigong outcome labels; Open-Jev, Laya, and English TF-IDF will then receive the same translated text. Native-Chinese DiffusionGemma remains a separate transport analysis. Translation model choice and decoding parameters will be locked in a separate label-free protocol before outcomes are analyzed.

## Deviations and paper scope

If an implementation defect or data-integrity problem is found after registration, the affected analysis will stop and the date, reason, and correction will be documented before the corrected result is inspected. If the original result has already been seen, both versions will remain in the audit trail and the supersession will be reported.

The first paper requires the internal v2.1 confirmatory analysis, clinician construct validation, and Zigong narrative validation. Penn State narrative data, eICU/NWICU structured transport, a full equity analysis, semantic trajectories, the historical vasopressor analysis, and a rebuilt supervised encoder are not required for initial submission.


The initial combined benchmark `W9R6M4N2` timed out after 14,401.6 seconds before emitting an artifact because it combined full-size runtime fitting with repeated model-refit null simulations. The redesigned benchmark was validated by `X4R7M2Q8` and completed as `Y5R7M2Q8`.

One exact full-size synthetic ventilation refit-bootstrap replicate required 5,470.3 seconds. That corresponds to about 759.8 serial hours for 500 ventilation replicates alone. Because this benchmark used no real predictors or outcome labels, it provided a legitimate pre-registration basis to amend the infeasible refit-bootstrap plan without outcome-driven adaptation.

The previous 500-refit specification remains in `config/v2_1_refit_bootstrap_inference_freeze.json` with status `superseded_before_registration`. The operative inference rule is `config/v2_1_primary_inference_freeze.json`.
