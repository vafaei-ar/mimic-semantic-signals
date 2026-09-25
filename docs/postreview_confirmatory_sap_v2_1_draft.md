# Post-review confirmatory statistical analysis plan for v2.1

## Study status and objective

This registration covers the remaining post-review v2.1 analyses. It is not an inception-stage preregistration: earlier MIMIC-III results were already available, and those results are disclosed below. No v2.1 predictive performance has been examined.

The confirmatory question is whether semantic information extracted from prospective ICU notes adds short-horizon deterioration discrimination beyond structured physiology, treatment and support state, and documentation behavior. The outcomes are invasive ventilation, renal-replacement therapy (RRT), and ICU death within 12 hours after a 12-hour ICU landmark.

All three confirmatory analyses use MetaVision stays. CareVue ICU death is analyzed separately because a label-free source audit showed that CareVue and MetaVision remain readily distinguishable from documentation behavior and structured missingness.

## Information known before registration

The team had already seen v1 results. In the earlier prevalence-preserving population analysis, the Open-Jev increment over structured physiology plus note context was +0.00338 AUROC for ventilation, -0.00075 for RRT, and +0.01332 for ICU death. Laya increments were -0.00469, -0.00033, and +0.00720. Open-Jev added +0.00537 AUROC after TF-IDF for ICU death. Documentation context itself produced a large ventilation increment, from AUROC 0.7071 with the structured model to 0.8596 after note context was added. A separate matched zero-shot benchmark showed larger ventilation and death increments for DiffusionGemma than for Open-Jev.

These observations preceded several v2.1 choices, including use of stripped text as the primary corpus and addition of treatment and documentation comparators. Open-Jev is the primary semantic instrument because it measures the eight predefined clinical constructs on one interpretable scale, not because it had the largest earlier predictive increment.

## Frozen populations and inputs

The confirmatory populations are:

| Outcome | Rows | Cases | Controls | Patients | Eligible notes |
| --- | ---: | ---: | ---: | ---: | ---: |
| Invasive ventilation | 11,116 | 279 | 10,837 | 8,982 | 4,499 |
| RRT | 19,395 | 314 | 19,081 | 15,080 | 7,709 |
| ICU death, MetaVision | 19,811 | 214 | 19,597 | 15,312 | 7,889 |

CareVue ICU death contains 25,632 rows and 306 cases and is retained as a separate replication analysis.

For each row, note identity, note time, note category, and note availability are fixed before text processing. The primary corpus removes prespecified direct endpoint or treatment expressions from that fixed note and applies no other text normalization. Before registration, the stripping vocabulary was broadened to include standalone `vent` for ventilation and `ultrafiltration` plus context-limited hemodialysis `HD` expressions for RRT; bare `HD` and bare `RRT` remain unstripped because of their clinical ambiguities. This refreeze changed 646 ventilation notes and 465 RRT notes, while the death corpora were unchanged. The unstripped prospective note is a secondary sensitivity. The primary TF-IDF analysis uses the same corrected stripped corpus.

The rich comparator contains the frozen 34-feature physiology, laboratory, and urine block; pre-landmark respiratory, vasoactive, and sedative context; death-only code status; note-documentation metadata from the prior 12 hours; and ordinary note context (availability, selected-note age, and collapsed category). It contains neither a source-system indicator nor endpoint-defining invasive-ventilation variables.

The primary learner is scikit-learn HistGradientBoostingClassifier with learning rate 0.05, 300 iterations, at most 15 leaf nodes, minimum 50 samples per leaf, L2 regularization 1.0, and early stopping disabled. These settings are fixed across outcomes. Patients without an eligible note retain has_note=0 and have all eight semantic inputs set to missing. Note-available rows must have all eight semantic scores. No explicit semantic-by-has_note interaction is added.

## Primary semantic comparison

Open-Jev applied to the stripped note is the primary semantic representation. The augmented model is identical to the rich comparator except for addition of the eight Open-Jev scores.

For each outcome, the primary estimand is:

Delta AUROC = AUROC(rich comparator + Open-Jev) - AUROC(rich comparator).

The point estimate uses the first frozen five-fold patient-grouped partition (seed 20260924). Four additional frozen partitions, using seeds 20260925 through 20260928, assess sensitivity to refitting and fold assignment.

The three outcomes are reported as separate prespecified co-primary estimands. We will not calculate confirmatory p-values, apply Holm testing, or classify an outcome as a success or failure according to whether an interval crosses zero.

## Uncertainty and stability

The primary interval uses 500 patient-cluster refit-bootstrap replicates of the complete repeat-1 five-fold cross-fitting procedure. Source patients are sampled with replacement, all ICU rows from each sampled patient are duplicated according to that patient's bootstrap multiplicity, and each patient's frozen repeat-1 fold assignment is retained. Within every replicate, both the rich comparator and rich comparator plus stripped Open-Jev are refit in all five folds. Held-out observations also retain their bootstrap multiplicity when delta-AUROC is recomputed.

Bootstrap child seeds are generated deterministically with `numpy.random.SeedSequence(20260924).spawn(500)`. The reported primary interval is the two-sided 95% percentile interval of the 500 refitted delta-AUROC estimates.

This interval captures patient-sampling and model-refit variability conditional on the frozen repeat-1 fold partition. It does not incorporate uncertainty from choosing a different fold partition; that component is addressed separately by refitting the analysis under frozen repeats 2 through 5 and reporting all five repeat-specific delta-AUROC estimates and their range.

The refit plan was retained only after a synthetic-only runtime re-audit. The earlier benchmark `Y5R7M2Q8` required 5,470 seconds for one ventilation replicate because the workstation exposed 112 CPUs to OpenMP despite a four-core task allocation. In `B6R9M4Q2`, explicit four-thread execution completed one exact five-fold replicate in 11.21 seconds, corresponding to about 1.56 serial hours for 500 ventilation replicates. The registered HGB execution contract therefore fixes `OMP_NUM_THREADS=4`, `OPENBLAS_NUM_THREADS=4`, `MKL_NUM_THREADS=4`, and `NUMEXPR_NUM_THREADS=4`.

## Precision planning

Before performance analysis, we calculated an approximate delta-AUROC detectable-effect grid from frozen case/control counts, exact note-available counts, and previously known v1 structured AUROCs. The grid used paired-score correlations of 0.80, 0.90, and 0.95. It was originally also tabulated at a conservative alpha of 0.0167 while the plan still contemplated three formal tests. That alpha is no longer part of the operative inference procedure; the grid is retained only as a planning and interpretation aid.

At correlation 0.90, the approximate 80% detectable full-cohort increments under that conservative grid were 0.0233 for ventilation, 0.0113 for RRT, and 0.0241 for MetaVision death. The corresponding note-available-only values were 0.0334, 0.0170, and 0.0385. Ventilation and MetaVision death therefore have limited precision for increments in the range previously seen in v1. Small estimates will be reported with their uncertainty rather than interpreted as evidence of no effect.

## Prespecified secondary analyses

Secondary discrimination measures include delta-AUPRC. Brier score, log loss, calibration-in-the-large, calibration slope, expected calibration error, and decision-curve summaries are also secondary.

Laya is a semantic-method sensitivity. DiffusionGemma is a robustness and external-transport representation. The six-construct state-dominant Open-Jev subset excludes poor treatment response and escalation considered but is not described as treatment-free. Additional prespecified analyses include the unstripped corpus, broad respiratory-support ventilation endpoint, timing sensitivities, CareVue death replication, and patient-shuffled semantic negative control.

The TF-IDF comparison uses a separate sparse-logistic family because the 10,000-dimensional lexical representation is not passed to HGB. For a row without an eligible note, the TF-IDF component is the all-zero sparse vector and the existing has_note indicator remains in the rich comparator. Within each training fold, the same encoded rich comparator is evaluated as comparator-only, comparator + Open-Jev, comparator + TF-IDF, and comparator + TF-IDF + Open-Jev. Semantic-versus-lexical comparisons are made within that common logistic family. The primary HGB comparison is unchanged.

The patient-shuffled semantic negative control permutes complete eight-score vectors among note-available patients within deciles of repeat-1 rich-comparator out-of-fold risk, using seed 20260929. No-note rows remain no-note rows.

## Construct and external validation

Clinician construct validation is separate from the primary predictive analysis. Blinded raters will score the eight constructs and provide a 12-hour deterioration probability. The analysis will report inter-rater reliability, same-construct agreement across methods, cross-construct discrimination, and model-human association. Direct access to MIMIC notes by raters will proceed only under the applicable PhysioNet credential/DUA requirements and after a Penn State IRB determination for the annotation activity.

Zigong will have two prespecified external arms. A local Chinese-to-English translation pipeline will be frozen without access to Zigong outcome labels; Open-Jev, Laya, and English TF-IDF will then receive the same translated text. Native-Chinese DiffusionGemma remains a separate transport analysis. Translation model and decoding settings will be fixed before labels are joined.

## Deviations and paper scope

If an implementation or data-integrity problem is found after registration, the affected analysis will stop. The date, reason, and correction will be logged before the corrected result is inspected. If the affected result has already been seen, both versions will remain in the audit trail and the supersession will be reported. A change that alters the scientific estimand requires an amended protocol.

The minimum first paper consists of the internal v2.1 confirmatory analysis, clinician construct validation, and Zigong narrative validation. Penn State narrative data, eICU/NWICU structured transport, a full equity analysis, semantic trajectories, the historical vasopressor analysis, and a rebuilt supervised encoder are outside the minimum submission set.


## Pre-registration runtime correction

The earlier runtime result `Y5R7M2Q8` is superseded as an execution-environment artifact. The workstation exposed 112 CPUs to OpenMP despite a four-core RunRelay resource request. In synthetic-only audit `B6R9M4Q2`, library-default execution did not complete one two-fit fold within 90 seconds, whereas explicit four-thread execution completed the fold in 2.18 seconds and a full exact five-fold refit replicate in 11.21 seconds. The 500-replicate patient-cluster refit bootstrap is therefore the operative primary uncertainty procedure, with OMP, OpenBLAS, MKL, and NumExpr each fixed at four threads. No v2.1 predictive performance was opened before this correction.
