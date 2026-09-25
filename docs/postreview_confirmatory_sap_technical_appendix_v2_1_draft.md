# Technical appendix to the v2.1 post-review confirmatory SAP

**Draft status:** the scientific design is frozen; the refit-bootstrap count is frozen at 500 replicates per confirmatory outcome. The revised outcome-specific synthetic exact-runtime benchmark is engineering-only and cannot change the inferential replicate count.

## A. Analysis populations

The three confirmatory cohorts are source-homogeneous MetaVision populations. Ventilation and RRT were already restricted to MetaVision because their endpoints are MetaVision-observable. ICU death was initially built across both MIMIC-III source systems, but source-system audits showed that CareVue versus MetaVision could be recovered from documentation behavior with AUROC 0.9527 and from the current full comparator with AUROC 0.9796 using patient-grouped logistic diagnostics. Confirmatory death was therefore restricted to MetaVision before any v2.1 mortality performance was examined. CareVue death is analyzed separately as replication/sensitivity.

Adult eligibility is determined before the deidentification age cap. NICU first-careunit stays and patients younger than 18 years are excluded. Downstream jobs assert frozen row, patient, case, control, and note-availability counts.

## B. Outcomes

The landmark is 12 hours after ICU admission and the prediction horizon is the following 12 hours. Outcome definitions follow the frozen corrected v2.1 cohort protocol. The primary ventilation endpoint is the high-specificity MetaVision intubation procedure item 224385, with broader respiratory-support evidence used for pre-landmark disqualification/control eligibility. The corrected explicit-intubation sensitivity is empirically identical to the primary cohort. A broad respiratory-support endpoint is retained as the meaningful ventilation sensitivity.

RRT and death definitions follow the corrected v2.1 protocol. Controls have no populated future event time.

## C. Structured physiology

The core structured block has 34 features: age, sex; latest and six-hour change in heart rate, systolic blood pressure, diastolic blood pressure, mean arterial pressure, respiratory rate, SpO2, and temperature; GCS eye, verbal, and motor; lactate, creatinine, BUN, WBC, hemoglobin, platelets, sodium, potassium, bicarbonate, chloride, glucose, bilirubin, INR, pH; and six-hour net urine output.

Airway-coded GCS verbal values such as `1.0 ET/Trach` and `No Response-ETT` are missing, not verbal score 1. The corrected extraction excluded 32,942 such rows.

## D. Treatment/support context

The respiratory lookback is six hours. FiO2 is normalized to percent: values in (0,1] are multiplied by 100, values in [20,100] are retained, and all other numeric values are missing. Oxygen flow is the latest source-compatible value in the six-hour window. High-flow and NIV are binary source-compatible indicators.

For MetaVision, vasoactive and sedative/analgesic variables represent mapped non-cancelled infusions active at the landmark. For CareVue death replication they represent mapped recent six-hour exposure because duration is not represented equivalently. Agent counts are numbers of distinct mapped agents.

The death comparator also contains the last pre-landmark code-status state, represented by availability and non-full-code indicator variables. Code status is not included for ventilation or RRT.

## E. Documentation behavior and note context

Documentation-behavior variables are based on eligible bedside-note metadata in the 12 hours before the landmark. They include note count, total characters, latest-note characters, number of collapsed note-category groups, and note counts by nursing, physician, respiratory, and other categories.

Selected-note age is kept only in ordinary note context, not duplicated in the documentation-behavior block. The candidate inter-note-gap variable was dropped before performance because its first implementation was all-missing and it was unnecessary for the frozen primary block.

The analysis does not describe this block as an exact CONCERN implementation. It is a prespecified note-documentation-behavior comparator intended to distinguish content from the process of documentation.

## F. Text preprocessing

The selected prospective note is fixed before any language handling. Stripping is outcome-specific, case-insensitive, replaces each frozen direct-language match with one ASCII space, and performs no additional normalization. The corpus build verified that the number of notes changed by stripping exactly matched the previously frozen direct-language flag in each source-specific analysis.

The primary corpus hashes are frozen in `config/v2_1_fixed_note_corpus_result_contract.json`.

## G. Semantic representations

The eight constructs are:

1. overall clinician concern;
2. worsening trajectory;
3. respiratory concern;
4. hemodynamic concern;
5. poor treatment response;
6. escalation considered;
7. diagnostic uncertainty;
8. reassuring stability.

Open-Jev is primary. Laya is a prespecified semantic-method sensitivity. DiffusionGemma is a robustness and external-transport representation. These roles are fixed in `config/v2_1_semantic_model_roster.json`.

For patients without an eligible note, all eight semantic features are NaN. For note-available rows, all eight must be present. No explicit interaction between a semantic score and `has_note` is added.

## H. Lexical reference

The stripped-text TF-IDF reference uses training-fold fitting only, lowercase text, Unicode accent stripping, word unigrams and bigrams, min_df 5, max_df 0.98, at most 10,000 features, and sublinear term frequency. The full-note lexical analysis is a secondary sensitivity.

## I. Cross-validation

The split assignment is frozen before performance. All ICU rows from the same source patient remain within the same fold. Five deterministic repeats use seeds 20260924 through 20260928. The first repeat is the primary partition. Repeats 2–5 are not averaged into the decisive inferential bootstrap; they show sensitivity to fold assignment.

Frozen primary split hashes are:

- ventilation: `30d6d4e591bfe3ff0dc736d8619dcead94f1c3880b160dbfed7efbffce727b35`;
- RRT: `1a2b8e23045ac79429bcb65b6ff3c382226be1fbab5a9460f2d8c1ca49bb5ee0`;
- MetaVision death: `444a0dac02358d1d4eafe83b96d3804df30134de00e4b54509beb7bbbe411658`;
- CareVue death replication: `490c70902518a9620a9f3c0808f2275f56652e423e8820c78a8fa4d7dca30a2f`.

## J. Model specification

The nonlinear learner is scikit-learn HistGradientBoostingClassifier with:

- learning_rate 0.05;
- max_iter 300;
- max_leaf_nodes 15;
- min_samples_leaf 50;
- l2_regularization 1.0;
- early_stopping false.

No outcome-specific hyperparameter search is permitted.

Comparator and augmented models use the same preprocessing and learner settings. The only difference in the primary comparison is the eight Open-Jev inputs.

## K. Primary inference

For each outcome, the primary estimate is repeat-1 out-of-fold ΔAUROC. The patient-cluster refit bootstrap samples patients with replacement and duplicates all their ICU rows according to patient multiplicity while retaining frozen fold membership. Each replicate refits both models in all five folds. Test-set duplicates remain duplicated when AUROC is calculated.

This bootstrap conditions on the repeat-1 fold partition. Repeats 2–5 quantify split-assignment stability separately.

The refit-bootstrap replicate count is `500`. The one-sided centered-bootstrap p-value is

[
p = \frac{1 + \#\{(\Delta_b-\Delta_{obs}) \ge \Delta_{obs}\}}{B+1}.
]

The three p-values are adjusted by Holm. A confirmatory positive-increment claim for an outcome requires both an observed positive \(\Delta AUROC\) and a Holm-adjusted one-sided refit-bootstrap p-value below 0.05. The same refit-bootstrap distribution supplies the single reported two-sided 95% percentile interval for effect magnitude; that interval is not used as an unadjusted substitute for the Holm decision rule. No fixed-prediction bootstrap interval is used for confirmatory inference.

## L. Secondary performance measures

ΔAUPRC is the key secondary discrimination contrast. Brier score, log loss, calibration-in-the-large, calibration slope, expected calibration error, and decision-curve summaries are secondary. Calibration and utility claims are made only in prevalence-preserving populations and not in matched historical cohorts.

## M. Conditional analyses and multiplicity

Note-available-only analyses change the target population and are labeled conditional/descriptive. They are not part of the Holm family and cannot replace a null full-cohort result.

Laya, DiffusionGemma, state-dominant constructs, TF-IDF, full-note text, ventilation endpoint sensitivity, timing sensitivity, CareVue death replication, and negative controls are prespecified secondary or sensitivity analyses. Their results are reported with effect estimates and uncertainty but do not create additional primary claims.

## N. Negative control

The negative control is patient-shuffled semantics. For each outcome/source analysis, note-available patients are assigned to deciles of the repeat-1 out-of-fold rich-comparator predicted risk. The entire eight-score semantic vector is permuted between patients within each decile with fixed seed 20260929. No-note rows remain no-note rows with semantic NaNs. The shuffled augmented model is fit with the same frozen folds, preprocessing, and HGB specification. This preserves note availability and approximate comparator risk while breaking correspondence between a patient's own note and semantic scores.

## O. Construct validation

Clinician raters remain blinded to model scores and prediction errors. Raters score the eight constructs and provide a 12-hour deterioration probability. The construct-validation analysis reports inter-rater reliability, same-construct agreement across methods, cross-construct discrimination, and model-human association. Controlled edits can test negation, concern insertion/removal, and copy-forward duplication. Prompt repeatability is evaluated by a frozen small set of wording variants rather than by outcome-driven prompt selection.

## P. External narrative validation

The translated Zigong arm will use one locally executable Chinese-to-English model and fixed decoding parameters selected without outcome labels. Translation quality is assessed before labels are joined. Open-Jev, Laya, and TF-IDF then receive the same translated text. DiffusionGemma is evaluated separately on native Chinese under its frozen direct-Chinese eligibility rules.

The external analyses do not alter the internal confirmatory model or thresholds.

## Q. Deviations and audit trail

Any implementation defect discovered after registration is logged with date, affected analysis, reason, and correction. If discovered before the affected result is opened, the corrected analysis supersedes the defective implementation. If the affected result has already been seen, both versions are retained in the audit trail and reported with the reason for supersession. A computational change that alters the scientific estimand requires an amended protocol rather than an undocumented implementation substitution.


The initial combined benchmark `W9R6M4N2` timed out before emitting an artifact because it combined full-size runtime fitting with repeated model-refit null simulations. It is not used to set the replicate count. The revised benchmark isolates one exact full-size refit replicate per outcome and evaluates p-value null behavior separately with cheap synthetic statistics.


## Runtime benchmark execution rule

Runtime benchmark results do not change B = 500. They are used only to determine whether the exact patient-cluster refit bootstrap needs engineering changes such as outcome-specific tasks, checkpointed replicate batches, or controlled parallel execution. Any such engineering change must preserve the frozen patient sampling, fixed-fold membership, model specification, held-out multiplicity, seed stream, interval, and p-value definitions. If execution is still impractical, the plan must be amended before OSF registration rather than silently reducing the number of replicates.
