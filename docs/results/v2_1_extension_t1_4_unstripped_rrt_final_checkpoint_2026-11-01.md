# Exploratory extension v2.1 — T1.4 unstripped TF-IDF RRT final checkpoint

Date: 2026-11-01 (US Eastern)  
Status: **Final renal-replacement-therapy T1.4 endpoint/treatment-language sensitivity completed; post-registration exploratory**  
Primary registration: OSF `ahxn9`; exploratory extension: OSF `wmyb2`  
**Exact scientific execution commit:** `e5772f7a1a40b2368465e1b95e24a04abc98cc2a`  
Documentation branch: `extension-v2_1`. Preserve the separate JAMIA-ready `main` branch.

## Frozen design

The prespecified T1.4 sensitivity repeats the T1.1 supervised TF-IDF/L2-logistic single-score late-fusion comparison, using the frozen **full, unstripped H6 notes** (`fixed_notes_full_v2_1_local.jsonl`) rather than stripped notes. The intended scientific change is the note-corpus variant. The rich structured HGB comparator D, training-fold-only vocabulary and model fitting, patient-grouped inner cross-fitting, five frozen outer patient-grouped partitions, primary `repeat_1`, seed `20260924`, and source-patient-cluster full-refit bootstrap are retained. Each bootstrap replicate refits the text model and both HGB models with the same-patient inner-fold guard.

The primary estimand is primary-partition out-of-fold `ΔAUROC = AUROC(D + unstripped supervised TF-IDF score) − AUROC(D)`. Uncertainty is a two-sided 95% paired patient-cluster percentile interval from **500 valid complete refits**. Bootstrap means must not be substituted for the original out-of-fold point estimate. The registered stripped-versus-unstripped T1.4 exercise is **endpoint/treatment-language sensitivity, not a pure leakage estimate**.

## Verified unstripped RRT final results

| Quantity | Canonical final aggregate |
|---|---:|
| Source cohort stays / RRT events / note-available stays | 19,395 / 314 / 7,709 |
| Comparator D AUROC | 0.973936290 |
| D + unstripped TF-IDF AUROC | 0.974555507 |
| **Primary-partition ΔAUROC relative to D** | **+0.000619217** |
| Bootstrap mean ΔAUROC (distinct from the point estimate) | +0.000696312 |
| **Two-sided 95% full-refit bootstrap CI, ΔAUROC** | **[−0.001952942, +0.003571597]** |
| Comparator D AUPRC | 0.344353129 |
| D + unstripped TF-IDF AUPRC | 0.354695884 |
| Primary-partition ΔAUPRC | +0.010342755 |
| Bootstrap mean ΔAUPRC | +0.003929601 |
| 95% full-refit bootstrap CI, ΔAUPRC | [−0.015335465, +0.026254465] |
| Standalone unstripped text-score AUROC (7,709 note-available, 143 events) | 0.911520808 |
| Valid full-refit patient-cluster bootstraps / replacements | **500 / 0** |

All five frozen-partition primary ΔAUROC point estimates in order: `[+0.000619217, +0.001312874, +0.001213900, −0.000660443, +0.000842536]` (range `[−0.000660443, +0.001312874]`, four positive and one negative). All five ΔAUPRC point estimates are positive, range `[+0.002821521, +0.013272667]`. The standalone note-available AUROC ranges `[0.906537, 0.915286]` and exceeds the predeclared **interpretive** 0.60 threshold in all five partitions. Comparator D regeneration maximum absolute prediction difference was `9.996344030316351e-17`.

At the prespecified **5% fixed alert budget** (970 alerts per model), the augmented model captured **three fewer RRT events** than D in the primary partition. Primary sensitivity changed `−0.009554140`; PPV changed `−0.003092784`. The bootstrap mean net captured events per 1,000 stays was `+0.039091` with 95% interval `[−0.516306, +0.566896]`. The fixed-budget bootstrap interval crosses zero and does **not** establish clinical benefit or harm.

**Interpretation:** The 95% full-refit bootstrap intervals for ΔAUROC, ΔAUPRC, and fixed-budget net events all include zero. These data show strong standalone discrimination in note-available stays, but **no demonstrated reliable incremental discrimination over rich comparator D**. Do not claim equivalence, negligible information content, or benefit based on positive point estimates.

## Stripped versus unstripped: descriptive comparison, not a paired estimate

The frozen T1.1 **stripped-note** results checkpoint (`docs/results/v2_1_extension_t1_1_tfidf_three_outcome_freeze_2026-10-13.md`, scientific execution commit `843d0ab5d356efbbb7ac888bd6dc925d20ed0946`) documented RRT comparator D AUROC `0.97394`, augmented AUROC `0.97325`, primary ΔAUROC `−0.00068` (rounded), standalone text AUROC `0.87350`, and full-refit bootstrap ΔAUROC CI `[−0.00230, +0.00269]`.

| Primary-partition metric | Stripped T1.1 (historical checkpoint, rounded) | Unstripped T1.4 (verified R2) |
|---|---:|---:|
| Comparator D AUROC | 0.97394 | 0.973936 |
| D + TF-IDF AUROC | 0.97325 | 0.974556 |
| ΔAUROC relative to D | −0.00068 | +0.000619 |
| 95% full-refit interval for arm-specific ΔAUROC | [−0.00230, +0.00269] | [−0.00195, +0.00357] |
| Standalone note-available text AUROC | 0.87350 | 0.911521 |

The **descriptive difference in arm-specific primary ΔAUROC** (unstripped minus stripped) is approximately **+0.00130**, using rounded historical T1.1 values. The unstripped standalone text-score AUROC is descriptively about **0.03802 higher** than the historical stripped text score. Neither is a paired bootstrap estimate of a text-stripping effect; no paired stripped-versus-unstripped confidence interval was computed here. The direction may reflect endpoint/treatment-language sensitivity, but the data **do not isolate pure leakage**.

**Stripped-arm source limitation:** The T1.1 RRT `S9R4K2M7` final aggregate JSON, `outputs/multitask_benchmark/extension_t1_tfidf_v2_1_rrt.json` with historical SHA-256 `e66bdf718e2570d784d3bbde6b97a6d4001fd11822e80ebbae778cc5f3a63ea0`, was previously retrieved and documented on 2026-10-13. The canonical RunRelay Reader could **not** retrieve that older job or its artifact on 2026-11-01; this checkpoint uses the **historically verified GitHub document**, not a fresh R2 read for the stripped arm.

## Timing gate, jobs, and immutable provenance

- The synthetic-only unstripped wrapper self-test was passed by `XBWBSA62` after the earlier authorization-timeout job `Q1E86E6G` failed before scientific execution. No scientific parameters were changed.
- The registered timing job `NR1Y1ZT3` completed with exit code 0, **10/10 valid** timing refits, zero replacements, and median **311.156186 seconds** per valid refit. Its mechanical 500-refit projection was **43.216137 hours**, below the registered **72-hour** threshold; thus **500** final valid refits were selected. Performance estimates from timing-only bootstrap replicates were discarded. Declared timing JSON: `outputs/multitask_benchmark/extension_t1_tfidf_unstripped_timing_v2_1_rrt.json`, SHA-256 `e6c9acbc92d526ecd4dc691ea9fed7ccff6fcd9b2b61e0bcfdd62df6ae7821ad`.
- **Final job `TQ9S8WBX`**: named task `evaluate_extension_t1_unstripped_v2_1_rrt`, manual Telegram approval; canonical status `completed`, exit code `0`, **500/500 valid refits and zero replacements**; runtime **162,991.075 seconds** (45 h 16 min 31 s), observed final `2026-11-01T17:42:43.827Z`. Bound machine `pshjl4vf24`; frozen execution commit `e5772f7a1a40b2368465e1b95e24a04abc98cc2a`.
- **Sole declared safe aggregate output**: `outputs/multitask_benchmark/extension_t1_tfidf_unstripped_v2_1_rrt.json`, **15,304 bytes**, SHA-256 **`b44f6395ad39c1fd3c410a7dffd140f5aa19cd96ead0330039a1dee661e0e8a7`**. Canonical RunRelay Reader verified the same path/SHA and direct-text availability. The **complete final R2 JSON was retrieved and read on 2026-11-01**. The final safe share expires at `2026-11-04T17:42:44.676Z`.
- This Markdown is a reproducible **aggregate/provenance checkpoint**, not the canonical JSON. Raw clinical notes, patient-level records, identifiers, predictions, embeddings, and local model-score files remain local; none are included.

Frozen source anchors: `.runrelay/project.yaml`; `src/175_evaluate_extension_t1_tfidf_unstripped_v2_1.py` with T1.1 code `src/172_evaluate_extension_t1_tfidf_v2_1.py`; `scripts/run_extension_t1_tfidf_unstripped_full_v2_1_rrt.sh`; `docs/registration/exploratory_extension_protocol_v2_1_2026-10-04.md`; stripped T1.1 checkpoint above; RunRelay control job `jobs/TQ9S8WBX.json`.

## Registered continuation boundary

T1.4 **ICU-death timing and full bootstrap** remain outstanding, followed by registered T1.5 comparator-richness decomposition. Avoid launching unregistered scientific alternatives or revising results based on their direction. Preserve the JAMIA-ready `main` branch. **No additional RunRelay job is submitted in this bounded checkpoint.**
