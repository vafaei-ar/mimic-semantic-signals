# Exploratory extension v2.1 — T1.5 ventilation comparator-richness final checkpoint

Date: 2026-11-06 (US Eastern)  
Status: **Final invasive-ventilation T1.5 A-through-D supervised-text comparator decomposition completed; post-registration exploratory.** The other two registered T1.5 outcomes remain outstanding.  
Primary registration: OSF `ahxn9`; exploratory extension: OSF `wmyb2`  
**Exact scientific execution commit:** `e5772f7a1a40b2368465e1b95e24a04abc98cc2a`  
Documentation branch: `extension-v2_1`. Preserve JAMIA-ready `main`.

## Prespecified design and estimands

T1.5 repeats the previously frozen comparator levels A–D with the registered **stripped-note T1.1 TF-IDF** and **T1.2 frozen BGE embedding** supervised scalar scores. These are **not** the unstripped T1.4 scores. The synthetic-only T1.5 helper self-test `P12HZ35M` passed before any T1.5 outcome analysis.

For each comparator level, model the difference in out-of-fold AUROC and AUPRC between the registered HGB structured comparator and HGB augmented by one cross-fitted supervised text score, evaluating the **same frozen five outer patient-grouped partitions**. Inner text-score training and hyperparameter selection occur strictly inside the outer training data; global out-of-fold text scores must not be reused for model training. Comparator levels increase structured-data richness: **A 34 features**, **B 42** after treatment/support, **C 50** after documentation behavior, and **D 57** for the registered rich comparator including note context.

The predeclared inferential analysis uses **two-sided 95% percentile intervals from source-patient-cluster full text-model/HGB refits on primary `repeat_1` at A and D only**, not at B and C. This study is exploratory comparator-richness sensitivity, **not causal mediation**. Arm-specific bootstrap intervals are not paired confidence intervals for the A-minus-D contrast. The five partitions are not independent bootstrap replicates.

## Primary frozen partition (`repeat_1`, seed 20260924)

Cohort: **11,116 MetaVision ICU stays**, **279 invasive ventilation events**, **4,499 note-available stays**. All values below are from the canonical R2 result, not timing-only bootstrap estimates.

| Level | Features | Structured comparator AUROC | + TF-IDF AUROC | **TF-IDF ΔAUROC** | + embedding AUROC | **Embedding ΔAUROC** |
|---|---:|---:|---:|---:|---:|---:|
| A: 34 structured | 34 | 0.672388 | 0.695276 | **+0.022888** | 0.679921 | **+0.007533** |
| B: + treatment/support | 42 | 0.704065 | 0.711584 | **+0.007519** | 0.709091 | **+0.005026** |
| C: + documentation behavior | 50 | 0.720039 | 0.730860 | **+0.010821** | 0.719673 | **−0.000366** |
| D: registered rich comparator | 57 | 0.724675 | 0.723304 | **−0.001372** | 0.726613 | **+0.001937** |

| Level | Structured comparator AUPRC | TF-IDF ΔAUPRC | Embedding ΔAUPRC |
|---|---:|---:|---:|
| A | 0.063965 | +0.002337 | −0.002395 |
| B | 0.081860 | −0.000840 | −0.002026 |
| C | 0.083550 | −0.001992 | −0.007429 |
| D | 0.081271 | +0.000145 | +0.003196 |

**Point-estimate-only pattern:** Relative to D, the TF-IDF primary-partition apparent gain is larger at thinner comparator A, but it does not decrease monotonically across A→B→C→D (B `+0.007519` and C `+0.010821`). Embedding point estimates are smaller and inconsistent in sign. This table alone establishes neither reliable incremental discrimination nor a statistically significant contrast between A and D.

## All five frozen patient-grouped partitions

Values are **ΔAUROC relative to the level-specific structured comparator**. Array order is `repeat_1` through `repeat_5`, with frozen outer seeds `20260924` through `20260928`.

| Level | TF-IDF ΔAUROC: five partitions | Embedding ΔAUROC: five partitions |
|---|---|---|
| A | `[+0.022888, +0.011974, +0.002839, +0.000678, +0.000146]` | `[+0.007533, +0.007170, +0.011721, +0.009490, −0.001402]` |
| B | `[+0.007519, −0.001936, +0.009733, +0.008674, +0.003106]` | `[+0.005026, +0.003090, +0.002466, +0.007061, −0.002479]` |
| C | `[+0.010821, −0.000949, +0.005109, +0.003487, −0.003476]` | `[−0.000366, −0.001718, +0.006605, +0.000236, −0.003592]` |
| D | `[−0.001372, −0.010196, −0.001193, −0.009024, −0.004568]` | `[+0.001937, −0.010458, −0.010509, −0.009548, −0.003336]` |

The D-level TF-IDF ΔAUROC is negative in all five partitions; the D-level embedding ΔAUROC is negative in four of five. Conversely, the A-level TF-IDF ΔAUROC is positive in all five. These are descriptive within-design direction checks, **not independently sampled study replications**.

For completeness, the five partition-specific **ΔAUPRC** values are:

| Level | TF-IDF ΔAUPRC: five partitions | Embedding ΔAUPRC: five partitions |
|---|---|---|
| A | `[+0.002337, −0.001470, +0.004339, +0.002206, +0.002055]` | `[−0.002395, +0.000629, +0.002396, +0.003955, −0.003416]` |
| B | `[−0.000840, −0.004945, +0.005002, +0.004025, +0.007092]` | `[−0.002026, −0.004366, +0.000705, +0.003131, +0.005267]` |
| C | `[−0.001992, +0.001183, +0.007003, +0.004197, −0.004202]` | `[−0.007429, −0.000344, −0.000578, −0.002608, +0.004571]` |
| D | `[+0.000145, −0.001183, −0.004388, +0.001103, −0.000013]` | `[+0.003196, −0.002286, −0.002717, −0.003263, +0.000599]` |

## Registered 200-valid-refit uncertainty: A and D only

The following are **primary-partition paired source-patient-cluster percentile bootstrap intervals within each comparator level**, with the supervised text and HGB models refit in each of 200 valid replicates, **zero replacements**. The bootstrap **mean** and the frozen original out-of-fold **point estimate** represent different quantities and must not be conflated.

| Level and score | Original ΔAUROC point | Bootstrap mean ΔAUROC | **95% percentile CI for ΔAUROC** |
|---|---:|---:|---:|
| A + TF-IDF | +0.022888 | +0.003558 | **[−0.012831, +0.020596]** |
| A + embedding | +0.007533 | +0.003342 | **[−0.012389, +0.020793]** |
| D + TF-IDF | −0.001372 | −0.000527 | **[−0.014735, +0.014324]** |
| D + embedding | +0.001937 | +0.001561 | **[−0.012622, +0.017966]** |

| Level and score | Original ΔAUPRC point | Bootstrap mean ΔAUPRC | **95% percentile CI for ΔAUPRC** |
|---|---:|---:|---:|
| A + TF-IDF | +0.002337 | +0.000173 | **[−0.010439, +0.009325]** |
| A + embedding | −0.002395 | −0.000592 | **[−0.010777, +0.008419]** |
| D + TF-IDF | +0.000145 | +0.000241 | **[−0.009131, +0.010586]** |
| D + embedding | +0.003196 | +0.000097 | **[−0.011032, +0.008745]** |

All **eight** available ΔAUROC and ΔAUPRC 95% intervals include zero. Neither text representation demonstrates reliable discrimination improvement at A or at D under the registered full-refit percentile interval analysis. The primary TF-IDF A point advantage over D is **descriptive only**. No paired A-minus-D bootstrap contrast or uncertainty was output; do not assert that comparator richness *significantly* attenuates text gain. No fixed 5% alert-budget evaluation was declared in this T1.5 final JSON, so do not infer an operational benefit.

### Methodological QA flag: A + TF-IDF original estimate versus bootstrap distribution

The **original** primary A + TF-IDF ΔAUROC is `+0.022888200`, while the complete-refit bootstrap mean is `+0.003557552` (difference approximately `+0.019331`) and the percentile 95% interval's upper endpoint is `+0.020595897`. Thus, the original point is **above the upper 97.5th-percentile limit** of its bootstrap distribution. A percentile bootstrap confidence interval need not contain the observed estimate, so this discrepancy **does not automatically invalidate the calculation**. However, before using T1.5 for publication-facing inference, audit the bootstrap estimand, sample reweighting, patient-cluster resampling, full-refit/evaluation pipeline alignment, potential bootstrap bias, and reproducibility against the preserved implementation. Do not retroactively change the prespecified statistical method or report a positive finding simply because the original A point is favorable. Audit first and report the result regardless of direction.

## Canonical job chain, timing gate and provenance

- Synthetic-only validation `P12HZ35M`: `validate_extension_t1_decomposition_v2_1`, completed with exit code 0; no clinical data read, no declared artifacts.
- Timing job `Q2X07F24`: `time_extension_t1_decomposition_v2_1_ventilation`, completed with exit code 0, 10/10 valid timing-only patient-cluster refits, zero replacements. Median **561.125335835 seconds** per valid refit projected **77.934074 hours** for 500, **above the registered 72-hour cap**. Therefore the prespecified mechanical rule selected **200 valid final refits**, and timing-only bootstrap performance estimates were discarded. Sole declared safe timing artifact: `outputs/multitask_benchmark/extension_t1_decomposition_timing_v2_1_ventilation.json`, **29,537 bytes**, SHA-256 `757f7099969b60e8802395f4d37e135d04ebaaff6103ae6b124e7a912ce854ef` (retrieved and verified from R2 in the 2026-11-04 continuation).
- **Final job `YG5Z0JK8`**: `evaluate_extension_t1_decomposition_v2_1_ventilation`, manual Telegram approval, canonical `completed`, exit code `0`, **200/200 valid** refits, **0 replacements**, runtime **116,889.714 seconds** (approximately 32.47 hours), fixed machine `pshjl4vf24`, scientific commit `e5772f7a1a40b2368465e1b95e24a04abc98cc2a`, Reader observed final `2026-11-06T08:31:23.009Z`.
- **Only declared safe final JSON**: `outputs/multitask_benchmark/extension_t1_decomposition_v2_1_ventilation.json`, **31,844 bytes**, SHA-256 `3496a9623c499d7e1a485efeb7e1bccac5742435d521c9df7d7ae6da632258de`. RunRelay Reader confirmed the declared path, SHA-256, R2 `shared` state and zero direct-text publication errors. The complete final JSON was retrieved and read directly from R2 on 2026-11-06. Safe share expiry `2026-11-09T08:31:23.925Z`.

All four comparator levels used the same frozen patient population, and the aggregate source hashes in the canonical JSON record the registered structured data, note corpus, embedding cache and split manifests. This Markdown is an **aggregate results and provenance checkpoint**, not a substitute for the canonical JSON. Restricted clinical notes, patient-level outcomes and predictions, local embeddings, identifiers, and credentials remain local and are **not** published in this document.

Primary registration and methodological anchors: `docs/registration/exploratory_extension_protocol_v2_1_2026-10-04.md`; `.runrelay/project.yaml`; `src/178_evaluate_extension_t1_decomposition_v2_1.py`; `scripts/run_extension_t1_decomposition_full_v2_1_ventilation.sh`; RunRelay private control jobs `jobs/P12HZ35M.json`, `jobs/Q2X07F24.json`, and `jobs/YG5Z0JK8.json`.

## Registered continuation and stop rule

The next registered T1.5 work is **renal replacement therapy and MetaVision ICU death** comparator-richness decomposition. Each requires its own named five-partition timing gate and subsequent registered A/D full-refit bootstrap if the corresponding timing run succeeds. The registered exploratory extension explicitly forbids unplanned further analyses after the planned T1.5 freeze absent an independent dataset with genuine bedside narrative and its own protocol. Maintain that stop rule. **No additional RunRelay job is submitted in this bounded documentation checkpoint.**
