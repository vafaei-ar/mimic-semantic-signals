# Exploratory extension v2.1 — T1.4 unstripped ventilation timing gate

Date: 2026-10-28 (US Eastern)  
Status: **Predeclared timing gate complete; full T1.4 ventilation final not yet run**  
Primary registration: OSF `ahxn9`; exploratory extension: OSF `wmyb2`  
Frozen scientific execution commit: `e5772f7a1a40b2368465e1b95e24a04abc98cc2a`  
Documentation branch: `extension-v2_1`. Do not modify the JAMIA-ready `main`.

## Registered scope and interpretation

T1.4 repeats the supervised **T1.1 TF-IDF / L2-logistic late-fusion** analysis, changing *only* the text corpus to the frozen **full unstripped H6 notes** (`fixed_notes_full_v2_1_local.jsonl`). Structured comparator D, HGB model, patient-grouped cross-fitting, five frozen partitions and bootstrap seed `20260924` are unchanged. Report stripped versus unstripped outcomes as **endpoint/treatment-language sensitivity**, **not** a pure leakage estimate.

The named timing task generates descriptive out-of-fold point estimates on five partitions and runs the first 10 valid, timing-only source-patient-cluster bootstrap refits to apply the prespecified mechanical runtime decision. It does not provide final bootstrap inference; the performance estimates from timing-only bootstrap replicates must be discarded before the full final fit.

## Canonical timing decision — invasive ventilation

| Item | Verified aggregate result |
|---|---:|
| Timing job | `KBCCPKH7` |
| Task | `time_extension_t1_unstripped_v2_1_ventilation` |
| Status / exit | Completed / 0 |
| Execution machine | `pshjl4vf24` |
| Total elapsed execution time | 3,696.615 seconds (about 1 h 1 m 37 s) |
| Valid timing refits / replacements | **10 / 0** |
| Median elapsed seconds per valid bootstrap refit | **237.722964** |
| Mechanical projection for 500 valid refits | **33.017078 hours** |
| Registered runtime cap | **72 hours** |
| **Prespecified final bootstrap target** | **500 valid refits** |
| Bootstrap seed sequence | `20260924` |

The registered rule selects 200 valid replicates *only when* the median of the first 10 valid refit runtimes multiplied by 500 exceeds 72 hours; otherwise it selects 500. Because **33.017078 h is below 72 h**, the proper target is **500**. This decision is based solely on runtime, not observed performance, and is not a promise of final elapsed wall time.

## Timing-run descriptive point estimates — not final inference

| Metric, frozen primary partition `repeat_1` | Value |
|---|---:|
| Comparator D AUROC | 0.724675 |
| D + unstripped supervised TF-IDF AUROC | 0.728449 |
| Descriptive ΔAUROC versus D | **+0.003773** |
| Comparator D AUPRC | 0.081271 |
| D + unstripped supervised TF-IDF AUPRC | 0.089033 |
| Descriptive ΔAUPRC versus D | +0.007763 |
| Standalone unstripped TF-IDF note-available AUROC | 0.643767 |
| Predeclared interpretive standalone AUROC threshold | 0.60 (met for all five partitions) |
| Net events captured at the 5% alert budget, unstripped TF-IDF minus D | −1 |

All five frozen-partition ΔAUROC descriptive point estimates, in order: `[+0.003773, −0.007704, +0.006193, −0.007430, +0.000263]` (range `[−0.007704, +0.006193]`, **three positive and two negative**). Standalone text AUROC across the five partitions ranged `[0.608541, 0.643767]`.

These are **descriptive out-of-fold point estimates**, not a paired stripped-versus-unstripped contrast and not confidence intervals. The final full-refit patient-cluster bootstrap has not run. **Do not infer reliable incremental value, pure leakage, or clinical benefit** from this timing output. The eventual T1.4 endpoint/treatment-language comparison must use the frozen stripped T1.1 benchmark and final unstripped analysis on like-for-like partitions.

## Reproducibility and safe-artifact provenance

- RunRelay Reader canonical status for `KBCCPKH7`: `completed`, exit code `0`, 10/10 timing refits, scientific commit `e5772f7a1a40b2368465e1b95e24a04abc98cc2a`, and exact bound machine `pshjl4vf24`; verified on 2026-10-28.
- The only declared safe aggregate JSON: `outputs/multitask_benchmark/extension_t1_tfidf_unstripped_timing_v2_1_ventilation.json` (**13,891 bytes**, SHA-256 **`d6d77d8b0092b2a7b25dfbe4ca8ee38594fe1d82856be90530f3b1694830cda2`**).
- The **complete R2 direct-text aggregate JSON was retrieved** in this continuation and its reported SHA-256 agreed with the separately declared Reader artifact metadata. R2 share expiry was recorded as `2026-10-31T23:40:14.068Z`. This Markdown is a documentation checkpoint and **not** the original canonical JSON.
- Scientific code: `src/175_evaluate_extension_t1_tfidf_unstripped_v2_1.py` and its T1.1 implementation dependency `src/172_evaluate_extension_t1_tfidf_v2_1.py`.
- Manifest: `.runrelay/project.yaml`; predeclared protocol: `docs/registration/exploratory_extension_protocol_v2_1_2026-10-04.md`.
- No raw notes, patient identifiers, row-level scores, predictions, sensitive clinical records, or credentials are included in this checkpoint.

## Registered next step and safety boundary

The named final task is `evaluate_extension_t1_unstripped_v2_1_ventilation`, which consumes the frozen local timing JSON and writes only `outputs/multitask_benchmark/extension_t1_tfidf_unstripped_v2_1_ventilation.json` as an externally shareable aggregate. The manifest requires **manual Telegram approval** and reserves 4 CPU cores, 24 GB RAM, with a 4,500-minute hard timeout. The timing projection for the full bootstrap is about **33.02 hours**; no final task is initiated by this checkpoint.

Preserve patient isolation, original partitions and seed, the frozen exact scientific commit, the 72-hour runtime rule, and the protected JAMIA-ready `main` branch. Check canonical RunRelay state for a same-purpose active job and obtain approval before submitting any manual final run. Do not chain RRT/death timing jobs within this bounded continuation.
