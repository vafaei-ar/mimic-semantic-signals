# Exploratory extension v2.1 — T1.1 supervised TF-IDF three-outcome result freeze

Date: 2026-10-13  
Status: **Completed, post-registration exploratory**  
Primary registration: `ahxn9`; exploratory extension OSF project: `wmyb2`  
Scientific execution commit (all outcomes): `843d0ab5d356efbbb7ac888bd6dc925d20ed0946`  
Repository branch for this results freeze: `extension-v2_1` (do not modify the JAMIA-ready `main`/tag).

## Design and estimand

T1.1 adds **one patient-grouped cross-fitted supervised TF-IDF/logistic text log-odds score** to the frozen rich comparator D (physiology, treatment/support, documentation behavior, and note context). The frozen five outer patient-grouped partitions, inner patient-grouped cross-fitting, training-fold-only TF-IDF vocabulary, and downstream HGB settings are retained. The primary estimand is primary-partition out-of-fold (OOF) **delta AUROC = AUROC(D + TF-IDF score) - AUROC(D)**. Paired patient-cluster bootstrap intervals refit the supervised text and downstream HGB components in every replicate. No-note rows receive a text score of zero while note availability remains represented in comparator D. All data-derived row scores stay local.

## All three final outcomes (primary partition)

| Outcome | N stays / events | Note-available stays | Standalone note-available text AUROC | Comparator D AUROC | D + TF-IDF AUROC | Primary delta AUROC | 95% paired full-refit bootstrap CI for delta AUROC |
|---|---:|---:|---:|---:|---:|---:|---:|
| Invasive ventilation | 11,116 / 279 | 4,499 | 0.64023 | 0.72468 | 0.72330 | -0.00137 | [-0.01493, +0.01468] |
| Renal replacement therapy | 19,395 / 314 | 7,709 | 0.87350 | 0.97394 | 0.97325 | -0.00068 | [-0.00230, +0.00269] |
| MetaVision ICU death | 19,811 / 214 | 7,889 | 0.85626 | 0.93338 | 0.93677 | +0.00339 | [-0.00625, +0.00784] |

All three final jobs report **500/500 valid full-refit bootstrap replicates**, without a protocol-dependent switch to 200. The RRT and death outputs report zero bootstrap replacements. The fixed 5% alert budget in the primary partition produced a net **-2 detected RRT events** and **-5 detected ICU deaths** for D + TF-IDF relative to D, despite the death AUROC point increase.

### Five-partition and uncertainty checks

- Ventilation: previously reviewed point-estimate delta AUROC values were negative across the five partitions; the 95% refit interval includes zero.
- RRT: the five point delta AUROCs range from **-0.000685 to +0.002371** (mixed sign); its interval includes zero.
- ICU death: the five point delta AUROCs range from **+0.002416 to +0.005067** (all positive); despite consistent point direction, the primary refit interval includes zero.
- All three standalone note-available text AUROCs exceed the **prespecified interpretive** 0.60 threshold. This shows outcome discrimination by text among note-available stays, **not** established incremental information after comparator D.
- No outcome has a 95% full-refit delta-AUROC interval excluding zero. Do not call these results equivalence, proof of no residual signal, or a statistically demonstrated positive increment. Do not promote the exploratory T1.1 results to the registered H1–H3 analysis.

### Interpretation under the frozen extension decision table

The present T1.1 result is consistent with substantial predictability of outcomes from bedside lexical text and little **detectable** additional discrimination after a rich structured comparator in this particular *single-scalar late-fusion* implementation. It **does not yet establish** the decision-table conclusion for *all* representations: T1.2 supervised frozen embeddings and T1.2b 32-component early fusion still need their prespecified outcome evaluations. It also does not by itself distinguish redundancy from losses caused by compression, interactions, or comparator richness; those distinctions require the frozen T1.2/T1.2b/T1.5 analyses.

For ICU death, explicitly report the discordance between positive five-partition AUROC point differences and the non-positive-at-fixed-alert-budget primary contrast. Do not infer a clinical benefit from the AUROC point increase.

## Artifact provenance and retrieval status at freeze

| Outcome | RunRelay job | Canonical execution result | Safe aggregate result JSON | SHA-256 |
|---|---|---|---|---|
| Ventilation | `R8M4K2V7` | completed, exit 0, 500/500 | `outputs/multitask_benchmark/extension_t1_tfidf_v2_1_ventilation.json` | `be56300188728ef18a89024cd11acceb06931d9f600832c67bb3317e4b578349` |
| RRT | `S9R4K2M7` | completed, exit 0, 500/500 | `outputs/multitask_benchmark/extension_t1_tfidf_v2_1_rrt.json` | `e66bdf718e2570d784d3bbde6b97a6d4001fd11822e80ebbae778cc5f3a63ea0` |
| ICU death | `M5BT7CTQ` | completed, exit 0, 500/500 | `outputs/multitask_benchmark/extension_t1_tfidf_v2_1_death.json` | `fb8feac2dcdce9fb8e57b7dd4e1d63ea153d416a8c44e95498d2ae0ba31c35b1` |

The RRT and ICU-death **direct-text R2 aggregate artifacts were successfully read on 2026-10-13**. The ventilation artifact's RunRelay R2 share expired on 2026-10-12; ventilation performance and interval figures in this document were transcribed from the **previously verified project checkpoint**, not represented as a fresh October 13 artifact read. Re-retrieve from an authorized preserved local source before manuscript-final independent verification if necessary. This Markdown is an aggregate evidence synopsis, **not** a replacement for the three canonical JSON artifacts. No clinical note text, identifiers, row-level predictions, raw data, or credentials appear here.

## Frozen forward boundary

Next planned representations (not completed by this T1.1 freeze) are T1.2 frozen `BAAI/bge-large-en-v1.5` embedding + supervised scalar late fusion, then T1.2b early fusion of 32 training-fold PCA components. Their original protocols, classifier-selection constraints, patient grouping, and 10-replicate/72-hour runtime decision rule remain unchanged. Do not select endpoints, change models, or reinterpret thresholds based on the signs in the table above.

## Related source documentation

- `docs/EXTENSION_PLAN_v2_1_2026-10-04.md`
- `docs/registration/exploratory_extension_protocol_v2_1_2026-10-04.md`
- `docs/registration/exploratory_extension_t1_implementation_clarification_2026-10-05.md`
- `docs/registration/exploratory_extension_t1_embedding_classifier_clarification_2026-10-05.md`
