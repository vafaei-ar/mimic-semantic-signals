# Post-review confirmatory statistical analysis plan for v2.1

**Draft status:** complete except for the final patient-cluster refit-bootstrap replicate count, which will be filled from the synthetic-only W9R6M4N2 runtime benchmark before registration. No v2.1 predictive performance has been examined.

## Study status and purpose

This is a prospectively registered **post-review confirmatory analysis plan**, not a preregistration of the study from inception. Earlier MIMIC-III analyses informed the questions and several design revisions. The purpose of v2.1 is to test, under corrected eligibility and stronger comparators, whether semantic information measured from prospective ICU notes adds near-term deterioration discrimination beyond structured physiology, treatment/support state, and documentation behavior.

The three confirmatory outcomes are invasive ventilation within 12 hours, renal-replacement therapy (RRT) within 12 hours, and ICU death within 12 hours. All three confirmatory analyses use MetaVision stays. CareVue ICU death is retained as a separate replication/sensitivity analysis because documentation behavior and structured missingness strongly distinguished CareVue from MetaVision in label-free source-system audits.

## Information known before this registration

The analysis team had already seen v1 results. In the earlier prevalence-preserving population analysis, the Open-Jev increment over structured physiology plus note context was +0.00338 AUROC for ventilation, -0.00075 for RRT, and +0.01332 for ICU death. The corresponding Laya increments were -0.00469, -0.00033, and +0.00720. Open-Jev added +0.00537 AUROC after TF-IDF for ICU death in that analysis. The earlier work also showed a large documentation-context association for ventilation: AUROC increased from 0.7071 with the structured model to 0.8596 after adding note context. In a separate matched zero-shot benchmark, DiffusionGemma showed larger structured-model increments for ventilation and death than Open-Jev, and DiffusionGemma was the only model that passed the prior label-free gate for direct-Chinese Zigong scoring.

Several v2.1 decisions were therefore made after these results were known. These include making stripped text primary, strengthening treatment and documentation-process comparators, restricting confirmatory death to MetaVision after a source-proxy audit, and designating the post-review analysis as confirmatory rather than presenting it as an inception-stage preregistration. Open-Jev is the primary semantic instrument because it directly operationalizes the eight predefined typed clinical constructs with a stable interpretable score representation; it was not chosen because it had the largest previously observed increment.

## Frozen populations and text

The confirmatory populations are:

| Outcome | Rows | Cases | Controls | Patients | Eligible notes |
| --- | ---: | ---: | ---: | ---: | ---: |
| Invasive ventilation | 11,116 | 279 | 10,837 | 8,982 | 4,499 |
| RRT | 19,395 | 314 | 19,081 | 15,080 | 7,709 |
| ICU death, MetaVision | 19,811 | 214 | 19,597 | 15,312 | 7,889 |

CareVue ICU death is a prespecified replication population with 25,632 rows and 306 cases.

For every analysis row, note identity, note time, note category, and note availability are fixed before text transformation. The primary corpus replaces prespecified direct endpoint/treatment language with a single space and performs no other text normalization. The full prospective note is a secondary sensitivity. The primary TF-IDF lexical reference uses the same stripped corpus as the semantic analysis.

## Frozen comparator and learner

The richest comparator contains four blocks:

1. the frozen 34-feature structured physiology/laboratory/urine representation;
2. pre-landmark treatment/support context: FiO2, oxygen flow, high-flow and non-invasive respiratory support, vasoactive state/count, sedative/analgesic state/count, and death-only code-status indicators;
3. note-documentation behavior over the prior 12 hours: note count, total characters, latest-note characters, category diversity, and nursing, physician, respiratory, and other note counts;
4. ordinary note context: note availability, selected-note age, and collapsed note category.

No source-system indicator is used. No endpoint-defining invasive-ventilation variable is included in the ventilation treatment block.

The primary learner is HistGradientBoostingClassifier with learning rate 0.05, 300 iterations, at most 15 leaf nodes, minimum 50 samples per leaf, L2 regularization 1.0, and early stopping disabled. Hyperparameters are fixed and are not tuned on v2.1 results. Preprocessing parameters are estimated within the training fold. Categorical variables are one-hot encoded. Structured/context numeric missingness is handled according to the frozen preprocessing pipeline. Semantic scores are not median-imputed: for rows without an eligible note, all eight semantic values remain NaN and `has_note` remains in the comparator; for rows with a note, all eight scores are required.

## Primary semantic comparison

The primary semantic instrument is Open-Jev applied to the frozen stripped note. The augmented model is identical to the rich comparator except for addition of the eight Open-Jev scores.

For each outcome the primary estimand is

[
\Delta AUROC =
AUROC_{rich\ comparator + Open\text{-}Jev}
-
AUROC_{rich\ comparator}.
]

The primary point estimate uses the first frozen five-fold patient-grouped partition (seed 20260924). Four additional frozen partitions are used only to assess split stability.

There are three confirmatory hypotheses, one per outcome:

[
H_0: \Delta AUROC \le 0, \qquad H_1: \Delta AUROC > 0.
]

The three one-sided tests form one family and are adjusted by the Holm procedure at family-wise alpha 0.05.

## Primary uncertainty analysis

The decisive uncertainty analysis is a patient-cluster refit bootstrap. Patients are sampled with replacement. All ICU rows belonging to a sampled patient are duplicated according to that patient's bootstrap multiplicity and remain in that patient's frozen repeat-1 fold. In each bootstrap replicate both the rich comparator and the Open-Jev-augmented model are refit in each of the five folds. Duplicated held-out patients contribute to AUROC with their bootstrap multiplicity.

This procedure estimates patient-sampling and model-refit variability conditional on the frozen repeat-1 partition. It does not estimate variability due to choosing a different fold partition; repeats 2–5 provide that separate stability check.

The bootstrap replicate count will be **{{REFIT_BOOTSTRAP_REPLICATES}}**, fixed from the synthetic-only runtime benchmark before registration. The only inferential interval reported for the primary contrast will be the patient-cluster refit-bootstrap interval; no fixed-prediction bootstrap interval will be used as a competing primary interval.

For the one-sided test, the bootstrap distribution is centered at the observed effect. With bootstrap estimates (Delta_b) and observed effect (Delta_{obs}),

[
p = \frac{1 + \#\{(\Delta_b-\Delta_{obs}) \ge \Delta_{obs}\}}{B+1}.
]

Holm adjustment is then applied to the three outcome p-values.

## Power and interpretation

Power planning used only frozen cohort counts, exact note-available counts, and previously known v1 structured AUROCs as planning anchors. At the Holm first-step alpha of 0.0167, the approximate 80% detectable full-cohort AUROC increments at an assumed paired-prediction correlation of 0.90 are 0.0233 for ventilation, 0.0113 for RRT, and 0.0241 for ICU death. The corresponding note-available-only values are 0.0334, 0.0170, and 0.0385.

The study deliberately retains the three outcome-specific Holm-controlled tests despite this limited power. A nonsignificant result will therefore be reported with its effect estimate and uncertainty rather than interpreted as evidence that the true increment is zero. Note-available-only analyses are secondary and descriptive; they cannot replace the full-cohort estimand.

## Prespecified secondary analyses

Secondary analyses include ΔAUPRC, Brier score, log loss, calibration, and decision-curve summaries; Laya as a semantic-method sensitivity; DiffusionGemma as a robustness representation; stripped-text TF-IDF as the high-dimensional lexical reference; the six-construct state-dominant Open-Jev subset; full-note analyses; the broad respiratory-support ventilation endpoint; prospective-timing sensitivities; and CareVue ICU-death replication.

The state-dominant subset retains overall clinician concern, worsening trajectory, respiratory concern, hemodynamic concern, diagnostic uncertainty, and reassuring stability. It excludes poor treatment response and escalation considered. It is not described as treatment-free because the respiratory and hemodynamic constructs can still refer to support needs.

A patient-shuffled semantic negative control will be reported as a secondary sanity check. Within each outcome and source-specific analysis, note-available patients will be assigned to deciles of the repeat-1 out-of-fold rich-comparator predicted risk. The complete eight-score semantic vector will then be permuted between patients within each decile using fixed seed 20260929; no-note rows remain unchanged with semantic NaNs. The shuffled augmented model will use the same frozen folds and learner. This preserves note availability and approximate structured/context risk while breaking correspondence between a patient's own note and semantic scores.

## Construct and external validation

Clinician construct validation is separate from predictive hypothesis testing. A blinded sample will be rated for the eight constructs and for estimated probability of deterioration within 12 hours. Inter-rater agreement, model-human convergent validity, and cross-construct discriminant validity will be reported. Controlled note edits and prompt-repeatability checks may be added as prespecified construct-validity analyses without using outcome performance for tuning.

For Zigong, the external program will contain two prespecified arms. A locally frozen Chinese-to-English translation pipeline will be selected and locked without access to Zigong outcome labels, after which Open-Jev, Laya, and English TF-IDF will be applied to the same translated text. Native-Chinese DiffusionGemma will remain a separate transport arm. Translation model choice and decoding parameters require a separate label-free freeze before external outcome analysis.

## Deviations

If a post-registration implementation defect, data-integrity problem, or violation of a prespecified assumption is discovered, the affected analysis will stop. The date, problem, reason, and correction will be documented before the corrected result is inspected. If the affected result has already been seen, the original and corrected versions and the reason for supersession will both be reported. Changes made for computational feasibility will preserve the scientific estimand whenever possible and will be documented before the corresponding result is opened.

## Minimum scope for the first paper

The first paper requires the internal v2.1 confirmatory analysis, clinician construct validation, and the prespecified Zigong narrative-transport analyses. Penn State narrative validation, eICU/NWICU structured transport, a full equity analysis, semantic trajectories, the historical vasopressor analysis, and a rebuilt supervised encoder are not submission-critical and may be reserved for revision or later work.
