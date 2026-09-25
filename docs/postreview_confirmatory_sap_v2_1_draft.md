# Post-review confirmatory statistical analysis plan for v2.1

**Draft status:** the design is frozen. The patient-cluster refit-bootstrap replicate count remains to be filled from the synthetic-only W9R6M4N2 runtime benchmark. No v2.1 predictive performance has been examined.

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

## Primary comparison and multiplicity

Open-Jev on the stripped note is the primary semantic instrument. The augmented model is identical to the rich comparator except for addition of the eight Open-Jev scores.

For each outcome,

[
\Delta AUROC =
AUROC_{rich\ comparator + Open\text{-}Jev}
-
AUROC_{rich\ comparator}.
]

The primary point estimate uses the first frozen five-fold patient-grouped partition (seed 20260924). Four additional frozen partitions assess split stability.

Each outcome has the one-sided hypothesis (H_0:\Delta AUROC\le0) versus (H_1:\Delta AUROC>0). The three p-values form one family and are adjusted by Holm at family-wise alpha 0.05.

## Primary uncertainty analysis

The decisive uncertainty procedure is a patient-cluster refit bootstrap. Patients are sampled with replacement; all ICU rows from a sampled patient are duplicated by that patient's multiplicity and remain in the patient's frozen repeat-1 fold. Both models are refit in all five folds for every replicate. Duplicated held-out patients retain their bootstrap multiplicity in AUROC calculation.

This procedure captures patient-sampling and model-refit variability conditional on the repeat-1 partition. Variation from choosing a different partition is assessed separately with repeats 2–5.

The bootstrap count will be **{{REFIT_BOOTSTRAP_REPLICATES}}**, fixed from the synthetic runtime benchmark before registration. Bootstrap patient samples use deterministic child seeds generated by `numpy.random.SeedSequence(20260924).spawn(B)`; the HGB random state remains fixed at 20260924 for the primary partition. The only primary uncertainty interval is the two-sided 95% percentile interval from the refit-bootstrap distribution. The one-sided centered-bootstrap p-value is

[
p = \frac{1 + \#\{(\Delta_b-\Delta_{obs}) \ge \Delta_{obs}\}}{B+1},
]

followed by Holm adjustment across the three outcomes.

## Power and interpretation

Power planning used only frozen counts, exact note-available counts, and previously known v1 structured AUROCs as planning anchors. At Holm's first-step alpha and assumed paired-prediction correlation 0.90, the approximate 80% detectable full-cohort increments are 0.0233 for ventilation, 0.0113 for RRT, and 0.0241 for ICU death. The note-available-only values are 0.0334, 0.0170, and 0.0385.

We retain the three outcome-specific Holm-controlled tests despite this limited power. Nonsignificant findings will therefore be reported with their effect estimates and uncertainty and will not be interpreted as evidence that the true increment is zero. Note-available-only analyses are secondary and descriptive.

## Secondary analyses

Prespecified secondary analyses include ΔAUPRC, Brier score, log loss, calibration and decision curves; Laya; DiffusionGemma; stripped-text TF-IDF; the six-construct state-dominant Open-Jev subset; full-note text; the broad respiratory-support ventilation endpoint; timing sensitivities; and CareVue death replication. These secondary analyses are not part of the three-test Holm family and are not used to redefine a null primary result.

The high-dimensional lexical comparison uses a separate fixed sparse-logistic analysis family because 10,000-dimensional TF-IDF is not passed to HistGradientBoostingClassifier. Within each training fold, the same encoded rich comparator is evaluated with sparse logistic regression as comparator-only, comparator + Open-Jev, comparator + TF-IDF, and comparator + TF-IDF + Open-Jev. Direct semantic-versus-lexical conclusions are drawn within this common logistic family. The primary HGB Open-Jev comparison remains unchanged.

The state-dominant subset excludes poor treatment response and escalation considered. It is not described as treatment-free because respiratory and hemodynamic concern can still refer to support needs.

The patient-shuffled semantic negative control uses repeat-1 out-of-fold rich-comparator risk deciles. Within each outcome/source analysis, complete eight-score vectors are permuted among note-available patients within decile using seed 20260929; no-note rows remain unchanged.

## Construct and external validation

Clinician construct validation is separate from predictive hypothesis testing. Blinded raters will score the eight constructs and estimate 12-hour deterioration probability. Inter-rater reliability, same-construct agreement across methods, cross-construct discrimination, and model-human association will be reported.

Zigong will have two prespecified external arms. A local Chinese-to-English translation pipeline will be frozen without access to Zigong outcome labels; Open-Jev, Laya, and English TF-IDF will then receive the same translated text. Native-Chinese DiffusionGemma remains a separate transport analysis. Translation model choice and decoding parameters will be locked in a separate label-free protocol before outcomes are analyzed.

## Deviations and paper scope

If an implementation defect or data-integrity problem is found after registration, the affected analysis will stop and the date, reason, and correction will be documented before the corrected result is inspected. If the original result has already been seen, both versions will remain in the audit trail and the supersession will be reported.

The first paper requires the internal v2.1 confirmatory analysis, clinician construct validation, and Zigong narrative validation. Penn State narrative data, eICU/NWICU structured transport, a full equity analysis, semantic trajectories, the historical vasopressor analysis, and a rebuilt supervised encoder are not required for initial submission.
