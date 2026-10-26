# Exploratory extension v2.1 — T1.2b early-fusion RRT checkpoint

Date: 2026-10-25 (US Eastern)  
Status: **Completed for renal replacement therapy; post-registration exploratory; ICU-death T1.2b final still pending**  
Primary registration: OSF `ahxn9`; exploratory extension OSF project: `wmyb2`  
Scientific execution commit: `e5772f7a1a40b2368465e1b95e24a04abc98cc2a`  
Result documentation branch: `extension-v2_1`. The JAMIA-ready `main` baseline at `f57ddfbdc5ac6c700431a96b281b40cdd1505382` remains protected.

## Frozen design and estimand

This is the predeclared T1.2b **32-component early-fusion** analysis, distinct from the previously completed T1.2 one-dimensional supervised late-fusion analysis. The frozen `BAAI/bge-large-en-v1.5` document vectors undergo label-free PCA (`n_components=32`, `svd_solver=full`, no whitening), fitted among note-available rows inside every outer training sample. The resulting 32 PCA components are appended directly to the registered rich structured HistGradientBoostingClassifier comparator D. Rows without notes receive 32 zeros, while note availability (`has_note`) stays in D. PCA and both HGB models are refit inside every valid source-patient-cluster bootstrap replicate.

The five frozen patient-grouped partitions, primary partition `repeat_1`, seed sequence `20260924`, and original comparator D are unchanged. No alternative component counts, solvers, models, or missing-note encodings were evaluated.

**Primary estimand:** primary-partition out-of-fold `ΔAUROC = AUROC(D + 32-component early fusion) − AUROC(D)`. The full-refit patient-cluster bootstrap gives a two-sided 95% percentile interval. The five-partition range, ΔAUPRC, and fixed 5% alert-budget contrasts are secondary.

## Verified RRT final results

| Quantity | Result |
|---|---:|
| Stays / outcome events / note-available stays | 19,395 / 314 / 7,709 |
| Comparator D AUROC | 0.973936 |
| D + 32-component early-fusion AUROC | 0.973451 |
| **Primary-partition ΔAUROC** | **−0.000485** |
| Bootstrap **mean** ΔAUROC (separate from primary point estimate) | +0.000009 |
| Two-sided 95% percentile full-refit CI, ΔAUROC | **[−0.003479, +0.003209]** |
| Comparator D AUPRC | 0.344353 |
| D + early-fusion AUPRC | 0.344315 |
| Primary-partition ΔAUPRC | −0.000038 |
| Full-refit bootstrap mean ΔAUPRC | −0.006245 |
| Two-sided 95% full-refit CI, ΔAUPRC | [−0.036183, +0.022783] |
| Valid source-patient-cluster full-refit bootstraps / replacements | **500 / 0** |

The five frozen-partition ΔAUROC point estimates, in order, are `[−0.000485, +0.000379, +0.002634, −0.000980, +0.003448]`, range `[−0.000980, +0.003448]` (two negative and three positive). The bootstrap interval pertains to the primary partition only, not a confidence interval across the five partition point estimates. Recreated comparator D predictions agreed with the frozen comparator up to a reported maximum absolute difference of `9.996344030316351e−17`.

At the fixed **5% alert budget**, the primary partition contained 970 alerts per model. Early fusion captured **four fewer RRT events** than comparator D (a descriptive primary-partition contrast). The full-refit bootstrap mean net-events-caught difference per 1,000 stays was `−0.053535`, with a two-sided 95% interval of `[−0.646117, +0.567216]`. These secondary estimates do **not** establish a clinical difference.

**Interpretation:** The primary ΔAUROC and its interval do not demonstrate reliable incremental discrimination from early fusion over rich comparator D in RRT. This is not statistical equivalence and does not rule out smaller benefit or harm. The result should be reported irrespective of direction. The separate T1.2 supervised late-fusion RRT ΔAUROC was `−0.000800` (95% CI `[−0.002648, +0.002391]`), but these two arm-specific intervals are **not** a paired test between fusion strategies. T1.2b has no separate standalone text score by protocol.

## Timing gate, job identity and provenance

- Synthetic-only early-fusion validation: RunRelay `E5GA80YS`, completed with exit 0 at the unchanged T1.2b scientific commit.
- Predeclared timing gate: RunRelay `72A2942P`, completed with exit 0 on the same commit, ten valid timing-only replicates with zero replacements. Median runtime was `147.073601` seconds per valid replicate; multiplying by 500 projected `20.426889` hours, below the 72-hour cap, hence **500 final valid replicates**. Timing-only performance estimates were discarded.
- Final RRT early-fusion evaluation: RunRelay **`C146SQDF`**, named task `evaluate_extension_t1_early_fusion_v2_1_rrt`, completed on **2026-10-25 at 21:12:59 US Eastern** (2026-10-26T01:12:59Z), exit 0. Actual execution runtime `71,894.067` seconds (19 h 58 m 14 s); 500/500 valid refits, zero replacements; bound machine `pshjl4vf24`; original frozen seed sequence preserved in the final run.
- The full bootstrap recomputed the analysis under the frozen seed sequence with fresh PCA and HGB refits. Timing-only performance estimates were not substituted for final full-refit estimates.
- **Canonical safe aggregate JSON:** `outputs/multitask_benchmark/extension_t1_early_fusion_v2_1_rrt.json` (19,035 bytes); **SHA-256:** `baee85fafcc7d382194ee273f35905b7c87527174b1eb9b159a0075b39b283d0`. RunRelay Reader confirmed completed execution, successful artifact publication with no publication errors, and direct retrieval of the complete aggregate JSON from R2 on 2026-10-25. The R2 share expires on 2026-10-28 at 21:13 US Eastern; this Markdown is a result/provenance checkpoint, **not a substitute for the canonical JSON**.
- No raw notes, embeddings, patient identifiers, row-level predictions, or restricted clinical data are placed in this documentation checkpoint.

## Scientific boundary and next step

The earlier T1.2b ventilation final was completed and documented separately in `docs/results/v2_1_extension_t1_2b_early_fusion_ventilation_checkpoint_2026-10-25.md`. The prespecified T1.2b **ICU-death final** is the remaining outcome: its timing job `TQX1MACX` selected 500 refits under the same 72-hour gate. Its final evaluation is a manual-approval RunRelay task and should be submitted only through the normal named-task, exact-commit and Telegram approval workflow after checking for duplicate active jobs. No ICU-death final is submitted by creating this checkpoint.

The downstream preregistered T1.4 stripped/unstripped sensitivity and T1.5 comparator-richness decomposition remain in scope, but are not initiated here. Do not add unregistered analyses. Preserve the primary JAMIA-ready `main` branch and original preregistered hypotheses.

**Source of truth:** RunRelay Reader status and direct-text R2 artifact for `C146SQDF`; project code `src/176_evaluate_extension_t1_early_fusion_v2_1.py` at `e5772f7a1a40b2368465e1b95e24a04abc98cc2a`; protocol `docs/registration/exploratory_extension_protocol_v2_1_2026-10-04.md`.
