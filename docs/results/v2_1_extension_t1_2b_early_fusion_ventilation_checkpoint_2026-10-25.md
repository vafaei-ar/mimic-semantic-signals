# Exploratory extension v2.1 — T1.2b early-fusion ventilation checkpoint

Date: 2026-10-25 (US Eastern)  
Status: **Completed for invasive ventilation; post-registration exploratory; other T1.2b outcomes not yet frozen**  
Primary registration: OSF `ahxn9`; exploratory extension OSF project: `wmyb2`  
Scientific execution commit: `e5772f7a1a40b2368465e1b95e24a04abc98cc2a`  
Result documentation branch: `extension-v2_1`. The JAMIA-ready `main` baseline at `f57ddfbdc5ac6c700431a96b281b40cdd1505382` is protected.

## Frozen design

This is the predeclared T1.2b **32-component early-fusion** analysis, not the previously completed T1.2 one-dimensional supervised late-fusion analysis. Frozen `BAAI/bge-large-en-v1.5` document vectors undergo label-free PCA (`n_components=32`, `svd_solver=full`, no whitening) fitted only among note-available rows in each outer training fold. The resulting 32 components are added directly to the registered rich structured HGB comparator D. Missing-note rows receive 32 zeros, and the `has_note` indicator stays in D. PCA and both HGB models are refitted within every patient-cluster bootstrap replicate. The five original patient-grouped partitions and frozen bootstrap seed sequence are retained. No alternative component counts, models, or missing-note encodings were tried.

**Primary estimand:** primary-partition OOF `ΔAUROC = AUROC(D + 32-component early fusion) − AUROC(D)`.

## Verified ventilation results

| Quantity | Result |
|---|---:|
| Stays / outcome events / note-available stays | 11,116 / 279 / 4,499 |
| Comparator D AUROC | 0.724675 |
| D + early fusion AUROC | 0.721846 |
| **Primary-partition ΔAUROC** | **−0.002830** |
| Bootstrap mean ΔAUROC (a separate summary, not the point estimate) | +0.000355 |
| Two-sided 95% percentile full-refit CI, ΔAUROC | **[−0.024938, +0.026863]** |
| Comparator D AUPRC | 0.081271 |
| D + early fusion AUPRC | 0.079301 |
| Primary-partition ΔAUPRC | −0.001970 |
| Two-sided 95% full-refit CI, ΔAUPRC | [−0.015004, +0.013430] |
| Valid patient-cluster full-refit bootstraps / replacements | **500 / 0** |

Five frozen-partition ΔAUROC point estimates: `[−0.002830, −0.010836, +0.000642, −0.008583, −0.006297]`, range `[−0.010836, +0.000642]` (four negative and one positive). These partition point estimates are descriptive; the primary reported 95% CI comes from the full-refit patient-cluster bootstrap of the frozen primary partition.

At the fixed 5% alert budget, the primary partition contains 556 alerts in each model. Early fusion caught **10 more events** than D as a point contrast, but the full-refit bootstrap mean net-events-per-1,000 contrast was `+0.130169` with 95% CI `[−1.126620, +1.346630]`. This does **not** establish a clinical benefit.

**Interpretation:** There is no demonstrated positive incremental discrimination for the ventilation outcome with 32-component early fusion against comparator D; the primary CI crosses zero. This does not establish equivalence, exclude possible benefit or harm, or adjudicate the other outcomes and comparator-richness task T1.5. T1.2b has no standalone text score by protocol; interpretive standalone learnability belongs to the frozen T1.2 analysis.

## Timing gate and execution provenance

- Synthetic-only early-fusion validation: RunRelay `E5GA80YS`, completed with exit 0 on this execution commit.
- Timing gate: RunRelay `1SGWSBWJ`, completed with exit 0; ten valid timing-only replicates, zero replacements; median `127.805541` seconds per replicate, projected `17.750770` hours for 500. The frozen 72-hour threshold therefore selected **500 valid replicates** rather than 200.
- Final evaluation: RunRelay **`HKPPJX6F`**, task `evaluate_extension_t1_early_fusion_v2_1_ventilation`, completed 2026-10-24 22:28:35 UTC, exit 0; actual runtime `64,442.567` seconds, 500/500 valid full-refit replicates, no replacements; machine `pshjl4vf24`.
- The timing-only performance estimates were discarded. The final bootstrap independently recomputed from the same frozen seed sequence, starting at child seed index zero; thus the first ten seed indices are included in the final set through fresh refits rather than reusing timing-only performance estimates.
- **Canonical safe aggregate artifact:** `outputs/multitask_benchmark/extension_t1_early_fusion_v2_1_ventilation.json` (18,987 bytes). **SHA-256:** `5c18cb7b9cad16d0a7dfd9a9ea85b9c47d6076f0dd7bc1b4d4e1e52aa125eb1d`. RunRelay Reader confirmed the artifact was published without errors and the complete aggregate JSON was retrieved directly from R2 on 2026-10-25. Its temporary share can expire; this Markdown is an aggregate scientific checkpoint, not a replacement for the canonical JSON.
- Row-level predictions, note text, embeddings, patient identifiers, and restricted clinical data remained local and are not included here.

## Next frozen work and boundaries

The T1.2b RRT final is already running as RunRelay `C146SQDF`, with execution pinned to the unchanged scientific commit above. The predeclared ICU-death final remains the next sequential manual-approval job after the RRT final is verified. Do not run either final concurrently with an existing same-project long job. Preserve the extension registration, the JAMIA-ready main branch, the five frozen partitions and the 72-hour runtime rule. No unregistered analyses are authorized by this checkpoint.

Source of truth: RunRelay Reader canonical status and direct-text R2 artifact for `HKPPJX6F`; code `src/176_evaluate_extension_t1_early_fusion_v2_1.py`; predeclared protocol `docs/registration/exploratory_extension_protocol_v2_1_2026-10-04.md`.
