# Exploratory extension v2.1: T1.5 ICU-death comparator-richness final checkpoint

Date: 2026-11-10 (US Eastern)  
Status: **Final T1.5 MetaVision ICU-death comparator decomposition complete**. This completes the **three registered T1.5 outcomes** (invasive ventilation, RRT and ICU death); the cross-outcome scientific synthesis and manuscript framing remain separate writing/QA tasks.  
Primary registration: OSF `ahxn9`; exploratory extension: OSF `wmyb2`.  
**Frozen scientific execution commit:** `e5772f7a1a40b2368465e1b95e24a04abc98cc2a`  
Documentation branch: `extension-v2_1`. Do not alter JAMIA-ready `main`.

## Prespecified design and population

Post-registration exploratory T1.5 evaluates the registered **T1.1 stripped-note supervised TF-IDF/L2-logistic scalar score** and **T1.2 stripped-note frozen BGE embedding/L2-logistic scalar score**, each added individually to level-specific HGB structured comparators A–D. The supervised text-score training and inner folds are confined to the corresponding outer training folds. No global OOF score is reused as an HGB training input. Frozen seeds and five source-patient-grouped outer partitions are retained. These are *stripped* notes, not the unstripped-note T1.4 sensitivity.

MetaVision ICU-death cohort: **19,811 ICU stays**, **214 ICU-death events**, and **7,889 note-available stays**. The comparable structured feature count rises from **34 (A)** to **46 (B)** with treatment/support, **54 (C)** with documentation behavior, and **61 (D)** for the rich registered comparator including note context.

The estimand at each comparator level is **ΔAUROC = AUROC(structured HGB augmented by one supervised scalar text score) − AUROC(structured HGB)**. The analogous quantity is ΔAUPRC. Report all five frozen outer partitions at every A–D level. The predeclared 95% **two-sided percentile confidence intervals**, from source-patient-cluster full text-model/HGB refit bootstrap of the primary partition (`repeat_1`), apply **only to levels A and D**. Neither model-specific CIs nor visual changes across A–D constitute a formal paired A-minus-D contrast; this is **not causal mediation**.

## Primary frozen partition (repeat_1; seed 20260924)

| Comparator | Features | Baseline AUROC | + TF-IDF AUROC | TF-IDF ΔAUROC | + embedding AUROC | Embedding ΔAUROC |
|---|---:|---:|---:|---:|---:|---:|
| A: 34 structured | 34 | 0.926849 | 0.927352 | **+0.000503** | 0.922168 | **−0.004681** |
| B: + treatment/support | 46 | 0.935357 | 0.935607 | **+0.000251** | 0.934043 | **−0.001314** |
| C: + documentation behavior | 54 | 0.933557 | 0.935547 | **+0.001990** | 0.933959 | **+0.000402** |
| D: registered rich comparator | 61 | 0.933382 | 0.936771 | **+0.003389** | 0.932920 | **−0.000462** |

| Comparator | Baseline AUPRC | + TF-IDF AUPRC | TF-IDF ΔAUPRC | + embedding AUPRC | Embedding ΔAUPRC |
|---|---:|---:|---:|---:|---:|
| A: 34 structured | 0.286555 | 0.284282 | −0.002273 | 0.285990 | −0.000565 |
| B: + treatment/support | 0.302384 | 0.302199 | −0.000185 | 0.310777 | +0.008393 |
| C: + documentation behavior | 0.296882 | 0.306598 | +0.009717 | 0.316478 | +0.019596 |
| D: registered rich comparator | 0.301736 | 0.304847 | +0.003111 | 0.317073 | +0.015336 |

These are **original frozen out-of-fold point estimates**, not bootstrap means. In the primary partition, the TF-IDF ΔAUROC is **+0.003389 at D**, versus **+0.000503 at A**. Therefore a simple monotonically decreasing text increment as comparator richness increases is not supported for ICU death. A positive point estimate alone is not evidence of reliable incremental discrimination.

## Five frozen patient-grouped outer partitions

Arrays follow `repeat_1` through `repeat_5` with seeds `20260924`, `20260925`, `20260926`, `20260927` and `20260928`. Repeated partitions share the same cohort and are **not independent inference replicates**.

| Comparator | TF-IDF ΔAUROC (five partitions) | Embedding ΔAUROC (five partitions) |
|---|---|---|
| A: 34 structured | `[+0.000503, +0.003621, +0.002307, +0.000720, +0.001942]` | `[−0.004681, +0.005222, −0.001784, +0.003683, −0.000265]` |
| B: + treatment/support | `[+0.000251, −0.000047, −0.003280, +0.000019, +0.004702]` | `[−0.001314, +0.003182, +0.000485, −0.000016, −0.000894]` |
| C: + documentation behavior | `[+0.001990, −0.000536, +0.001786, +0.001605, +0.003026]` | `[+0.000402, +0.000235, +0.001915, +0.000319, −0.000233]` |
| D: registered rich comparator | `[+0.003389, +0.003104, +0.004005, +0.002416, +0.005067]` | `[−0.000462, +0.004807, +0.003623, +0.002201, −0.001418]` |

| Comparator | TF-IDF ΔAUPRC (five partitions) | Embedding ΔAUPRC (five partitions) |
|---|---|---|
| A: 34 structured | `[−0.002273, +0.011358, +0.015688, −0.000329, +0.014144]` | `[−0.000565, +0.013658, +0.013713, −0.001786, +0.008108]` |
| B: + treatment/support | `[−0.000185, −0.000424, +0.008869, +0.004439, +0.014230]` | `[+0.008393, +0.012354, +0.012918, −0.005823, +0.013903]` |
| C: + documentation behavior | `[+0.009717, +0.013617, +0.002143, +0.012275, +0.022909]` | `[+0.019596, +0.007845, +0.010225, −0.003295, +0.019802]` |
| D: registered rich comparator | `[+0.003111, +0.002549, +0.007159, +0.002749, +0.016599]` | `[+0.015336, −0.000917, +0.020120, +0.003301, +0.007449]` |

Level-D TF-IDF ΔAUROC is positive in all five frozen partitions (range **+0.002416 to +0.005067**), but this directional consistency is not a full-refit uncertainty interval and does **not** establish a statistically reliable effect.

## Registered 200-valid-refit primary-partition uncertainty: A and D only

The 72-hour runtime rule applied to the **first 10 valid timing-only joint A/D refits**. With median **816.040979 seconds/refit**, 500 would project **113.339025 hours**, above the registered **72-hour cap**. The rule therefore selected **200 valid final refits**. The successful final job completed **200/200**, with **zero replacements**. Each refit regenerates the supervised text scores and retrains the HGB model. The timing-only bootstrap performance estimates were discarded.

| Level and score | Original ΔAUROC point | Full-refit bootstrap mean | 95% percentile CI for ΔAUROC |
|---|---:|---:|---|
| A: 34 structured, TF-IDF | +0.000503 | +0.000255 | **[−0.007845, +0.007828]** |
| A: 34 structured, Embedding | −0.004681 | −0.000477 | **[−0.008746, +0.006446]** |
| D: registered rich comparator, TF-IDF | +0.003389 | +0.000837 | **[−0.005907, +0.007898]** |
| D: registered rich comparator, Embedding | −0.000462 | +0.000011 | **[−0.006668, +0.006261]** |

| Level and score | Original ΔAUPRC point | Full-refit bootstrap mean | 95% percentile CI for ΔAUPRC |
|---|---:|---:|---|
| A: 34 structured, TF-IDF | −0.002273 | +0.001444 | **[−0.016336, +0.018112]** |
| A: 34 structured, Embedding | −0.000565 | −0.001332 | **[−0.021227, +0.019047]** |
| D: registered rich comparator, TF-IDF | +0.003111 | +0.002445 | **[−0.016603, +0.026829]** |
| D: registered rich comparator, Embedding | +0.015336 | +0.000433 | **[−0.015998, +0.019971]** |

**Inference:** All eight available 95% A- and D-level ΔAUROC and ΔAUPRC percentile intervals contain zero. The prespecified full-refit analysis does **not demonstrate statistically reliable incremental discrimination or precision-recall performance** for ICU death at either comparator level. This is **not a proof of equivalence or absence of clinical information** in notes. No paired A-minus-D contrast CI was output, and the T1.5 result JSON does not supply fixed 5% alert-budget effects. Do not claim a statistically supported attenuation trend or an operational benefit. The bootstrap mean is not the original point estimate.

## Canonical RunRelay jobs, failure recovery, and provenance

- **DERSHP4Y**, `time_extension_t1_decomposition_v2_1_death`: completed, exit code 0, 10/10 valid timing refits and zero replacements, with the mechanical 200-valid-refit decision described above. Sole declared safe aggregate timing artifact: `outputs/multitask_benchmark/extension_t1_decomposition_timing_v2_1_death.json` (29,910 bytes), SHA-256 `f899b1f1f7dedfbd06c45a3cdc5b8f9adc9a4e07e61e34aaced050e4e37637a9` (retrieved directly from R2 in the preceding continuation).
- **HYYHP96D**, original manual-approval final task, **failed preflight, exit 2, runtime 3.1 seconds, no artifacts or scientific execution**. GitHub Actions runner log diagnosed a control-job schema issue: the original description was **1,245 characters**, exceeding schema-v2's 1,200-character limit. No scientific evidence came from this job. Its control file is preserved in the private RunRelay repository.
- **MSPQ11T2**, manual-approved correction with `retry_of: HYYHP96D`, same named task and exact scientific commit: **canonical completed, exit code 0**, runtime **166269.884 seconds** (about **46.186 hours**), machine `pshjl4vf24`, **200/200 valid full refits, zero replacements**; Reader final observation `2026-11-11T00:05:06.012Z`.
- The **only declared final safe aggregate result** is `outputs/multitask_benchmark/extension_t1_decomposition_v2_1_death.json`, **32,225 bytes**, SHA-256 **`8d08422a7354953adc89895c0176bce2506de12b9ba970bec8929ab82c853dc2`**, with R2 share status **`shared`**, no skipped artifacts or direct-text publish errors, and share expiry `2026-11-14T00:05:08.389Z`. The complete final JSON was retrieved through RunRelay Reader's declared direct-text R2 route and its SHA-256 matched the separately reported artifact metadata.
- All project code was executed at **`e5772f7a1a40b2368465e1b95e24a04abc98cc2a`**. The present Markdown documentation commit is separate and must not be mistaken for an updated scientific execution commit.

Only aggregate derived results are documented here. No PHI, identifiable clinical notes, raw patient-level labels, clinical embeddings, or row-level predictions have been added to this public repository. The canonical R2 JSON (which includes source data/split-hash provenance) remains the authoritative complete artifact; this Markdown is a readable checkpoint, not a replacement.

## Three-outcome T1.5 completion and registered stop rule

The registered T1.5 comparator-richness decomposition is **computationally complete for all three outcomes**. The other frozen result checkpoints are:

- Invasive ventilation: `docs/results/v2_1_extension_t1_5_ventilation_final_checkpoint_2026-11-06.md` (final RunRelay job `YG5Z0JK8`).
- Renal replacement therapy: `docs/results/v2_1_extension_t1_5_rrt_final_checkpoint_2026-11-08.md` (final RunRelay job `YHH9WXER`).

Across the three outcome-specific registered A/D complete-refit analyses, their documented 95% ΔAUROC intervals include zero for both scalar text representations. This is evidence of **no demonstrated reliable incremental AUROC gain at A or D**, not equivalence and not a causal estimate of redundancy. The cross-outcome scientific narrative and statistical-method QA should be handled separately without introducing new, unregistered outcome analyses.

**Stop rule:** No new exploratory analyses after T1.5 freeze without an independent dataset with genuine bedside narrative and a separate protocol. In this bounded continuation, **no follow-on RunRelay job was submitted**.
