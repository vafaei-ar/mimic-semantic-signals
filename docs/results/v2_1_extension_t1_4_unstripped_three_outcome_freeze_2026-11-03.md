# Exploratory extension v2.1 — T1.4 unstripped TF-IDF three-outcome result freeze

Date: 2026-11-03 (US Eastern; final ICU-death completion observed at 2026-11-04T03:37:40.694Z)  
Status: **T1.4 endpoint/treatment-language sensitivity complete for all three registered outcomes; post-registration exploratory**  
Primary registration: OSF `ahxn9`; exploratory extension: OSF `wmyb2`  
**Frozen scientific execution commit (all T1.4 outcomes):** `e5772f7a1a40b2368465e1b95e24a04abc98cc2a`  
Documentation branch: `extension-v2_1`. **Do not alter JAMIA-ready `main`**.

## Frozen design and estimand

T1.4 repeats T1.1 with the **frozen full unstripped H6 note text** (`fixed_notes_full_v2_1_local.jsonl`), instead of the endpoint/treatment-language-stripped H6 note text. The T1.1 TF-IDF specification and L2-logistic supervised text-score fitting, training-fold-only vocabulary learning, patient-grouped inner cross-fitting, single text-score late fusion with HGB rich comparator D, five frozen outer patient-grouped partitions, and the primary `repeat_1` partition are retained. Comparator D represents rich physiology, treatment/support, documentation behavior, and note context. A source-patient-cluster bootstrap refits the complete text model and both HGB models in each replicate; the implementation attests to a same-patient inner-fold guard and seed sequence `20260924`.

**Primary estimand within each arm:** primary-partition out-of-fold `ΔAUROC = AUROC(D + supervised TF-IDF score) − AUROC(D)`. Report two-sided 95% full-refit patient-cluster percentile intervals and the five partition-level point estimates. These arm-specific intervals are **not paired uncertainty estimates for the stripped-versus-unstripped contrast**. The registered label is **endpoint/treatment-language sensitivity**, **not** a pure leakage estimate. The goal is descriptive sensitivity, not a causal estimate of leakage from words.

The registered mechanical bootstrap gate uses the median runtime of the first 10 valid refits: choose **200 valid final refits only if** projected duration for 500 exceeds 72 hours, otherwise **500**. All three projected runtimes fell below 72 hours, so all three final T1.4 evaluations used 500 valid full refits and discarded timing-only bootstrap performance estimates.

## Final T1.4 unstripped-note results: primary partition

| Outcome | Stays / events | Note-available stays | Standalone unstripped TF-IDF AUROC | Comparator D AUROC | D + unstripped TF-IDF AUROC | **Primary ΔAUROC** | **95% full-refit CI for ΔAUROC** |
|---|---:|---:|---:|---:|---:|---:|---:|
| Invasive ventilation | 11,116 / 279 | 4,499 | 0.643767 | 0.724675 | 0.728449 | **+0.003773** | **[−0.016243, +0.014625]** |
| Renal replacement therapy (RRT) | 19,395 / 314 | 7,709 | 0.911521 | 0.973936 | 0.974556 | **+0.000619** | **[−0.001953, +0.003572]** |
| MetaVision ICU death | 19,811 / 214 | 7,889 | 0.874127 | 0.933382 | 0.936676 | **+0.003294** | **[−0.005525, +0.008254]** |

All three primary ΔAUROC confidence intervals include zero. None demonstrates a reliable incremental discrimination improvement over rich D, despite a positive primary out-of-fold point estimate in each unstripped arm. These intervals do not prove equivalence or no residual narrative information.

| Outcome | Primary ΔAUPRC | 95% full-refit ΔAUPRC CI | Fixed 5% alert-budget net events in primary partition (unstripped augmented minus D) |
|---|---:|---:|---:|
| Invasive ventilation | +0.007763 | [−0.009839, +0.010230] | −1 |
| RRT | +0.010343 | [−0.015335, +0.026254] | −3 |
| MetaVision ICU death | +0.009884 | [−0.015846, +0.026429] | 0 |

All three ΔAUPRC intervals include zero. The fixed-alert results do not establish improved event capture. For ICU death, the primary 5% alert budget was **991 alerts per model**, and both models captured the same number of deaths. The ICU-death bootstrap mean net events per 1,000 stays was `+0.050471`, with 95% interval `[−0.405949, +0.507752]`. Do not interpret the observed AUROC increase as clinical benefit.

### Five frozen partition checks

| Outcome | Five ΔAUROC point estimates (frozen order) | Direction |
|---|---|---|
| Ventilation | `[+0.003773, −0.007704, +0.006193, −0.007430, +0.000263]` | 3 positive / 2 negative |
| RRT | `[+0.000619, +0.001313, +0.001214, −0.000660, +0.000843]` | 4 positive / 1 negative |
| ICU death | `[+0.003294, +0.005319, +0.003184, +0.004436, +0.002793]` | 5 positive / 0 negative |

ICU-death standalone note-available AUROC was `0.874126792` in `repeat_1` (7,889 note-available stays; 83 outcome events), and ranged `[0.874127, 0.906072]` across the five frozen partitions. All three outcomes met the prespecified **interpretive**, not inferential, standalone text-AUROC threshold of `0.60` in all five partitions.

The **bootstrap mean** is separate from the original point estimator. For ICU death, the mean ΔAUROC across 500 refits was `+0.001465762` with 95% percentile CI `[−0.005524655, +0.008254272]`, while the frozen primary-partition out-of-fold point estimator was `+0.003293705`. Do not replace the primary point estimator with the bootstrap mean.

## Frozen stripped T1.1 versus unstripped T1.4: descriptive sensitivity only

The historical stripped-note T1.1 three-outcome freeze (`docs/results/v2_1_extension_t1_1_tfidf_three_outcome_freeze_2026-10-13.md`; scientific commit `843d0ab5d356efbbb7ac888bd6dc925d20ed0946`) reports the following rounded stripped-arm primary ΔAUROCs and standalone note-available text AUROCs.

| Outcome | Stripped T1.1 ΔAUROC | Unstripped T1.4 ΔAUROC | **Unstripped minus stripped: descriptive ΔAUROC difference** | Stripped standalone text AUROC | Unstripped standalone text AUROC |
|---|---:|---:|---:|---:|---:|
| Ventilation | −0.00137 | +0.003773 | **approximately +0.00514** | 0.64023 | 0.643767 |
| RRT | −0.00068 | +0.000619 | **approximately +0.00130** | 0.87350 | 0.911521 |
| ICU death | +0.00339 | +0.003294 | **approximately −0.00010** | 0.85626 | 0.874127 |

T1.1 values are rounded and originate from a previously frozen GitHub results checkpoint, **not a freshly re-read T1.1 R2 artifact**. The arm-specific T1.1 and T1.4 bootstrap confidence intervals do not yield a paired confidence interval for this between-arm contrast. The descriptive contrast therefore cannot establish statistical significance of stripping effects, isolate information leakage, or support a causal claim. The RRT standalone text AUROC rises descriptively by about `0.03802` when unstripped, while its rich-D incremental discrimination remains unproven. The ICU-death incremental AUROC contrast is descriptively very similar in both arms, despite higher standalone unstripped text AUROC.

## Canonical RunRelay final jobs and provenance

All three final RunRelay jobs were **rechecked directly against canonical RunRelay Reader status during this 2026-11-03 continuation**: each had `status=completed`, `exit_code=0`, 500/500 valid full-refit patient-cluster replicates, scientific commit `e5772f7a1a40b2368465e1b95e24a04abc98cc2a`, machine `pshjl4vf24`, and one declared safe aggregate JSON.

| Outcome | Final job | Final runtime | Final safe aggregate JSON basename | SHA-256 |
|---|---|---:|---|---|
| Ventilation | `89Y0XG9A` | 122,995.801 s | `extension_t1_tfidf_unstripped_v2_1_ventilation.json` | `c0b047c5fb0d694d04751cf1f3a764bb0aa77bc301684f1b43563ed792e4cd93` |
| RRT | `TQ9S8WBX` | 162,991.075 s | `extension_t1_tfidf_unstripped_v2_1_rrt.json` | `b44f6395ad39c1fd3c410a7dffd140f5aa19cd96ead0330039a1dee661e0e8a7` |
| ICU death | `09C5F4R6` | 168,063.827 s | `extension_t1_tfidf_unstripped_v2_1_death.json` | `3500e7252c7af04e27c4f8d0052b4f2f11f080ff347e3944dd126e584d7469e1` |

Each artifact is under `outputs/multitask_benchmark/`. The **complete final ICU-death JSON (15,134 bytes)** was directly read from R2 in this continuation; its SHA-256 agreed with the separately declared Reader artifact metadata and it has no direct-text publication errors. Its R2 share expiry is `2026-11-07T03:37:41.909Z`. The ventilation and RRT final JSON artifacts were retrieved and read in their respective earlier continuations, with detailed provenance preserved at `docs/results/v2_1_extension_t1_4_unstripped_ventilation_final_checkpoint_2026-10-30.md` and `docs/results/v2_1_extension_t1_4_unstripped_rrt_final_checkpoint_2026-11-01.md`; those earlier figures in the table above are drawn from their frozen GitHub checkpoints plus newly rechecked canonical job metadata, rather than fresh R2 reads in this continuation.

All three timing jobs also completed with exit 0 and 10/10 valid timing refits:
- Ventilation: `KBCCPKH7`, projected 33.017078 h for 500 valid refits.
- RRT: `NR1Y1ZT3`, projected 43.216137 h.
- ICU death: `TG96ASAY`, projected 45.276923 h; its declared timing JSON SHA-256 `6c4c85be0f8ca8ec024e3c3be5fc7c6222f607938c920335c448a742d5d4aef5`.

In all three timing gates the 72-hour rule selected **500**. The ICU-death final completed with 500 valid refits and **zero replacements**. Refitted text-model/HGB uncertainty was estimated with source-patient bootstrap, not by treating the five partitions as independent replications.

**Data/security boundary:** No raw clinical notes, row-level predictions, patient identifiers, local model scores, private embeddings, or credentials are included in this GitHub documentation. Source data remain on the bound workstation. This file is an **aggregate results and provenance freeze**, not a replacement for canonical safe JSON.

## Interpretation and next bounded boundary

T1.4 is **complete** for all three frozen outcomes. Every 95% full-refit interval for incremental AUROC and AUPRC over rich comparator D includes zero. Strong standalone supervised text discrimination is compatible with outcome information present in bedside notes, but these results alone do not identify why incremental discrimination is small. The descriptive stripped-versus-unstripped comparisons also cannot establish leakage or a reliable stripping effect. Do not conflate this negative inference with proof of equivalence.

The **next predeclared scientific milestone is T1.5 comparator-richness decomposition**, beginning with named, **synthetic-only** task `validate_extension_t1_decomposition_v2_1`, and then prespecified A-through-D comparator analyses using the frozen T1.1 and T1.2 supervised text scores. T1.5 requires all five partitions at A through D and primary-partition full-refit bootstrap intervals at levels A and D only, according to `docs/registration/exploratory_extension_protocol_v2_1_2026-10-04.md`. No T1.5 job is launched by this result-freeze checkpoint.

**Source anchors:** `.runrelay/project.yaml`; `src/175_evaluate_extension_t1_tfidf_unstripped_v2_1.py`; `src/172_evaluate_extension_t1_tfidf_v2_1.py`; original T1.1 three-outcome freeze; the ventilation and RRT T1.4 checkpoints; final R2 JSON for `09C5F4R6`; the registered T1.4/T1.5 protocol.
