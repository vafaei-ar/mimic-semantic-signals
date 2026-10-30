# Exploratory extension v2.1 — T1.4 unstripped TF-IDF ventilation final checkpoint

Date: 2026-10-30 (US Eastern)  
Status: **Final invasive-ventilation T1.4 endpoint/treatment-language sensitivity completed; post-registration exploratory**  
Primary registration: OSF `ahxn9`; exploratory extension OSF project: `wmyb2`  
**Exact scientific execution commit:** `e5772f7a1a40b2368465e1b95e24a04abc98cc2a`  
Documentation branch: `extension-v2_1`. Preserve the separate JAMIA-ready `main` branch.

## Frozen design

The registered T1.4 sensitivity repeats the T1.1 supervised TF-IDF/L2-logistic scalar late-fusion analysis, substituting the frozen **full, unstripped H6 note corpus** (`fixed_notes_full_v2_1_local.jsonl`) for the stripped primary note corpus. Vocabulary and text-score fitting occur within the appropriate training partitions; patient-grouped inner cross-fitting, rich structured HGB comparator D, five frozen patient-grouped outer partitions, primary `repeat_1`, seed `20260924`, source-patient-cluster full-refit bootstrap, and 5% fixed alert-budget secondary analysis are retained. The implementation records a same-patient inner-fold guard and re-fits the complete text model and both HGB models for each valid bootstrap replicate.

**Estimand:** primary-partition out-of-fold `ΔAUROC = AUROC(D + unstripped supervised TF-IDF score) − AUROC(D)`. Its registered uncertainty estimate uses a two-sided 95% percentile interval from **500 valid full-refit patient-cluster bootstrap replicates**. The registered T1.4 comparison against stripped T1.1 is an **endpoint/treatment-language sensitivity**, *not* a pure leakage effect. The arm-specific bootstrap intervals below do not provide a paired confidence interval for the stripped-versus-unstripped contrast.

## Verified final unstripped ventilation results

| Quantity | Canonical R2 result |
|---|---:|
| Stays / outcome events / note-available stays | 11,116 / 279 / 4,499 |
| Comparator D AUROC | 0.724675486 |
| D + unstripped TF-IDF AUROC | 0.728448568 |
| **Primary ΔAUROC versus D** | **+0.003773082** |
| **Bootstrap mean ΔAUROC** (distinct from primary point estimate) | −0.000349443 |
| **Two-sided 95% full-refit bootstrap CI for ΔAUROC** | **[−0.016243006, +0.014624541]** |
| Comparator D AUPRC | 0.081270532 |
| D + unstripped TF-IDF AUPRC | 0.089033279 |
| Primary ΔAUPRC | +0.007762747 |
| Full-refit bootstrap mean ΔAUPRC | +0.000217591 |
| Two-sided 95% full-refit bootstrap CI for ΔAUPRC | [−0.009838884, +0.010229971] |
| Standalone TF-IDF note-available AUROC (4,499 stays, 135 events) | 0.643767186 |
| Full-refit patient-cluster valid replicates / replacements | **500 / 0** |

The five frozen-partition ΔAUROC point estimates are `[+0.003773082, −0.007703927, +0.006192776, −0.007430074, +0.000262938]`, range `[−0.007703927, +0.006192776]` (three positive, two negative). Standalone note-available TF-IDF AUROC ranges `[0.608541, 0.643767]` and exceeds the preregistered **interpretive** 0.60 threshold in all five partitions. Comparator D regeneration matched the frozen comparator with maximum absolute prediction difference `9.974659986866641e−17`.

At the prespecified fixed 5% alert budget (556 alerts per model), the unstripped augmented model captured **one fewer** ventilation event than D in the primary partition. The full-refit mean net-event contrast per 1,000 stays was `+0.012480`, 95% interval `[−1.075663, +1.083303]`. These secondary numbers do **not** establish benefit or harm.

**Interpretation:** The two-sided 95% intervals for ΔAUROC, ΔAUPRC and fixed-budget net events all cross zero. There is **no demonstrated reliable incremental discrimination or clinical gain over rich D** from unstripped TF-IDF for ventilation. Do not assert equivalence, absence of usable text information, or clinically meaningful benefit from a positive primary point estimate.

## Registered T1.4 stripped-versus-unstripped comparison: descriptive only

The separate frozen **T1.1 stripped-note** three-outcome result checkpoint (`docs/results/v2_1_extension_t1_1_tfidf_three_outcome_freeze_2026-10-13.md`) reports the ventilation primary-partition Comparator D AUROC `0.72468`, augmented AUROC `0.72330`, rounded ΔAUROC `−0.00137`, standalone note-available text AUROC `0.64023`, and 95% full-refit ΔAUROC CI `[−0.01493, +0.01468]`. This T1.1 checkpoint is based on a previously verified result and was **not rederived from the original stripped-note R2 JSON in the present continuation**. RunRelay Reader did not retrieve the older stripped-note job `R8M4K2V7` on 2026-10-30.

| Primary-partition ventilation measure | Frozen stripped T1.1 (previously documented, rounded) | Unstripped T1.4 (verified R2) |
|---|---:|---:|
| Comparator D AUROC | 0.72468 | 0.724675 |
| Augmented AUROC | 0.72330 | 0.728449 |
| ΔAUROC relative to D | −0.00137 | +0.003773 |
| 95% full-refit ΔAUROC CI | [−0.01493, +0.01468] | [−0.01624, +0.01462] |
| Note-available standalone TF-IDF AUROC | 0.64023 | 0.643767 |

The **descriptive difference of arm-specific primary ΔAUROC point estimates** (unstripped minus stripped) is **approximately +0.00514**, using rounded T1.1 values. This is not a prespecified *paired* full-refit estimate or CI for the difference. The arm-specific intervals crossing zero do not independently establish that unstripping changes incremental discrimination. Do not label this difference pure outcome leakage. A full T1.4 scientific interpretation should retain the registered wording **endpoint/treatment-language sensitivity** and disclose the stripped-arm provenance limitation.

## Runtime gate, job identity and safe-artifact provenance

- Synthetic-only validation: prior dispatch `Q1E86E6G` failed before execution from an expired one-time dispatch authorization after GitHub Actions queueing; its proper lineage retry `XBWBSA62` passed with exit 0 (`{"t1_4_self_test":"passed"}`) at the frozen exact scientific commit.
- Mechanical 10-replicate timing task `KBCCPKH7`: completed, exit 0, **10/10 valid**, zero replacements, median **237.722964** seconds per valid refit, projected **33.017078 hours** for 500. The registered **72-hour cap** mechanically selected **500 valid full refits** rather than 200. The timing-run bootstrap performance estimates were discarded. Canonical timing JSON: `outputs/multitask_benchmark/extension_t1_tfidf_unstripped_timing_v2_1_ventilation.json`, SHA-256 `d6d77d8b0092b2a7b25dfbe4ca8ee38594fe1d82856be90530f3b1694830cda2`.
- **Final T1.4 unstripped ventilation job:** `89Y0XG9A`; named task `evaluate_extension_t1_unstripped_v2_1_ventilation`, manual Telegram approval, scientific commit `e5772f7a1a40b2368465e1b95e24a04abc98cc2a`, fixed machine `pshjl4vf24`; **completed with exit code 0**, runtime **122,995.801 seconds** (about 34 h 10 min), 500/500 valid bootstrap replicates and zero replacements; canonical Reader observed final status at `2026-10-30T11:01:59.624Z`.
- **Only declared final safe aggregate JSON:** `outputs/multitask_benchmark/extension_t1_tfidf_unstripped_v2_1_ventilation.json` (**15,317 bytes**, SHA-256 **`c0b047c5fb0d694d04751cf1f3a764bb0aa77bc301684f1b43563ed792e4cd93`**). Reader confirmed one safe aggregate, none skipped, no direct-text publication errors. Its complete contents were read from R2 on 2026-10-30, and the Reader's direct-text SHA matched declared artifact metadata. R2 share expiry: `2026-11-02T11:02:00.867Z`.
- This Markdown is an independently reviewable **aggregate/provenance checkpoint**, not a replacement for the canonical JSON. Row-level predictions, note texts, source-patient identifiers, private embeddings, and restricted clinical records remain local and are not included.

## Frozen next boundary

The prespecified T1.4 **RRT and ICU-death** timing and final runs remain outstanding, followed by preregistered T1.5 comparator-richness decomposition. Do not invent an outcome, alter comparator D or model parameters, or treat the descriptive stripped-versus-unstripped arm difference as a formal statistical test. Preserve the protected JAMIA-ready `main` branch. No subsequent scientific RunRelay job is created as part of this documentation checkpoint.

**Source anchors:** exact scientific code `src/175_evaluate_extension_t1_tfidf_unstripped_v2_1.py` and `src/172_evaluate_extension_t1_tfidf_v2_1.py`; manifest `.runrelay/project.yaml`; protocol `docs/registration/exploratory_extension_protocol_v2_1_2026-10-04.md`; T1.1 stripped checkpoint above; canonical RunRelay Reader + R2 direct-text artifact for `89Y0XG9A`.
