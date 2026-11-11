# Exploratory extension v2.1: cross-outcome synthesis and methodological QA

Date: 2026-11-10  
Status: **All registered T1.5 outcome runs completed. Scientific synthesis is ready for internal review. Two inferential and interpretation issues remain open.**  
Primary registration: OSF `ahxn9`. Exploratory extension: OSF `wmyb2`.  
Frozen scientific execution commit: `e5772f7a1a40b2368465e1b95e24a04abc98cc2a`.  
This report is a source-backed review, not a new outcome analysis. Keep the JAMIA-ready `main` branch unchanged.

## Central scientific conclusion

Supervised clinical text predicts ICU outcomes among stays with notes. However, across the completed exploratory T1.1, T1.2, T1.2b, T1.4 and T1.5 evaluations, no tested text-augmented model demonstrated statistically reliable incremental AUROC against the rich structured comparator D. T1.5 also failed to show a reliable gain for either supervised scalar text representation against the thinnest comparator A. Its twelve prespecified 95% ΔAUROC confidence intervals and twelve corresponding ΔAUPRC intervals at A and D all include zero.

The correct conclusion applies to the specific frozen models, notes, populations, outcome definitions and patient-grouped validation. **Do not conclude statistical equivalence, absence of residual bedside-narrative information, causal redundancy, or improved clinical decision-making.** The extension is post-registration exploratory.

## Data and design

| Outcome | ICU stays | Events | Note-available stays | Note availability |
|---|---:|---:|---:|---:|
| Invasive ventilation | 11,116 | 279 | 4,499 | 40.5% |
| Renal replacement therapy (RRT) | 19,395 | 314 | 7,709 | 39.7% |
| MetaVision ICU death | 19,811 | 214 | 7,889 | 39.8% |

Each T1.5 outcome uses five frozen source-patient-grouped outer partitions and separately adds either a supervised TF-IDF/L2-logistic text score or a frozen BGE-embedding/L2-logistic text score to a structured HGB model. The text inputs are stripped H6 notes. Comparator A has 34 structured predictors. B adds treatment and support. C adds documentation behavior. D adds note availability and note context. The number of predictors is 42, 50 and 57 at B, C and D for ventilation and RRT, and 46, 54 and 61 for ICU death. D includes four additional code-status features for ICU death.

T1.5 reports ΔAUROC and ΔAUPRC at all four comparators for five frozen partitions. Its 200-valid-replicate patient-cluster full-refit bootstrap produces 95% percentile intervals at A and D in the primary partition only. The frozen mechanical 72-hour runtime rule selected 200 for every T1.5 outcome. The three final analyses completed with zero replacement replicates.

## T1.5 original primary partition and interval results

For each model, the following table shows ΔAUROC (two-sided 95% full-refit percentile CI). A ΔAUROC measures the increase or decrease relative to the **structured baseline at that same comparator level**. These CIs do not represent A-minus-D contrasts.

| Outcome | Level | Baseline AUROC | TF-IDF ΔAUROC (95% CI) | Embedding ΔAUROC (95% CI) |
|---|---|---:|---|---|
| Ventilation | A, 34 features | 0.672388 | +0.022888 [−0.012831, +0.020596] | +0.007533 [−0.012389, +0.020793] |
| Ventilation | D, 57 features | 0.724675 | −0.001372 [−0.014735, +0.014324] | +0.001937 [−0.012622, +0.017966] |
| RRT | A, 34 features | 0.969887 | +0.000397 [−0.002030, +0.003366] | +0.000165 [−0.002686, +0.003096] |
| RRT | D, 57 features | 0.973936 | −0.000685 [−0.001830, +0.002553] | −0.000800 [−0.002685, +0.002289] |
| ICU death | A, 34 features | 0.926849 | +0.000503 [−0.007845, +0.007828] | −0.004681 [−0.008746, +0.006446] |
| ICU death | D, 61 features | 0.933382 | +0.003389 [−0.005907, +0.007898] | −0.000462 [−0.006668, +0.006261] |

The apparent TF-IDF point gain for ventilation is greater at A than at D. RRT point increments are very small at both levels. ICU-death TF-IDF point increments are larger at D than at A. Thus **there is no consistent monotonic attenuation pattern across all outcomes**. The five outer partitions share source patients and cannot substitute for a formal paired contrast bootstrap. The T1.5 output does not include a paired uncertainty interval for an A-minus-D difference.

## Earlier frozen extension arms at rich comparator D

Each cell gives the primary ΔAUROC and reported 95% full-refit percentile interval. These repeated analyses share patient populations and should not be counted as independent replications.

| Frozen model | Ventilation | RRT | ICU death |
|---|---|---|---|
| T1.1, stripped TF-IDF scalar | −0.001370 [−0.014930, +0.014680] | −0.000680 [−0.002300, +0.002690] | +0.003390 [−0.006250, +0.007840] |
| T1.2, frozen-BGE supervised scalar | +0.001937 [−0.014232, +0.017353] | −0.000800 [−0.002648, +0.002391] | −0.000462 [−0.006327, +0.006802] |
| T1.2b, 32-component BGE early fusion | −0.002830 [−0.024938, +0.026863] | −0.000485 [−0.003479, +0.003209] | +0.000240 [−0.010065, +0.006978] |
| T1.4, unstripped TF-IDF scalar | +0.003773 [−0.016243, +0.014625] | +0.000619 [−0.001953, +0.003572] | +0.003294 [−0.005525, +0.008254] |

All reported intervals include zero. The early-fusion study addresses one registered alternative to compressing notes into a scalar, but it does not exhaust other text representations or possible interactions. T1.4 compared stripped and unstripped notes descriptively. Do not interpret those differences as proof of outcome-language leakage.

Standalone note-available TF-IDF AUROCs in the primary partition were 0.64023, 0.87350 and 0.85626. Corresponding frozen-embedding AUROCs were 0.615456, 0.803578 and 0.794347. These metrics evaluate only patients with notes and are not incremental model contrasts. Ventilation embedding AUROC fell below the protocol's interpretive 0.60 threshold in three of the other four partitions. Strong claims of stable ventilation embedding discrimination would therefore be unsupported.

T1.1–T1.4 fixed 5% alert-budget analyses also failed to demonstrate a reliable clinical benefit. The T1.2b ventilation point estimate involved ten more captured events, but its patient-cluster interval for net events per 1,000 stays included zero. T1.5 did not evaluate the fixed alert budget.

## Methodological QA

**1. Frozen registration and grouped validation: consistent with code.** The frozen clarification requires training-only supervised text fitting, all five patient-grouped outer partitions, A and D full-refit intervals, and a mechanical 10-valid-replicate timing gate. Code inspection confirms patient overlap guards in the inner TF-IDF and embedding cross-fitting functions. The T1.5 code checks that reconstructed rich comparator D predictions match registered comparator predictions to tolerance `1e-12`. The patient-cluster bootstrap duplicates all eligible ICU rows for each resampled source patient while retaining its original outer-fold membership. The inference code refits text and HGB in each valid replicate. These checks support code-level procedural consistency. We did not rerun protected patient-level data.

**2. Documentation availability is entangled with the scalar text scores: high-priority interpretation risk.** The TF-IDF and embedding helper functions assign a text score of zero to stays without a note. The published feature lists for RRT and ICU death, and the comparator-construction code for all three outcomes, show that A and B omit explicit `has_note`. C includes note-count and documentation-behavior features that can proxy note availability. D explicitly includes `has_note`, note age and note categories. Hence an A-level scalar text increment could partly reflect **whether a note exists**, not necessarily the lexical or semantic information within it. About 60% of all stays lack notes. This is a structural interpretation limitation, not a measured estimate of the missingness contribution. The current protocol did not separately identify the two effects.

**3. Ventilation A point estimate versus bootstrap distribution: unresolved inferential QA.** Original TF-IDF ΔAUROC at ventilation A is **+0.022888**, yet the 200 full-refit bootstrap mean is **+0.003558** and its 97.5th-percentile endpoint is **+0.020596**. The original point is above the interval's upper endpoint. Percentile intervals need not contain their original estimate, so this is not automatically an error. Nevertheless, a statistical reviewer should inspect the resampled estimation target, full-refit weights, duplicate source-patient handling and the potential bias in the bootstrap distribution before manuscript-final interpretation.

**4. Point-estimate and bootstrap inner-fold seed paths differ: method review required.** Original point-estimate code chooses the text and embedding inner-fold seeds as `INNER_SEED_BASE + 100 * repeat_number + fold_number`. Bootstrap refits choose `INNER_SEED_BASE + fold_number`. Both remain patient grouped. This code-verified difference may be intentional and is not proof of an error, but it must be understood when investigating the ventilation A shift. Do not make an after-the-fact estimator change to improve the result.

**5. Limits of this audit.** This review reconciles the publicly frozen aggregate evidence, source-code paths and available RunRelay provenance. It does not inspect local note text, raw outcomes, individual clinical timestamps, row predictions or subject-level bootstrap draws. Therefore it cannot independently certify temporal eligibility, all content-leakage controls or bootstrap calibration. RRT's high structured baseline AUROC alone does not establish a ceiling-effect mechanism. The design cannot establish causal redundancy, statistical equivalence, cross-outcome pooled effects or generalizability to an independent health system.

**Verdict: descriptive synthesis is ready for internal review. Manuscript-final inferential QA remains CONDITIONAL** on explicit adjudication of the note-availability interpretation and ventilation A bootstrap shift. The original frozen protocol and results must remain unchanged.

## Candidate manuscript Results text

We evaluated supervised TF-IDF and frozen-embedding text scores among 11,116 invasive-ventilation stays (279 events), 19,395 renal-replacement-therapy stays (314 events), and 19,811 ICU-death stays (214 deaths). At the richest structured comparator, primary TF-IDF ΔAUROC was −0.001372, −0.000685 and +0.003389, respectively. Corresponding frozen-embedding ΔAUROC values were +0.001937, −0.000800 and −0.000462. Prespecified patient-cluster full-refit intervals included zero for both representations in each outcome. The same result held at the thinnest 34-feature comparator. Although ventilation showed a larger original TF-IDF increment at A (+0.022888), its interval [−0.012831, +0.020596] included zero. We observed no consistent monotonic decline in text increments with increasing comparator richness.

Separate registered exploratory models with 32-component early fusion and unstripped-note TF-IDF also did not demonstrate reliable additional AUROC discrimination against the rich structured comparator. Standalone text scores discriminated outcomes among note-available stays, but adding them to structured models did not yield a detectable improvement in this setting. The design could not distinguish all contributions of language content from documentation availability, especially with the thinner comparators. We did not test these findings in an independent bedside-narrative dataset.

## Priorities before manuscript integration

First, obtain a focused statistical review of the original-versus-bootstrap estimator mismatch for ventilation A and the inner-fold seed pathways. Use existing code and aggregate outputs before considering any protocol amendment. Second, identify the zero-for-no-note score encoding and comparator A versus D feature differences explicitly in Methods and limitations. Third, reconcile the manuscript abstract, Results, supplemental tables and fixed-alert conclusions against the frozen outcome-specific checkpoints. Report five patient-grouped repeats as stability checks, not independent statistical replications.

The registered **post-T1.5 stop rule remains in force**. No new outcome analysis is authorized without an independent dataset containing genuine bedside narrative and a new protocol.

## Evidence and code provenance

The numerical evidence comes from [T1.1](https://github.com/vafaei-ar/mimic-semantic-signals/blob/3d1cca9ea9a74d9d3b67e69a44f4fbb2bd3eec9a/docs/results/v2_1_extension_t1_1_tfidf_three_outcome_freeze_2026-10-13.md), [T1.2](https://github.com/vafaei-ar/mimic-semantic-signals/blob/3d1cca9ea9a74d9d3b67e69a44f4fbb2bd3eec9a/docs/results/v2_1_extension_t1_2_bge_three_outcome_freeze_2026-10-22.md), [T1.2b](https://github.com/vafaei-ar/mimic-semantic-signals/blob/3d1cca9ea9a74d9d3b67e69a44f4fbb2bd3eec9a/docs/results/v2_1_extension_t1_2b_early_fusion_three_outcome_freeze_2026-10-28.md), and [T1.4](https://github.com/vafaei-ar/mimic-semantic-signals/blob/3d1cca9ea9a74d9d3b67e69a44f4fbb2bd3eec9a/docs/results/v2_1_extension_t1_4_unstripped_three_outcome_freeze_2026-11-03.md), together with the three T1.5 freezes for [T1.5 ventilation](https://github.com/vafaei-ar/mimic-semantic-signals/blob/3d1cca9ea9a74d9d3b67e69a44f4fbb2bd3eec9a/docs/results/v2_1_extension_t1_5_ventilation_final_checkpoint_2026-11-06.md), [T1.5 RRT](https://github.com/vafaei-ar/mimic-semantic-signals/blob/3d1cca9ea9a74d9d3b67e69a44f4fbb2bd3eec9a/docs/results/v2_1_extension_t1_5_rrt_final_checkpoint_2026-11-08.md), and [T1.5 ICU death](https://github.com/vafaei-ar/mimic-semantic-signals/blob/3d1cca9ea9a74d9d3b67e69a44f4fbb2bd3eec9a/docs/results/v2_1_extension_t1_5_death_final_checkpoint_2026-11-10.md). The frozen methodological anchors are the [Protocol](https://github.com/vafaei-ar/mimic-semantic-signals/blob/3d1cca9ea9a74d9d3b67e69a44f4fbb2bd3eec9a/docs/registration/exploratory_extension_protocol_v2_1_2026-10-04.md) and [T1.5 clarification](https://github.com/vafaei-ar/mimic-semantic-signals/blob/3d1cca9ea9a74d9d3b67e69a44f4fbb2bd3eec9a/docs/registration/exploratory_extension_t1_decomposition_clarification_2026-10-06.md). This is a synthesis of existing outputs, not an independently computed meta-analysis.

T1.5 canonical final jobs are ventilation `YG5Z0JK8` (SHA-256 `3496a9623c499d7e1a485efeb7e1bccac5742435d521c9df7d7ae6da632258de`), RRT `YHH9WXER` (SHA-256 `40263dfda4ff32be4aa0cdc255de8115a4d16d639b8ad4c0fc7bf3c3ee990080`), and ICU death `MSPQ11T2` (SHA-256 `8d08422a7354953adc89895c0176bce2506de12b9ba970bec8929ab82c853dc2`). The ICU-death result followed a corrected-schema retry of `HYYHP96D`, whose preflight failure produced no scientific result. The final job statuses and results were already confirmed through canonical RunRelay. RRT and ICU-death artifacts were re-read directly from R2 for feature membership in this synthesis. The expired ventilation R2 share was not re-read, and its values come from the prior R2-verified GitHub checkpoint.

Code anchors: [src/160_evaluate_submission_exploratory_v2_1.py](https://github.com/vafaei-ar/mimic-semantic-signals/blob/e5772f7a1a40b2368465e1b95e24a04abc98cc2a/src/160_evaluate_submission_exploratory_v2_1.py#L65-L118) (comparator composition), [src/178_evaluate_extension_t1_decomposition_v2_1.py](https://github.com/vafaei-ar/mimic-semantic-signals/blob/e5772f7a1a40b2368465e1b95e24a04abc98cc2a/src/178_evaluate_extension_t1_decomposition_v2_1.py#L98-L179) (zero-for-no-note scalar scores), [src/178_evaluate_extension_t1_decomposition_v2_1.py](https://github.com/vafaei-ar/mimic-semantic-signals/blob/e5772f7a1a40b2368465e1b95e24a04abc98cc2a/src/178_evaluate_extension_t1_decomposition_v2_1.py#L249-L319) (point estimation and frozen D checks), [src/178_evaluate_extension_t1_decomposition_v2_1.py](https://github.com/vafaei-ar/mimic-semantic-signals/blob/e5772f7a1a40b2368465e1b95e24a04abc98cc2a/src/178_evaluate_extension_t1_decomposition_v2_1.py#L350-L546) (bootstrap refitting and seeds), and [src/preregistration_stats.py](https://github.com/vafaei-ar/mimic-semantic-signals/blob/e5772f7a1a40b2368465e1b95e24a04abc98cc2a/src/preregistration_stats.py#L19-L48) (patient-cluster resampling). All scientific code was executed at immutable commit `e5772f7a1a40b2368465e1b95e24a04abc98cc2a`.

No raw clinical records, text, row-level outcomes, cached embeddings, or patient-level predictions were moved or committed. This document adds no new modeling, changes no preregistration and submits no RunRelay job.
