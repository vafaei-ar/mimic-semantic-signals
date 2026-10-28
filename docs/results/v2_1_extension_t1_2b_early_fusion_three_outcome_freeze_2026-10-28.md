# Exploratory extension v2.1 — T1.2b 32-component early-fusion three-outcome result freeze

Date: 2026-10-28 (US Eastern)  
Status: **All three T1.2b final outcome evaluations completed; post-registration exploratory, not confirmatory**  
Primary registration: OSF `ahxn9` (DOI `10.17605/OSF.IO/AHXN9`); exploratory extension OSF project: `wmyb2`  
**Frozen scientific execution commit for all three outcomes:** `e5772f7a1a40b2368465e1b95e24a04abc98cc2a`  
Documentation branch: `extension-v2_1`. The JAMIA-ready `main` at `f57ddfbdc5ac6c700431a96b281b40cdd1505382` is not modified.

## Frozen design and primary estimand

T1.2b appends **exactly 32 PCA components** of frozen `BAAI/bge-large-en-v1.5` document embeddings to the registered rich structured HistGradientBoostingClassifier comparator D. PCA is **label-free**, `svd_solver=full`, without whitening. It is fitted only on note-available outer-training-fold rows. No-note rows have 32 zeros, while the registered `has_note` feature remains in D. PCA and both HGB models are refitted within each patient-cluster bootstrap replicate. All five patient-grouped partitions, the primary partition (`repeat_1`), and bootstrap seed `20260924` are frozen; comparator D was regenerated and validated.

**Primary estimand:** primary-partition out-of-fold `ΔAUROC = AUROC(D + 32-component early fusion) − AUROC(D)`. Uncertainty is a paired source-patient-cluster full-refit bootstrap, using **500 valid replicates per outcome**, with two-sided 95% percentile intervals. Point estimates and bootstrap means are distinct summaries. Five-partition variability, ΔAUPRC and the fixed 5% alert budget are secondary. There is **no T1.2b standalone text classifier**: standalone text-score learnability refers to the separate frozen T1.2 supervised late-fusion arm.

## Final primary-partition results

| Outcome | Stays / events / note-available stays | Comparator D AUROC | D + early fusion AUROC | Primary ΔAUROC | Bootstrap mean ΔAUROC | Two-sided 95% full-refit bootstrap CI for ΔAUROC |
|---|---|---:|---:|---:|---:|---|
| Invasive ventilation | 11,116 / 279 / 4,499 | 0.724675 | 0.721846 | **−0.002830** | +0.000355 | **[−0.024938, +0.026863]** |
| Renal replacement therapy | 19,395 / 314 / 7,709 | 0.973936 | 0.973451 | **−0.000485** | +0.000009 | **[−0.003479, +0.003209]** |
| MetaVision ICU death | 19,811 / 214 / 7,889 | 0.933382 | 0.933623 | **+0.000240** | −0.001250 | **[−0.010065, +0.006978]** |

**None of the three two-sided 95% primary full-refit intervals excludes zero.** There is no demonstrated reliable incremental AUROC for early fusion against rich D. This does **not** show equivalence, prove information redundancy, rule out smaller effects, or establish clinical utility.

### Secondary results and variation

| Outcome | Five-partition ΔAUROC range (number positive) | Primary ΔAUPRC | Two-sided 95% full-refit CI for ΔAUPRC | Primary net outcome events captured at fixed 5% alert budget, early fusion minus D | Two-sided 95% full-refit CI for net events per 1,000 stays |
|---|---|---:|---|---:|---|
| Ventilation | [−0.010836, +0.000642] (1/5) | −0.001970 | [−0.015004, +0.013430] | +10 | [−1.126620, +1.346630] |
| RRT | [−0.000980, +0.003448] (3/5) | −0.000038 | [−0.036183, +0.022783] | −4 | [−0.646117, +0.567216] |
| ICU death | [−0.001657, +0.009284] (4/5) | +0.006716 | [−0.027630, +0.028221] | −3 | [−0.556470, +0.531058] |

The signs of the five frozen-partition point estimates are mixed for RRT and ICU death. Ventilation is negative in four partitions. The bootstrap intervals above all cross zero. The 5% budget primary-partition net-event point contrasts do **not** establish benefit or harm.

The three-outcome **T1.2 supervised one-score late-fusion** evaluation was previously frozen separately, with primary ΔAUROC values `+0.001937` (ventilation), `−0.000800` (RRT), and `−0.000462` (ICU death). All three late-fusion primary intervals also crossed zero. Do not infer a statistically significant *between-fusion-strategy* contrast from these arm-specific intervals. The T1.2 standalone note-available embedding-score AUROCs were `0.615456`, `0.803578`, and `0.794347` respectively; they are interpretive signals, not incremental effects.

## Registered runtime gate and execution

The first 10 frozen-seed timing-only valid refits yielded projections below the predeclared 72-hour threshold for 500 replicates, so **500 valid full refits** (rather than 200) were selected for every outcome, without checking timing-run performance estimates. The full final run used 500 valid replicates with **zero replacements** for each outcome.

| Outcome | Timing RunRelay job | 500-replicate projected bootstrap time | Final RunRelay job | Final runtime, seconds | Final exit / valid / replacements |
|---|---|---:|---|---:|---|
| Ventilation | `1SGWSBWJ` | 17.750770 h | `HKPPJX6F` | 64,442.567 | 0 / 500 / 0 |
| RRT | `72A2942P` | 20.426889 h | `C146SQDF` | 71,894.067 | 0 / 500 / 0 |
| ICU death | `TQX1MACX` | 19.457435 h | `MX2QQ105` | 76,075.061 | 0 / 500 / 0 |

All final jobs ran exact scientific commit `e5772f7a1a40b2368465e1b95e24a04abc98cc2a` on project-bound workstation `pshjl4vf24`, under the named registered tasks and with original analysis definitions unchanged.

## Canonical safe aggregate artifact provenance

| Outcome | Declared aggregate JSON (project-relative) | SHA-256 |
|---|---|---|
| Ventilation | `outputs/multitask_benchmark/extension_t1_early_fusion_v2_1_ventilation.json` | `5c18cb7b9cad16d0a7dfd9a9ea85b9c47d6076f0dd7bc1b4d4e1e52aa125eb1d` |
| RRT | `outputs/multitask_benchmark/extension_t1_early_fusion_v2_1_rrt.json` | `baee85fafcc7d382194ee273f35905b7c87527174b1eb9b159a0075b39b283d0` |
| ICU death | `outputs/multitask_benchmark/extension_t1_early_fusion_v2_1_death.json` | `e1d91688b4d9f319516ec7356d6500418667e6a5117c8870a4fce27059a601b8` |

The ICU-death final was independently checked against the RunRelay Reader **canonical completed status, declared artifact metadata, and directly retrieved full JSON from R2 on 2026-10-28**. Ventilation and RRT values are reconciled to their earlier, separately verified GitHub result checkpoints, sourced from the corresponding R2 artifacts on 2026-10-25; those R2 shares are time limited. This Markdown preserves inspectable aggregate metrics and provenance but is **not** the original canonical JSON. No PHI, patient identifiers, notes, raw embeddings, row-level scores or predictions, secrets, or restricted records are included.

Related result checkpoints:
- `docs/results/v2_1_extension_t1_2b_early_fusion_ventilation_checkpoint_2026-10-25.md`
- `docs/results/v2_1_extension_t1_2b_early_fusion_rrt_checkpoint_2026-10-25.md`
- `docs/results/v2_1_extension_t1_2_bge_three_outcome_freeze_2026-10-22.md`

## Pending registered work and operational boundary

The next registered T1.4 **endpoint/treatment-language sensitivity** repeats T1.1 with frozen unstripped H6 notes, followed by T1.5 **A→D comparator-richness decomposition**. The user-registered stop rule applies after the planned T1.5 freeze absent an independent bedside-narrative dataset and new protocol. No unregistered analyses are authorized.

The T1.4 synthetic-only self-test `Q1E86E6G` **did not execute**: its GitHub Actions dispatch workflow `40270065292` was queued from 2026-10-26 04:37:57 UTC until 2026-10-27 00:57 UTC and then failed at the **one-time RunRelay dispatch authorization redemption** step with HTTP **409** (curl exit 22); all scientific execution steps were skipped. The canonical Reader reports `workflow_failed` and `no_result` with no artifacts. The specific reason for 409 (expiry versus other redemption conflict) is **not established by the workflow logs**. Investigate/reissue authorization under normal RunRelay lineage and safety rules before any retry. This is a dispatch-control failure, **not** a failed T1.4 scientific analysis. No retry is initiated by this result freeze.

Keep scientific execution commit `e5772f7a1a40b2368465e1b95e24a04abc98cc2a` immutable for these completed T1.2b results. Preserve the JAMIA-ready main branch.
