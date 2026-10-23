# Exploratory extension v2.1 — T1.2 frozen-BGE supervised late-fusion three-outcome result freeze

Date: 2026-10-22 (US Eastern)  
Status: **Completed; post-registration exploratory, not a confirmatory reanalysis**  
Primary registration: OSF `ahxn9` (DOI `10.17605/OSF.IO/AHXN9`)  
Exploratory extension OSF project: `wmyb2`  
Scientific execution commit (all three final jobs): `e2ce4ed1107a9d9b2c007e5d4c2ed40337f62179`  
Results branch: `extension-v2_1` (do not modify the JAMIA-ready `main`, `f57ddfbdc5ac6c700431a96b281b40cdd1505382`)

## Frozen design and primary estimand

T1.2 uses the single prespecified local offline frozen embedding model `BAAI/bge-large-en-v1.5`, revision `d4aa6901d3a41ba39fb536a557fa166f842b0e09`. Its label-free cached 1,024-dimensional document embeddings use 448-content-token chunks with 64-token overlap, normalized chunk vectors, unweighted mean pooling, and document-level L2 normalization. The embedding cache across the three frozen note-available cohorts was completed in RunRelay job `4PZ0GZMF` (20,097 note records); embeddings remain local.

A supervised L2-logistic classifier selects `C` from `[0.01, 0.1, 1, 10, 100]` in training-only, five-fold patient-grouped inner CV. Its cross-fitted **single log-odds embedding score** is added to the registered rich structured HistGradientBoostingClassifier comparator **D**. The outer analysis uses the five frozen patient-grouped partitions. No-note rows receive an embedding score of 0, while note availability remains represented in D. The comparator predictions are explicitly regenerated and checked against the frozen comparator.

**Primary estimand:** out-of-fold, primary-partition `delta AUROC = AUROC(D + supervised embedding score) - AUROC(D)`. The 95% percentile interval uses a paired **source-patient-cluster full-refit bootstrap**: logistic `C` selection, embedding classifier fitting, and both HGB models are refit within each valid replicate, preserving patient-level fold isolation. Five-partition ranges, ΔAUPRC, and outcomes captured at a fixed 5% alert budget are secondary. Standalone supervised embedding-score AUROC is evaluated only among note-available stays; the 0.60 threshold is interpretive, not a validity boundary.

## Final primary-partition results

| Outcome | Stays / events | Note-available stays | D AUROC | D + embedding AUROC | Primary ΔAUROC | Bootstrap mean ΔAUROC | Two-sided 95% full-refit bootstrap CI | Standalone note-available embedding AUROC |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| Invasive ventilation | 11,116 / 279 | 4,499 | 0.724675 | 0.726613 | +0.001937 | +0.001424 | [-0.014232, +0.017353] | 0.615456 |
| Renal replacement therapy | 19,395 / 314 | 7,709 | 0.973936 | 0.973136 | -0.000800 | -0.000002 | [-0.002648, +0.002391] | 0.803578 |
| MetaVision ICU death | 19,811 / 214 | 7,889 | 0.933382 | 0.932920 | -0.000462 | +0.000092 | [-0.006327, +0.006802] | 0.794347 |

**No T1.2 outcome has a 95% full-refit delta-AUROC interval excluding zero.** All three final jobs reached **500/500 valid full-refit replicates, with zero replacements**, using the 500-valid-replicate target selected *before the final jobs* by the frozen timing gate. The primary-partition point estimates and bootstrap means are separate summaries; do not substitute one for the other.

### Five-partition variation and learnability

| Outcome | Five frozen-partition ΔAUROC point-estimate range | Five-partition standalone note-available embedding AUROC range | 5% alert budget: net events identified by D + embedding versus D, primary partition |
|---|---|---|---:|
| Invasive ventilation | [-0.010509, +0.001937] (4/5 negative) | [0.544063, 0.615456] | +1 |
| RRT | [-0.000800, +0.001997] (mixed signs) | [0.797060, 0.820212] | 0 |
| ICU death | [-0.001418, +0.004807] (mixed signs) | [0.778535, 0.806209] | -3 |

The primary-partition standalone score passes the protocol's **interpretive** AUROC 0.60 threshold for all three outcomes. Ventilation is only marginally above that threshold in the primary partition and **falls below 0.60 in three other partitions**; avoid portraying that outcome's learnability as strong or stable. The RRT and death standalone discrimination is consistently above 0.60 across the five partitions. These observations do not imply reliable incremental discrimination over D.

### Secondary precision–recall metric

| Outcome | Primary D AUPRC | Primary D + embedding AUPRC | Primary ΔAUPRC | Full-refit bootstrap mean ΔAUPRC | 95% bootstrap CI for ΔAUPRC |
|---|---:|---:|---:|---:|---|
| Ventilation | 0.081271 | 0.084467 | +0.003196 | +0.000071 | [-0.010972, +0.009916] |
| RRT | 0.344353 | 0.347632 | +0.003279 | -0.000206 | [-0.015543, +0.017517] |
| ICU death | 0.301736 | 0.317073 | +0.015336 | +0.000990 | [-0.015512, +0.020011] |

Every secondary ΔAUPRC interval also crosses zero. In particular, the ICU-death primary-partition AUPRC point increase should **not** be framed as established precision–recall or clinical benefit.

## Prespecified timing gate and execution

The frozen rule selected **500** rather than 200 valid bootstraps for each outcome because the first 10 frozen-seed timing-only replicates projected no more than 72 hours for 500. Timing-replicate performance estimates were discarded; the final full-refit estimates above were calculated from the final runs.

| Outcome | Timing RunRelay job | Projected 500-replicate runtime | Final RunRelay job | Actual final runtime | Valid/replacements |
|---|---|---:|---|---:|---|
| Ventilation | `ERD8W4PA` | 33.23 h | `TDRBB70W` | 32 h 28 m 13 s | 500 / 0 |
| RRT | `VZADM6BA` | 49.96 h | `5E1BC892` | 64 h 58 m 08 s | 500 / 0 |
| ICU death | `TZB3V470` | 54.55 h | `GQJ7WBMX` | 56 h 43 m 50 s | 500 / 0 |

The 72-hour rule is a **selection gate** based on timing-replicate projection, not a promise that actual work will finish within 72 hours. The final RunRelay task timeout remained 75 hours; no protocol-dependent target change, retry, or new analysis was used to produce these outcomes.

## RunRelay aggregate artifact provenance

| Outcome | Canonical safe aggregate JSON path | Declared SHA-256 | Retrieval/provenance as of freeze |
|---|---|---|---|
| Ventilation | `outputs/multitask_benchmark/extension_t1_embedding_v2_1_ventilation.json` | `2cce87bc6294d79bdb765d188d5eba841cbcd0299636763fd76fb41265ef235a` | Canonical Reader confirms completed, exit 0, 500/500 and declared artifact; direct-text artifact was **previously successfully read on 2026-10-17**; R2 share expired on 2026-10-20, and was **not** readable again on 2026-10-22 |
| RRT | `outputs/multitask_benchmark/extension_t1_embedding_v2_1_rrt.json` | `cc6c49d82df02dca8f1f9035ebb71555a5beedd3820e1bdaf270683258a35216` | Canonical Reader completed, exit 0, 500/500; safe aggregate direct-text **read anew on 2026-10-22** |
| ICU death | `outputs/multitask_benchmark/extension_t1_embedding_v2_1_death.json` | `32c8e0e9e434f2816e41587aa89074bba2f1a1675c54ccb8a6af5071bc7371b7` | Canonical Reader completed, exit 0, 500/500; safe aggregate direct-text **read anew on 2026-10-22** |

All three final jobs ran the exact frozen scientific commit `e2ce4ed1107a9d9b2c007e5d4c2ed40337f62179` on the bound project workstation. The declared artifacts are aggregate-only. No note text, case IDs, patient-level predictions, raw embeddings, restricted clinical records, credentials, or sensitive local file contents are included in this freeze. This summary is **not** a replacement for canonical safe JSON evidence; re-access to the expired ventilation share needs an authorized preserved local source for any independent artifact re-audit.

## Interpretation and boundary to next prespecified tasks

The T1.2 data support standalone outcome discrimination by a supervised frozen-embedding scalar for all three primary partitions, with **no detectable positive incremental AUROC** over the rich comparator D under the specified late-fusion implementation. These negative incremental findings are consistent with, but do not prove, redundancy of some narrative information under a rich comparator. Do **not** claim statistical equivalence, absence of all residual bedside-text information, or superiority based solely on secondary point differences.

The one-dimensional supervised text score may fail to capture interactions between individual embedding dimensions and structured covariates. Therefore T1.2 results **cannot adjudicate** the prespecified 32-component PCA **T1.2b early-fusion** arm. Comparator-level sensitivity **T1.5** is likewise required to distinguish signal redundancy from a comparator-richness effect. The registered H1–H9 results, model definitions, frozen cohort boundaries, and primary JAMIA-ready package remain untouched. Do not add unregistered models/analyses based on observed signs.

### Related frozen source material

- `docs/EXTENSION_PLAN_v2_1_2026-10-04.md`
- `docs/registration/exploratory_extension_protocol_v2_1_2026-10-04.md`
- `docs/registration/exploratory_extension_embedding_implementation_clarification_2026-10-05.md`
- `docs/registration/exploratory_extension_t1_embedding_classifier_clarification_2026-10-05.md`
- `docs/results/v2_1_extension_t1_1_tfidf_three_outcome_freeze_2026-10-13.md`
