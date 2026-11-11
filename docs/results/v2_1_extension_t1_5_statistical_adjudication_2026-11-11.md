# T1.5 statistical adjudication and manuscript-reporting disposition

Date: 2026-11-11  
Project: Medical JEV, `mimic-semantic-signals`  
Scope: existing protocol, source-code review, validated aggregate results, and manuscript claims. **No new model fitting or patient-level reanalysis.**  
Frozen scientific execution commit: `e5772f7a1a40b2368465e1b95e24a04abc98cc2a`.  
Parent synthesis: [cross-outcome synthesis and QA](v2_1_extension_t1_cross_outcome_synthesis_method_qa_2026-11-10.md).

## Overall decision

**Proceed only with a narrowly worded exploratory descriptive supplement. Do not claim a causal or statistically established attenuation of text value with comparator richness.** The three registered T1.5 final jobs finished successfully and all 12 A/D AUROC confidence intervals and their 12 A/D AUPRC counterparts contain zero. The additional code review identifies one definite interpretation limitation, one deterministic algorithmic difference, and one unresolved numerical discrepancy. None establishes an unreported positive effect. None supports declaring equivalence.

| Question | Adjudicated status | Reporting consequence |
|---|---|---|
| Does the A-level text increment isolate information in note language? | **No. Confirmed design limitation.** | Call it augmentation by a supervised score with a built-in note-availability signal, not a content-only effect |
| Is the bootstrap seed difference a novel T1.5 implementation failure? | **No evidence of a novel failure. Confirmed inherited convention.** | Disclose the different deterministic inner-seed rules, but do not identify them as the proven cause of an estimate shift |
| Why does the ventilation A TF-IDF original point fall above the percentile interval? | **Unresolved from available aggregate evidence.** | Retain exact point and interval with a limitation. Do not center the interval on the original point or revise the prespecified analysis |
| Is there a significant A-versus-D interaction or attenuation? | **Not tested.** | Do not infer an A-minus-D effect from the two level-specific intervals |
| Can these results revise the preregistered primary conclusion? | **No. Post-registration exploratory.** | Keep primary H1–H3 results and the frozen JAMIA manuscript separate |

## 1. Note availability and what the thin-comparator estimand measures

The text-score functions set both training and test scores to **exactly zero for all stays without an eligible note**. They replace those defaults with supervised TF-IDF/logistic or embedding/logistic decision scores only for note-available stays. The downstream HGB model therefore receives a value distribution with a structural zero mass for no-note stays. A tree can potentially use this pattern to recover documentation availability. A genuine note may also produce a score close to zero, so this is an indirect and imperfect availability indicator.

The comparator-construction code assigns the initial 34 physiology, laboratory and urine features to level A. B adds treatment and support features. Neither A nor B contains the explicit `has_note` predictor. C adds note-count, note-length and related documentation-behavior variables, which can indirectly represent presence or absence. D adds `has_note`, note age and note categories explicitly. This is a visible design difference, independent of the observed model effects.

The manuscript's frozen Table 1 provides unadjusted documentation-availability differences:

| Outcome | Note available among cases | Note available among controls | Difference in percentage points |
|---|---:|---:|---:|
| Invasive ventilation | 135/279 (48.4%) | 4,364/10,837 (40.3%) | +8.1 |
| Renal replacement therapy | 143/314 (45.5%) | 7,566/19,081 (39.7%) | +5.8 |
| ICU death | 83/214 (38.8%) | 7,806/19,597 (39.8%) | −1.0 |

These descriptive differences support the possibility that documentation availability carries outcome information, especially for ventilation. They do **not** estimate the adjusted contribution of missingness to ΔAUROC. The results do not identify the gain attributable to clinical language alone. Reporting that A demonstrates text-content gain would conflate two sources of information.

**Adjudication:** This is an established limitation of the existing T1.5 contrast, not a software failure. The registered A/D comparisons remain reportable as augmentation experiments. They cannot establish a causal redundancy mechanism or isolate lexical/semantic information.

Source anchors: [text score defaults and note-specific replacement](https://github.com/vafaei-ar/mimic-semantic-signals/blob/e5772f7a1a40b2368465e1b95e24a04abc98cc2a/src/178_evaluate_extension_t1_decomposition_v2_1.py#L98-L179), [comparator A–D membership](https://github.com/vafaei-ar/mimic-semantic-signals/blob/e5772f7a1a40b2368465e1b95e24a04abc98cc2a/src/160_evaluate_submission_exploratory_v2_1.py#L65-L118), and [frozen manuscript Table 1](https://github.com/vafaei-ar/mimic-semantic-signals/blob/27176ec9c5bcdd0032ca095d894fabd2d424c431/manuscript/JAMIA_WORKING_DRAFT_2026-10-03.md#L75-L86).

## 2. Ventilation A TF-IDF original point versus bootstrap distribution

The previously verified ventilation result reports the original primary-fold ΔAUROC as **+0.022888200**, the 200-full-refit bootstrap mean as **+0.003557552**, and the percentile 95% interval as **[−0.012831, +0.020596]**. The original estimate exceeds the bootstrap mean by approximately **0.019331** AUROC and the upper percentile endpoint by approximately **0.002292** AUROC. The mean and the original estimate are different statistics.

The code establishes the following. The original point estimate pools out-of-fold predictions from the unresampled five-fold primary partition. Each bootstrap replicate instead draws source patients with replacement, duplicates all their associated ICU rows, retains the original fold assignment, refits the supervised text model and structured/augmented HGB models, then pools out-of-fold predictions over the resampled population. The code takes the 2.5th and 97.5th percentiles of the resulting 200 ΔAUROC values. It does not center those quantiles on the original statistic. Therefore, the percentile interval need not include the original estimate as a matter of construction.

Both paths use the same AUROC estimand, namely the difference between the augmented and structured baseline AUROCs. The HGB construction uses the same fixed model random seed. The D comparator is checked against its previously registered out-of-fold predictions within every original partition. These checks give no evidence of arithmetic subtraction or baseline-reconstruction errors. They **do not** validate sampling-distribution coverage or eliminate data-level causes.

The patient resampling and full refits can shift the empirical estimator distribution, especially with relatively rare events. An inner-fold seed change also occurs, as described next. However, **neither the source code nor the saved aggregate summary can apportion the observed 0.019331 shift** among sample reweighting, model instability, random inner splits and other effects. The published aggregate result stores moments and percentile endpoints, not the full patient-level bootstrap distributions or replicate predictions. The original ventilation R2 direct-text share has expired as of this review. Its previously validated aggregate freeze supplies the numerical evidence above.

**Adjudication:** Preserve the original estimate and the prespecified percentile interval, state that the interval includes zero, and flag the unusual displacement for statistical review. Do not calculate a new p-value, move the interval to contain the observed value, or imply a proven implementation defect.

Source anchors: [original point path](https://github.com/vafaei-ar/mimic-semantic-signals/blob/e5772f7a1a40b2368465e1b95e24a04abc98cc2a/src/178_evaluate_extension_t1_decomposition_v2_1.py#L241-L319), [source-patient bootstrap](https://github.com/vafaei-ar/mimic-semantic-signals/blob/e5772f7a1a40b2368465e1b95e24a04abc98cc2a/src/preregistration_stats.py#L19-L48), [replicate refitting and evaluation](https://github.com/vafaei-ar/mimic-semantic-signals/blob/e5772f7a1a40b2368465e1b95e24a04abc98cc2a/src/178_evaluate_extension_t1_decomposition_v2_1.py#L350-L412), [percentile quantiles](https://github.com/vafaei-ar/mimic-semantic-signals/blob/e5772f7a1a40b2368465e1b95e24a04abc98cc2a/src/178_evaluate_extension_t1_decomposition_v2_1.py#L471-L478), and [frozen ventilation result](v2_1_extension_t1_5_ventilation_final_checkpoint_2026-11-06.md).

## 3. Inner cross-validation seed offsets

The T1.5 original five-partition code uses `INNER_SEED_BASE + 100 * repeat_index + outer_fold`. The patient-cluster bootstrap uses `INNER_SEED_BASE + outer_fold`. For repeat 1, the base seed `20261005` yields five original inner-seed identifiers `20261106` through `20261110`, while bootstrap refits use `20261006` through `20261010`.

The same two-branch seed convention appears independently in the **earlier frozen T1.1 TF-IDF and T1.2 embedding implementations**. It is not a new T1.5-only deviation. Both original and bootstrap branches retain source-patient grouping. The registered T1.5 implementation clarification requires inner grouped fitting, full bootstrap refits and a deterministic bootstrap seed sequence. It does not explicitly require equal inner-fold random-state values across the unresampled and resampled data paths.

**Adjudication:** Record the seed difference as an inherited, deterministic implementation choice. It can alter inner fold assignments and fitted scores, so its numerical influence remains unknown. It is neither evidence of patient overlap nor a demonstrated explanation of the ventilation A shift. Repeating a numerical outcome analysis solely to harmonize the seeds after observing results would introduce a post hoc analysis and violate the current stop rule.

Source anchors: [T1.5 original and bootstrap seeds](https://github.com/vafaei-ar/mimic-semantic-signals/blob/e5772f7a1a40b2368465e1b95e24a04abc98cc2a/src/178_evaluate_extension_t1_decomposition_v2_1.py#L249-L277) and [bootstrap seeds](https://github.com/vafaei-ar/mimic-semantic-signals/blob/e5772f7a1a40b2368465e1b95e24a04abc98cc2a/src/178_evaluate_extension_t1_decomposition_v2_1.py#L369-L382), [T1.1 original](https://github.com/vafaei-ar/mimic-semantic-signals/blob/e5772f7a1a40b2368465e1b95e24a04abc98cc2a/src/172_evaluate_extension_t1_tfidf_v2_1.py#L426-L435) and [bootstrap](https://github.com/vafaei-ar/mimic-semantic-signals/blob/e5772f7a1a40b2368465e1b95e24a04abc98cc2a/src/172_evaluate_extension_t1_tfidf_v2_1.py#L580-L590), [T1.2 original](https://github.com/vafaei-ar/mimic-semantic-signals/blob/e5772f7a1a40b2368465e1b95e24a04abc98cc2a/src/174_evaluate_extension_t1_embedding_v2_1.py#L470-L484) and [bootstrap](https://github.com/vafaei-ar/mimic-semantic-signals/blob/e5772f7a1a40b2368465e1b95e24a04abc98cc2a/src/174_evaluate_extension_t1_embedding_v2_1.py#L630-L644), and [frozen clarification](https://github.com/vafaei-ar/mimic-semantic-signals/blob/e5772f7a1a40b2368465e1b95e24a04abc98cc2a/docs/registration/exploratory_extension_t1_decomposition_clarification_2026-10-06.md#L1-L52).

## 4. Statistical interpretation boundaries

The complete T1.5 results include **six A-level and six D-level** paired baseline-versus-augmented AUROC intervals across three outcomes and two text representations. All contain zero. Each corresponding ΔAUPRC interval also contains zero. The analysis uses only the frozen primary partition for inferential intervals, with four additional frozen patient-grouped partitions serving as stability checks. There is no inferential A-minus-D contrast, no causal mediator specification, and no T1.5 fixed-alert-budget result.

A point estimate of +0.022888 with an interval from −0.012831 to +0.020596 does not support the claim that the model improves discrimination. Because the intervals are not equivalence intervals and some allow nontrivial positive improvements, the results also do not establish absence of clinically useful information. The current data support a narrower observation: **the tested supervised scalar text scores did not demonstrate a reliable added AUROC over either A or D under the specified full-refit uncertainty procedure**.

The rich comparator D result remains useful because it includes documented note context, treatment and physiologic predictors. It asks whether adding the tested text representation improves discrimination **conditional on this comparator and these modeling choices**. It does not prove that the narrative has no independent content, and it cannot establish that comparator richness causally removed a text effect.

## 5. Proposed publication-safe supplement wording

### Supplementary Methods: supervised text and comparator richness

In a post-registration exploratory analysis, we evaluated a supervised TF-IDF score and a frozen-embedding supervised score as single added features to four increasingly detailed structured HistGradientBoosting models. The models used five patient-grouped outer cross-validation partitions. The thinnest model included 34 physiologic and laboratory predictors. Successively richer models added treatment/support, documentation behavior and note context. We estimated ΔAUROC and ΔAUPRC in every partition. For the thinnest and richest comparators, we computed two-sided percentile 95% intervals from 200 valid patient-cluster bootstrap replicates with complete refitting of the text and structured prediction models. The study selected 200 rather than 500 replicates using the prespecified 72-hour timing rule. We treated these analyses as descriptive sensitivity assessments.

### Supplementary Results: cross-outcome text augmentation

Across invasive ventilation, renal replacement therapy and ICU death, neither supervised text score demonstrated a reliable improvement in AUROC at the thinnest or richest structured comparator. All 12 reported 95% confidence intervals for ΔAUROC included zero. For ventilation, the original TF-IDF increment at the 34-feature comparator was +0.0229, with a 95% full-refit interval of −0.0128 to +0.0206. At the richest comparator, the corresponding increment was −0.0014, with an interval of −0.0147 to +0.0143. The point estimates did not follow a consistent monotonic pattern across outcomes. We did not estimate a paired A-versus-D contrast.

### Supplementary Discussion: limits of inference

The thinnest structured comparators did not contain an explicit note-availability variable, while the added text score took the value zero for stays without eligible notes. Consequently, the estimated increment may reflect documentation availability alongside clinical language content. The full-refit bootstrap distribution for the ventilation TF-IDF increment at the thinnest comparator also differed from its original point estimate. The existing aggregate outputs do not explain that difference. These exploratory results do not establish equivalence, absence of residual narrative information, or a causal explanation for changes across comparator levels.

## 6. Release and next-step decision

The current JAMIA working manuscript reports **3,904 main-text words against a stated 4,000-word limit** and focuses on the registered primary hypotheses. Do not silently insert post-registration exploratory claims into its abstract or primary results. The three paragraphs above are **candidate supplementary text**, not changes to the registered manuscript. A human statistical reviewer should first approve the explicit bootstrap-interpretation disclosure and confirm whether the inner seed convention requires any additional methodological caveat.

The existing registration prohibits new exploratory analyses after T1.5 without an independent bedside-narrative dataset and a separate protocol. This review has no authority to modify that stop rule. No outcome refitting, new RunRelay job, change to frozen code or revision to the registered statistical method occurred in this checkpoint.

Reproducibility anchors: prior [three-outcome synthesis](v2_1_extension_t1_cross_outcome_synthesis_method_qa_2026-11-10.md), [T1.5 ventilation](v2_1_extension_t1_5_ventilation_final_checkpoint_2026-11-06.md), [T1.5 RRT](v2_1_extension_t1_5_rrt_final_checkpoint_2026-11-08.md), and [T1.5 ICU death](v2_1_extension_t1_5_death_final_checkpoint_2026-11-10.md). This note preserves their previously verified aggregate evidence and does not substitute for R2 raw aggregate files.
