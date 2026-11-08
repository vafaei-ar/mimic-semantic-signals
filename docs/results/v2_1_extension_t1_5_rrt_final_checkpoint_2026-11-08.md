# Exploratory extension v2.1: T1.5 RRT comparator-richness final checkpoint

Date: 2026-11-08 (US Eastern)  
Status: **Final renal replacement therapy (RRT) T1.5 comparator-richness analysis completed, post-registration exploratory.** Ventilation T1.5 completed earlier; ICU-death T1.5 remains outstanding.  
Primary registration: OSF `ahxn9`; exploratory extension: OSF `wmyb2`.  
**Frozen scientific execution commit:** `e5772f7a1a40b2368465e1b95e24a04abc98cc2a`  
Documentation branch: `extension-v2_1`. Preserve JAMIA-ready `main` and do not alter registered parameters.

## Frozen design, population, and estimand

T1.5 repeats the frozen A-through-D Open-Jev structured comparator levels with the supervised scalar **T1.1 TF-IDF** and **T1.2 BGE embedding** representations from the registered **stripped H6 note corpus**. This is distinct from the unstripped-note T1.4 sensitivity. Source-patient-grouped outer partitions, training-only supervised text model fitting, the frozen HGB model configuration, and inner-fold isolation are retained by the registered implementation. Global out-of-fold text scores are not reused as downstream HGB training inputs. Each comparator receives its own HGB baseline and separately augmented TF-IDF/embedding model.

Registered estimand for each comparator level and text representation: primary-partition out-of-fold **ΔAUROC = AUROC(structured baseline + one supervised text score) − AUROC(structured baseline)**, with analogous ΔAUPRC. Point estimates are reported for all five frozen patient-grouped partitions at levels A, B, C and D. The prespecified source-patient-cluster full text/HGB refit bootstrap provides **two-sided 95% percentile intervals at levels A and D only**. These are level-specific paired model comparisons, **not** paired A-minus-D contrast intervals. T1.5 is exploratory comparator-richness sensitivity, **not causal mediation**.

Frozen MetaVision RRT cohort: **19,395 ICU stays**, **314 RRT events**, **7,709 note-available stays**.

## Primary partition results (repeat_1, seed 20260924)

| Comparator level | Features | Baseline AUROC | + TF-IDF AUROC | TF-IDF ΔAUROC | + embedding AUROC | Embedding ΔAUROC |
|---|---:|---:|---:|---:|---:|---:|
| A: 34 structured features | 34 | 0.969887 | 0.970284 | **+0.000397** | 0.970052 | **+0.000165** |
| B: + treatment/support | 42 | 0.973277 | 0.973114 | **−0.000163** | 0.972477 | **−0.000800** |
| C: + documentation behavior | 50 | 0.973710 | 0.973752 | **+0.000042** | 0.973805 | **+0.000094** |
| D: registered rich comparator | 57 | 0.973936 | 0.973251 | **−0.000685** | 0.973136 | **−0.000800** |

| Comparator level | Baseline AUPRC | + TF-IDF AUPRC | TF-IDF ΔAUPRC | + embedding AUPRC | Embedding ΔAUPRC |
|---|---:|---:|---:|---:|---:|
| A: 34 structured features | 0.336692 | 0.339859 | +0.003167 | 0.339195 | +0.002502 |
| B: + treatment/support | 0.333981 | 0.334022 | +0.000042 | 0.340454 | +0.006473 |
| C: + documentation behavior | 0.339420 | 0.344092 | +0.004672 | 0.334091 | −0.005328 |
| D: registered rich comparator | 0.344353 | 0.348154 | +0.003801 | 0.347632 | +0.003279 |

**Descriptive interpretation:** The 34-feature level A baseline already has AUROC 0.969887, versus 0.973936 at level D. Primary TF-IDF ΔAUROC is +0.000397 at A and −0.000685 at D. All primary text increments are small and mixed in direction. No monotonic attenuation across A–D is established; these point estimates alone do not test A-minus-D differences or imply causal mediation.

## All five frozen patient-grouped partitions

Each array below follows outer frozen seeds `20260924`, `20260925`, `20260926`, `20260927`, `20260928`, respectively. The repeated partitions are stability checks, not independent patient samples or formal inferential replicates.

| Level | TF-IDF ΔAUROC by partition | Embedding ΔAUROC by partition |
|---|---|---|
| A: 34 structured features | `[+0.000397, +0.000338, +0.000106, +0.001370, +0.000292]` | `[+0.000165, −0.000159, −0.001285, +0.001024, +0.000554]` |
| B: + treatment/support | `[−0.000163, −0.000334, −0.000846, +0.000627, +0.000141]` | `[−0.000800, +0.000404, −0.000326, +0.000170, +0.000484]` |
| C: + documentation behavior | `[+0.000042, −0.000358, −0.000921, +0.000394, +0.001492]` | `[+0.000094, −0.000242, +0.000170, −0.000052, +0.002267]` |
| D: registered rich comparator | `[−0.000685, +0.001124, +0.000881, +0.000106, +0.002371]` | `[−0.000800, +0.001503, +0.000967, −0.000271, +0.001997]` |

| Level | TF-IDF ΔAUPRC by partition | Embedding ΔAUPRC by partition |
|---|---|---|
| A: 34 structured features | `[+0.003167, +0.012627, −0.006921, +0.000262, +0.006764]` | `[+0.002502, −0.002547, −0.006222, −0.012869, +0.006713]` |
| B: + treatment/support | `[+0.000042, −0.001196, −0.014845, −0.005550, +0.002514]` | `[+0.006473, +0.005678, −0.010478, −0.008392, −0.001956]` |
| C: + documentation behavior | `[+0.004672, −0.003820, +0.000624, +0.013361, +0.004403]` | `[−0.005328, +0.006951, +0.005715, +0.005854, +0.000823]` |
| D: registered rich comparator | `[+0.003801, +0.017382, −0.001314, +0.006551, −0.000313]` | `[+0.003279, +0.008024, +0.003423, +0.014150, −0.002827]` |

At level A, all five TF-IDF ΔAUROC point estimates are positive but between +0.000106 and +0.001370. At level D, TF-IDF ΔAUROC is negative in the first repeat and positive in the other four. This pattern is not evidence of a reliable incremental effect or a tested comparator-richness trend.

## Registered full-refit uncertainty (A and D only)

The prespecified timing gate selected **200** valid final source-patient-cluster complete refits, with zero single-class replacements. Each bootstrap replicate refits supervised text and HGB models. The **original frozen out-of-fold point estimate must not be substituted with the bootstrap mean**; all intervals here are two-sided 95% percentile intervals.

| Level and score | Original ΔAUROC point | Bootstrap mean ΔAUROC | 95% percentile CI for ΔAUROC |
|---|---:|---:|---|
| A: 34 structured features, TF-IDF | +0.000397 | +0.000353 | **[−0.002030, +0.003366]** |
| A: 34 structured features, Embedding | +0.000165 | +0.000057 | **[−0.002686, +0.003096]** |
| D: registered rich comparator, TF-IDF | −0.000685 | +0.000380 | **[−0.001830, +0.002553]** |
| D: registered rich comparator, Embedding | −0.000800 | +0.000048 | **[−0.002685, +0.002289]** |

| Level and score | Original ΔAUPRC point | Bootstrap mean ΔAUPRC | 95% percentile CI for ΔAUPRC |
|---|---:|---:|---|
| A: 34 structured features, TF-IDF | +0.003167 | +0.000532 | **[−0.016993, +0.018097]** |
| A: 34 structured features, Embedding | +0.002502 | −0.000719 | **[−0.017521, +0.015305]** |
| D: registered rich comparator, TF-IDF | +0.003801 | +0.002149 | **[−0.014779, +0.021769]** |
| D: registered rich comparator, Embedding | +0.003279 | +0.000171 | **[−0.016324, +0.018555]** |

**Inference:** All eight ΔAUROC and ΔAUPRC level-specific full-refit intervals cross zero. Neither supervised TF-IDF nor embedding demonstrates reliable incremental discrimination at the prespecified A and D levels. These results do not prove equivalence or the absence of predictive signal in clinical notes. No paired A-minus-D bootstrap contrast and no registered fixed-alert-budget operational result were provided by this T1.5 JSON. Do not claim a statistically significant A-to-D attenuation or clinical benefit.

## Canonical RunRelay and artifact provenance

- Synthetic-only helper validation `P12HZ35M`: completed with exit 0 at the same frozen scientific commit; no clinical data or declared artifacts.
- Timing job `RP5RTD8W`, named task `time_extension_t1_decomposition_v2_1_rrt`: completed with exit 0, **10/10 valid timing-only refits**, no replacements. Timing median **771.012258846 s/refit**; projected **107.085036 hours** for 500, above the frozen 72-hour threshold, so the mechanical rule selected **200**. Timing-only bootstrap performance estimates were discarded. Sole declared timing aggregate JSON: `outputs/multitask_benchmark/extension_t1_decomposition_timing_v2_1_rrt.json`, SHA-256 `1c2e75ada4065f63b6c474cdd383de291f7d330c5f415e9ad6c3ebd08a9ca342` (successfully retrieved from R2 in prior continuation).
- **Final job `YHH9WXER`**, named task `evaluate_extension_t1_decomposition_v2_1_rrt`: canonical completed, exit code 0, **200/200 valid full refits**, **zero replacements**, runtime **163741.138 seconds** (approximately 45.484 hours), bound machine `pshjl4vf24`, exact scientific execution commit `e5772f7a1a40b2368465e1b95e24a04abc98cc2a`; Reader final observation `2026-11-08T13:03:59.927Z`.
- The **only declared final safe aggregate output** is `outputs/multitask_benchmark/extension_t1_decomposition_v2_1_rrt.json`, **31,861 bytes**, SHA-256 **`40263dfda4ff32be4aa0cdc255de8115a4d16d639b8ad4c0fc7bf3c3ee990080`**. The complete final JSON was read via canonical RunRelay Reader's direct-text R2 retrieval on 2026-11-08, and its SHA matched the separately declared artifact metadata. Share status `shared`, no skipped artifacts or direct-text publishing errors, expiration `2026-11-11T13:04:00.915Z`.

All results here are derived from the **actual canonical R2 JSON**, not recreated from source code. The JSON preserves frozen input and split hashes; no raw notes, patient identifiers, row-level predictions, cached clinical embeddings, secrets, or restricted patient-level records are copied to this public documentation. This Markdown result checkpoint is not a substitute for the canonical aggregate artifact.

Source/registration anchors: `.runrelay/project.yaml`, `docs/registration/exploratory_extension_protocol_v2_1_2026-10-04.md`, `src/178_evaluate_extension_t1_decomposition_v2_1.py`, `scripts/run_extension_t1_decomposition_full_v2_1_rrt.sh`, and the private RunRelay control files `jobs/RP5RTD8W.json` and `jobs/YHH9WXER.json`.

## Next registered boundary and stop rule

With the RRT final result verified, **ventilation and RRT T1.5 are complete**. The remaining registered outcome is **MetaVision ICU death**, starting with the synthetic-validated named task `time_extension_t1_decomposition_v2_1_death`, then, if successful, its timing-selected final registered full-refit analysis. An independent dataset with genuine bedside narrative would require its own protocol before any unplanned outcome analysis. Preserve the registered post-T1.5 stop rule. **This documentation checkpoint submits no new RunRelay job.**
