# Technical appendix to the v2.1 post-review confirmatory SAP

This appendix records the implementation details fixed before OSF registration. An interim fixed-prediction uncertainty amendment remains in the repository as superseded provenance; after a synthetic threading/runtime re-audit, the original 500-replicate exact patient-cluster refit-bootstrap procedure was restored before any v2.1 predictive performance was examined.

## A. Analysis populations

The confirmatory cohorts are source-homogeneous MetaVision populations. Ventilation and RRT are MetaVision-only because their endpoints are MetaVision-observable. ICU death was initially built across both MIMIC-III source systems, but CareVue versus MetaVision could be recovered from documentation behavior with AUROC 0.9527 and from the full comparator with AUROC 0.9796 in patient-grouped label-free source diagnostics. Confirmatory death was therefore restricted to MetaVision. CareVue death is retained as a separate replication analysis.

Adult eligibility is determined before the deidentification age cap. Patients younger than 18 years and NICU first-careunit stays are excluded. Downstream analyses assert the frozen row, patient, case, control, and note-availability counts.

## B. Outcomes

The landmark is 12 hours after ICU admission and the prediction horizon is the next 12 hours. The primary ventilation endpoint is MetaVision intubation procedure item 224385. Broader respiratory-support evidence is used for pre-landmark disqualification and control eligibility. The corrected explicit-intubation sensitivity is empirically identical to the primary cohort; the broader respiratory-support endpoint is the meaningful ventilation sensitivity.

RRT and ICU-death definitions follow the corrected v2.1 cohort protocol. Control rows have no populated future event time.

## C. Structured physiology

The core structured comparator contains 34 features: age and sex; latest and six-hour change in heart rate, systolic pressure, diastolic pressure, mean arterial pressure, respiratory rate, SpO2, and temperature; GCS eye, verbal, and motor; lactate, creatinine, BUN, WBC, hemoglobin, platelets, sodium, potassium, bicarbonate, chloride, glucose, bilirubin, INR, pH; and six-hour net urine output.

Airway-coded verbal GCS values such as 1.0 ET/Trach and No Response-ETT are treated as missing, not verbal score 1. The corrected extraction excluded 32,942 such rows.

## D. Treatment and support context

The respiratory lookback is six hours. FiO2 is normalized to percent: values in (0,1] are multiplied by 100, values in [20,100] are retained, and other numeric values are set to missing. Oxygen flow is the latest source-compatible value in the six-hour window. High-flow oxygen and NIV are binary source-compatible indicators.

In the ventilation cohort, FiO2 is expected to be sparse because pre-landmark FiO2 is largely charted after respiratory support is already established. Its preregistration availability is approximately 9.9%, compared with roughly 44% for RRT and death. Ventilation treatment context therefore does not rely on FiO2 alone; oxygen device, oxygen flow, high-flow, and NIV indicators carry the main prespecified respiratory-support information, and FiO2 missingness is preserved.

For MetaVision, vasoactive and sedative/analgesic variables represent mapped non-cancelled infusions active at the landmark. For the CareVue death replication they represent mapped exposure during the prior six hours because duration is not represented equivalently. Agent counts are the numbers of distinct mapped agents.

Code status enters the ICU-death comparator only. The last source-specific value at or before the landmark is taken from CareVue item 128 or MetaVision item 223758 and encoded as availability plus non-full-code indicator variables.

## E. Documentation behavior and ordinary note context

Documentation behavior is based only on eligible bedside-note metadata from the 12 hours before the landmark. The variables are note count, total characters, latest-note characters, number of collapsed note-category groups, and note counts in nursing, physician, respiratory, and other groups.

Selected-note age appears only in ordinary note context, together with has_note and the selected note's collapsed category. The inter-note-gap candidate was dropped before performance because its first implementation was all-missing and was not needed for the frozen primary block.

This is a prespecified documentation-behavior comparator motivated by prior work on charting behavior; it is not described as an exact implementation of CONCERN.

## F. Fixed-note text preprocessing

The prospective note is selected before any language handling. Outcome-specific stripping is case-insensitive and replaces each frozen direct-language match with one ASCII space. It does not otherwise normalize the text.

The preregistration review broadened the frozen stripping vocabulary before any v2.1 text inference: standalone `vent` was added for ventilation, and `ultrafiltration` plus context-limited hemodialysis `HD` expressions were added for RRT. Bare `HD` and bare `RRT` remain unstripped because they can denote hospital day and rapid response team, respectively.

The corrected corpus was re-materialized successfully in `P7R4Q9V2` with the frozen note identities unchanged. The corrected transformation changed 646 ventilation notes versus 618 under the earlier vocabulary, and 465 RRT notes versus 347 earlier; the MetaVision and CareVue death corpora were unchanged at 797 and 1,159 changed notes. The corrected corpus artifact SHA-256 is `b6ace04ec469261d0c25b6c685c3c027c1b5bd8154b9dc028c7baa95e1edb4a0`.

The primary corrected stripped-text hashes are recorded in `config/v2_1_fixed_note_corpus_result_contract.json`. The full prospective note remains the secondary text sensitivity. No semantic or TF-IDF inference occurred before this refreeze.

Known vocabulary limits remain. The frozen patterns do not strip `vented`, `s/p HD`, or standalone `iHD`. These are documented limitations of the direct-language sensitivity and will not trigger another preregistration corpus expansion. The stripping procedure is intended to reduce obvious endpoint or treatment wording, not to remove every synonymous or contextual expression.

## G. Semantic representations

The eight constructs are overall clinician concern, worsening trajectory, respiratory concern, hemodynamic concern, poor treatment response, escalation considered, diagnostic uncertainty, and reassuring stability.

Open-Jev is primary. Laya is a semantic-method sensitivity. DiffusionGemma is a robustness and external-transport representation. The model roles are frozen in config/v2_1_semantic_model_roster.json.

Patients without an eligible note have all eight semantic values missing. Note-available rows must have all eight scores. No explicit interaction between semantic scores and has_note is added.

For HistGradientBoosting models, missing semantic values remain NaN and are handled natively. For any logistic model that includes semantic scores, each semantic dimension is imputed with the median calculated from finite values in that training fold only, and the same training-fold median is applied to the held-out fold. The prespecified has_note indicator remains in the comparator, so no-note rows are distinguishable from observed-note rows. A note-available row with an incomplete eight-score vector is treated as an inference failure and causes the analysis to stop rather than being silently imputed. The frozen rule is recorded in config/v2_1_semantic_missingness_freeze.json.

## H. Lexical reference

The stripped-text TF-IDF reference is fitted within each training fold. It uses lowercase text, Unicode accent stripping, word unigrams and bigrams, min_df=5, max_df=0.98, at most 10,000 features, and sublinear term frequency. Rows without an eligible note receive an all-zero TF-IDF vector; has_note remains in the comparator so this zero vector is not interpreted as an observed empty note. The unstripped lexical analysis is secondary.

## I. Cross-validation

Patient-grouped split assignments are frozen. All ICU rows from one source patient remain in one fold. Five repeats use seeds 20260924 through 20260928. Repeat 1 is the primary partition; repeats 2 through 5 assess refit and fold-assignment stability.

Frozen split hashes are:

- ventilation: 30d6d4e591bfe3ff0dc736d8619dcead94f1c3880b160dbfed7efbffce727b35;
- RRT: 1a2b8e23045ac79429bcb65b6ff3c382226be1fbab5a9460f2d8c1ca49bb5ee0;
- MetaVision death: 444a0dac02358d1d4eafe83b96d3804df30134de00e4b54509beb7bbbe411658;
- CareVue death replication: 490c70902518a9620a9f3c0808f2275f56652e423e8820c78a8fa4d7dca30a2f.

## J. Model specification

The nonlinear learner is scikit-learn HistGradientBoostingClassifier with learning_rate=0.05, max_iter=300, max_leaf_nodes=15, min_samples_leaf=50, l2_regularization=1.0, and early_stopping=False. No outcome-specific hyperparameter search is permitted.

Comparator and augmented models use the same preprocessing and learner settings. The primary comparison differs only by addition of the eight Open-Jev inputs.

## K. Primary estimation and uncertainty

For each outcome, the primary estimate is repeat-1 out-of-fold delta-AUROC.

The primary uncertainty interval uses 500 patient-cluster refit-bootstrap replicates of the complete repeat-1 cross-fitting procedure. Source patients are sampled with replacement. All ICU rows from a sampled patient enter with that patient's bootstrap multiplicity, the frozen repeat-1 fold assignment is retained, and both comparator and augmented HGB models are refit in every fold for every replicate. The reported interval is the two-sided 95% percentile interval of the 500 delta-AUROC replicates.

This interval includes patient-sampling and model-refit variability conditional on the frozen repeat-1 fold partition. Repeats 2 through 5 separately assess refit and fold-partition stability.

No confirmatory p-values are calculated, no Holm adjustment is applied, and interval crossing of zero is not used as a binary claim rule.

The execution contract fixes OMP_NUM_THREADS=4, OPENBLAS_NUM_THREADS=4, MKL_NUM_THREADS=4, and NUMEXPR_NUM_THREADS=4 for HGB workloads.

## L. Runtime benchmark correction

The prior Y5R7M2Q8 synthetic benchmark reported 5,470.3 seconds for one exact ventilation replicate and was used to replace the refit-bootstrap interval with a fixed-prediction interval. That inference amendment is superseded before registration.

Synthetic-only audit B6R9M4Q2 showed that the workstation exposes 112 CPUs to OpenMP despite a 4-core RunRelay resource request. Library-default execution failed to complete one two-fit fold within 90 seconds. Explicit one-thread execution completed that fold in 3.56 seconds, explicit four-thread execution in 2.18 seconds, and the full exact five-fold replicate in 11.21 seconds. The earlier runtime was therefore an oversubscription artifact rather than evidence that refit bootstrapping is infeasible.

At the corrected ventilation runtime, 500 serial replicates project to about 1.56 hours. The original 500-replicate refit-bootstrap concept is restored, while the later estimation-first framing is retained in the sense that no confirmatory p-values or Holm testing are used.

## M. Secondary measures and analyses

Delta-AUPRC is the key secondary discrimination contrast. Brier score, log loss, calibration-in-the-large, calibration slope, expected calibration error, and decision-curve summaries are secondary.

Note-available-only analyses change the target population and are descriptive. Laya, DiffusionGemma, state-dominant constructs, TF-IDF, the unstripped note, ventilation endpoint sensitivity, timing sensitivity, CareVue death replication, and negative controls are secondary or sensitivity analyses and do not redefine the primary estimands.

## N. Patient-shuffled semantic negative control

Within each outcome/source analysis, note-available patients are assigned to deciles of repeat-1 out-of-fold rich-comparator predicted risk. Complete eight-score semantic vectors are permuted between patients within each decile using seed 20260929. No-note rows remain unchanged. The shuffled augmented model uses the same frozen folds, preprocessing, and HGB settings.

## O. Clinician construct validation

Clinician raters remain blinded to model scores and prediction errors. Raters score the eight constructs and provide a 12-hour deterioration probability. The analysis reports inter-rater reliability, same-construct agreement across methods, cross-construct discrimination, and model-human association. Direct MIMIC note access will comply with applicable PhysioNet credential/DUA requirements, and annotation will begin only after a Penn State IRB determination.

## P. External narrative validation

The translated Zigong arm will use one locally executable Chinese-to-English model with fixed decoding settings selected without outcome labels. Translation quality is assessed before labels are joined. Open-Jev, Laya, and TF-IDF then receive the same translated text. DiffusionGemma is evaluated separately on native Chinese under its frozen direct-Chinese eligibility rules.

## Q. Deviations

Any implementation or data-integrity defect found after registration is logged with its date, affected analysis, reason, and correction. If the affected result has already been seen, both versions remain in the audit trail. Any change that alters the scientific estimand requires an amended protocol.
