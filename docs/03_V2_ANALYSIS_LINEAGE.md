# 03 - Corrected v2/v2.1 analysis lineage

Updated: 2026-10-01

This is the ordered provenance map for the current manuscript-facing analysis. Detailed frozen protocol/result files remain authoritative for exact definitions, settings, counts, seeds, hashes, and interpretation rules.

## Status map

| Stage | Status | Key output |
|---|---|---|
| External code review and integrity audit | Complete | v1 numerical results placed under integrity hold |
| Corrected v2/v2.1 cohort and feature rebuild | Complete | source-compatible adult cohorts, GCS correction, fixed notes |
| Exact patient-grouped CV and context freezes | Complete | frozen downstream analysis inputs |
| OSF preregistration ahxn9 | Complete/public | DOI 10.17605/OSF.IO/AHXN9 |
| Final OSF form import and exact-commit validation | Complete | final registration gate passed |
| H1-H3 primary Open-Jev | Complete | registered primary estimates frozen |
| H4 six-construct | Complete | all three outcomes frozen |
| H5 lexical comparison | Complete | all three outcomes frozen |
| H6 unstripped Open-Jev | Complete | all three outcomes frozen |
| H6 Laya | Complete | all three outcomes frozen |
| H6 DiffusionGemma | In progress | ventilation complete; RRT inference running |
| Remaining H6 sensitivities | Pending | endpoint, timing, note-availability, CareVue |
| H7 shuffled negative control | Pending | registered |
| H8 clinician construct validation | Pending | registered |
| H9 corrected Zigong transport | Pending | registered/frozen protocol |
| Manuscript claim lock | Pending | after H1-H9 freeze |

## 1. Integrity audit and v1 hold

The external review and aggregate integrity audit identified source-system endpoint observability, note-selection artifacts, note-category whitespace and error-flag problems, inconsistent semantic chunk aggregation, an eICU laboratory-window bug, and a Zigong leakage-regex defect.

Affected v1 numerical results are retained as provenance only.

Read:

- docs/external_review_integrity_audit_result_freeze_v1.md
- docs/04_V1_PROVENANCE_AND_HOLD.md

## 2. Corrected v2.1 analysis base

The v2.1 lineage rebuilt the manuscript-facing estimand before reopening performance:

- MetaVision-compatible ventilation and RRT risk sets;
- adult/NICU eligibility;
- corrected airway-coded GCS verbal handling;
- normalized note categories and numeric error flags;
- note selection before language stripping;
- no dbsource predictor;
- frozen rich structured comparator and context;
- exact patient-grouped repeated CV partitions;
- frozen note corpora;
- prespecified endpoint, timing, language, and CareVue sensitivities.

Confirmatory populations are 11,116/279 ventilation, 19,395/314 RRT, and 19,811/214 MetaVision ICU-death rows/cases.

## 3. Registration gate

OSF registration:

- ID: ahxn9
- DOI: 10.17605/OSF.IO/AHXN9
- cited repository commit: 873897e6c934cea3d558b6518ac1e399f9f75387
- manifest SHA-256: 22ac9f815309d81ebf03d279087848e33f8c0a16b563efe8af114a196194fc7d

The final imported OSF-form gate later passed at exact project commit e22b17938101b504fee6579e2a8b52b5d780e760 without reading clinical performance.

After that point the registered real-label analysis opened.

## 4. Registered H1-H3 primary Open-Jev

All three outcomes are complete with 500-valid-replicate patient-cluster refit bootstrap.

Primary delta-AUROC estimates:

- ventilation: -0.00005, 95% interval -0.02173 to +0.01910;
- RRT: -0.00079, 95% interval -0.00323 to +0.00275;
- MetaVision ICU death: -0.00212, 95% interval -0.00802 to +0.00531.

Read docs/results/v2_1_primary_openjev_results.md.

## 5. H4 and H5

H4 six-construct analyses are complete for all three outcomes.

H5 common-logistic representation comparisons are complete. Primary-partition TF-IDF increments are +0.00564 for ventilation, +0.00219 for RRT, and +0.00123 for MetaVision ICU death. Open-Jev increments are negative in all three, and Open-Jev after TF-IDF is also negative in all three primary analyses.

Read:

- docs/results/v2_1_h4_six_construct_results.md
- docs/results/v2_1_h5_lexical_results.md

## 6. H6 unstripped-note sensitivity

Complete for all three outcomes.

Delta-AUROC estimates:

- ventilation: -0.01043;
- RRT: -0.00034;
- MetaVision ICU death: +0.00108.

No outcome shows a consistent positive increment that was hidden by language stripping.

Read docs/results/v2_1_h6_unstripped_results.md.

## 7. H6 Laya alternative instrument

Complete for all three outcomes.

Delta-AUROC estimates:

- ventilation: +0.01031, 95% interval -0.01595 to +0.02519;
- RRT: -0.00079, 95% interval -0.00278 to +0.00302;
- MetaVision ICU death: +0.00141, 95% interval -0.00660 to +0.00728.

Read docs/results/v2_1_h6_laya_results.md.

## 8. H6 DiffusionGemma alternative instrument

Environment validation and exact local model-revision preflight are complete at project commit 097bf046a1c7eceb50d71d75e82e79f3993acb00.

Frozen inference configuration:

- google/diffusiongemma-26B-A4B-it;
- local model revision f7f5b7f5fa82ffc52addd066915886d497f5517b;
- fully offline;
- 977-token chunks;
- 97-token overlap;
- maximum 8 chunks;
- maximum across seven concern constructs and minimum for reassuring stability.

Ventilation inference job 9HN4R7T9 completed 4,499/4,499 notes with zero failures and no label access.

Ventilation evaluation job B7Q2M9RK completed:

- comparator AUROC 0.72468;
- augmented AUROC 0.71657;
- delta AUROC -0.00811;
- 95% refit-bootstrap interval -0.02030 to +0.01445;
- 500/500 valid bootstrap replicates, zero replacements.

RRT inference job D4M8Q2VN completed 7,709/7,709 notes with zero failures, zero label access, and zero max-chunk truncations. Evaluation job F7K3Q9MV completed with comparator AUROC 0.97394, augmented AUROC 0.97310, delta AUROC -0.00083, 95% refit-bootstrap interval -0.00283 to +0.00244, and 500/500 valid bootstrap replicates with zero replacements. Evaluation artifact SHA-256: 179b0e6ea1ab6e4f60eeeb4027ae7c291eec51599597ce7dbcead318e884ef9a.

Current job G8M4Q2VN is running the registered fully local MetaVision ICU-death DiffusionGemma inference. No death-arm outcome result should be inferred until its subsequent evaluation artifact is terminal and read.

Read docs/results/v2_1_h6_diffusiongemma_results.md.

## 9. Remaining registered H6-H9

After the DiffusionGemma three-outcome arm:

1. complete registered H6 endpoint, prospective-timing, note-availability, and CareVue death sensitivities;
2. run H7 patient-shuffled negative control within comparator-risk strata;
3. run H8 blinded multi-rater clinician construct validation;
4. run H9 corrected Zigong external narrative transport;
5. freeze one H1-H9 provenance/result index.

No registered definition should be changed in response to observed performance. Any implementation departure must be documented as a deviation.

## 10. Manuscript claim lock

The manuscript claim remains open.

The corrected evidence increasingly favors a question about the value and limits of interpretable semantic compression rather than a claim of unique incremental predictive information beyond strong structured physiology. That interpretation remains provisional until H6-H9 and the final provenance audit are complete.
