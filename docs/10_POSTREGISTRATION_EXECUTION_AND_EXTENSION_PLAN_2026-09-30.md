# Post-registration execution and extension plan

Updated: 2026-10-02

This is the authoritative forward plan after OSF registration ahxn9, DOI 10.17605/OSF.IO/AHXN9. It does not modify the frozen registration. Anything not named in the registration is explicitly post-registration exploratory.

## Current checkpoint

Completed registered work:

- H1-H3 primary stripped-note Open-Jev analyses for all three outcomes;
- H4 six-construct analyses for all three outcomes;
- H5 common-logistic lexical comparisons for all three outcomes;
- H6 unstripped-note Open-Jev sensitivity for all three outcomes;
- H6 Laya alternative-instrument sensitivity for all three outcomes;
- H6 DiffusionGemma invasive-ventilation inference/evaluation;
- H6 DiffusionGemma RRT inference/evaluation; delta AUROC -0.00083, 95% refit-bootstrap interval -0.00283 to +0.00244;
- H6 DiffusionGemma MetaVision ICU-death inference/evaluation; delta AUROC +0.00499, 95% refit-bootstrap interval -0.00654 to +0.00652.

DiffusionGemma ventilation result:

- comparator AUROC 0.72468;
- augmented AUROC 0.71657;
- delta AUROC -0.00811;
- 95% refit-bootstrap interval -0.02030 to +0.01445;
- 500/500 valid refit-bootstrap replicates, zero replacements.

Current registered execution:

- Z5G2R8N4 - evaluate_h7_patient_shuffled_v2_1_death_carevue
- exact project commit: 5dfaa30dedd273c453b6205100f199097b2f71ee
- running the final registered H7 patient-shuffled semantic negative control for the separate CareVue ICU-death replication using the same frozen risk-decile, seed, permutation, CareVue fold, HGB, and bootstrap definitions.

The broad endpoint audit R8V4N2M7 froze 11,380 stays, 543 cases, 10,837 unchanged controls, and 4,590 note-available rows. The explicit-intubation endpoint is empirically identical to H1 and requires no separate predictive rerun.

## Track A - finish all registered analyses

### A1. H6 DiffusionGemma complete

The registered three-outcome DiffusionGemma arm is complete:

- ventilation delta AUROC -0.00811, 95% interval -0.02030 to +0.01445;
- RRT -0.00083, -0.00283 to +0.00244;
- MetaVision ICU death +0.00499, -0.00654 to +0.00652.

All three evaluations completed 500/500 valid patient-cluster refit-bootstrap replicates with zero replacements. Do not select a preferred semantic instrument or outcome post hoc based on point estimates.

### A2. Complete remaining H6 sensitivities

Run the registered sensitivities without changing definitions in response to observed performance:

- ventilation explicit-intubation endpoint: aggregate audit confirms it is empirically identical to primary H1, so no separate predictive rerun is needed;
- ventilation broad respiratory-support endpoint: complete; comparator AUROC 0.70385, augmented AUROC 0.69741, delta AUROC -0.00643, 95% refit-bootstrap interval -0.01879 to +0.01046;
- CHARTEVENTS storetime constraint: complete across all three outcomes. Ventilation delta AUROC +0.00668 (95% interval -0.02079 to +0.02286), RRT +0.00053 (-0.00307 to +0.00261), and MetaVision ICU death -0.00207 (-0.00923 to +0.00689);
- 1-hour laboratory lag: complete across all three outcomes. Ventilation delta AUROC +0.00717 (95% interval -0.02333 to +0.01829), RRT +0.00069 (-0.00331 to +0.00331), and MetaVision ICU death +0.00153 (-0.00936 to +0.00618);
- 2-hour laboratory lag: complete across all three outcomes. Ventilation delta AUROC +0.00216 (95% interval -0.02269 to +0.01911), RRT -0.00110 (-0.00294 to +0.00309), and MetaVision ICU death -0.00415 (-0.00849 to +0.00655);
- note-availability/timing sensitivity: complete as an empirical identity sensitivity. Q5V8Z2N7 found 0 missing-storetime rows among 376,185 normalized bedside notes in the registered MetaVision admissions. The deterministic p90 rule froze a 3-hour fallback, but both registered note sensitivities select exactly the primary notes for all three outcomes, so no semantic/predictive rerun is required;
- separate CareVue ICU-death replication/sensitivity: complete. T8Y5Q2N6 reported comparator AUROC 0.93799, augmented AUROC 0.93544, delta AUROC -0.00255, and 95% refit-bootstrap interval -0.00858 to +0.00812, with 500/500 valid replicates and zero replacements. CareVue remains separate and is reported side by side with MetaVision without pooling.

Report MetaVision and CareVue death separately without pooling.

### A3. H7 shuffled negative control

Run the registered patient-shuffled negative control sequentially for ventilation, RRT, MetaVision ICU death, and CareVue ICU death. The frozen implementation assigns note-available patients to ten balanced deciles using mean repeat-1 rich-comparator OOF risk across that patient's note-available rows, then permutes complete eight-score row vectors only between different patients within the same decile using seed 20260929. No-note rows remain unchanged; frozen folds, HGB settings, and the 500-valid-replicate patient-cluster refit bootstrap are reused. Ventilation is complete: comparator AUROC 0.72468, shuffled-augmented AUROC 0.71408, delta AUROC -0.01059, 95% interval -0.02851 to +0.01432, with all five frozen-partition delta-AUROCs negative. RRT is complete: comparator AUROC 0.97394, shuffled-augmented AUROC 0.97369, delta AUROC -0.00024, 95% interval -0.00269 to +0.00313. MetaVision ICU death is complete: comparator AUROC 0.93338, shuffled-augmented AUROC 0.93647, delta AUROC +0.00309, 95% interval -0.00663 to +0.00599. CareVue ICU death is complete: comparator AUROC 0.93799, shuffled-augmented AUROC 0.93087, delta AUROC -0.00712, 95% interval -0.00784 to +0.00882. H7 is complete.

### A4. H8 clinician construct validation

Before rating begins, freeze:

- note sample;
- construct definitions;
- rater instructions;
- rating scale;
- missing/adjudication rules;
- agreement and model-versus-human summaries.

Use blinded multi-rater evaluation. Do not tune the semantic instruments to the human ratings.

### A5. H9 corrected Zigong external validation

Use the frozen 24-hour Zigong narrative transport design.

Only DiffusionGemma is eligible for direct-Chinese outcome scoring under the frozen bilingual semantic gate.

Use the frozen 340-note cohort with 85 cases, 255 controls, and 85 matched sets. Fit the semantic-only logistic pipeline on the full frozen MIMIC ventilation cohort, then apply it unchanged to Zigong.

No Zigong refit, recalibration, threshold selection, coefficient modification, prompt adaptation, or post hoc translation.

Primary metric: AUROC. Secondary AUPRC/Brier are descriptive, with 2,000 matched-set bootstrap replicates.

### A6. Freeze registered evidence

Create one authoritative H1-H9 result/provenance index containing:

- exact project commit;
- RunRelay job ID;
- artifact path and SHA-256;
- cohort/input hashes;
- split hashes;
- model/instrument versions;
- registration/deviation references.

No registered definition should change in response to observed performance. Any implementation departure must be documented as a deviation.

## Track B - post-registration exploratory decision-model extension

This track is not part of OSF registration ahxn9 and begins only after the registered critical path is frozen. The detailed frozen exploratory plan is docs/11_POSTREGISTRATION_DECISION_MODEL_EXTENSION_PLAN_2026-10-01.md.

### Planned local instrument roster and order

1. Clef-Flash 9B - first technical/preflight target because it is the smaller Cloudflare Jev/SystemOne-compatible model.
2. Clef 27B - full-capacity Cloudflare comparison if local hardware feasibility is clean. Do not silently quantize; any quantized variant must be frozen and labeled as a separate exploratory instrument before labels.
3. Nimble 9B - local Jev-style decision instrument through Ollama.
4. Tev1 4B - local Jev-style decision instrument through Ollama.

Clef and Clef-Flash are Apache-2.0 local models that expose a Jev/SystemOne-compatible typed-question interface. Their inclusion is scientifically useful because they provide an independently developed decision architecture while preserving the same eight-construct typed-question concept.

Before any outcome evaluation, every exploratory model must have a label-free frozen integration record covering:

- exact model repository/tag and immutable revision or digest;
- license and local model files;
- runtime/library versions and hardware topology;
- exact eight-construct schema hash;
- local-only execution and safe aggregate reporting;
- deterministic context/chunk/truncation policy;
- deterministic cross-chunk aggregation when chunking is used;
- failure/retry behavior;
- completion rate, score resolution, construct distributions, and cross-instrument agreement diagnostics.

Clef/Clef-Flash accept substantially longer native context than the registered compact instruments. Any native long-context arm or context-matched sensitivity must be specified and frozen before clinical labels are used; context length may not be chosen after observing outcome performance.

After the label-free gate, estimate exploratory clinical increments using the same frozen stripped-note cohorts, patient-grouped splits, rich structured comparator, and downstream estimation framework used for the registered analyses. Compare descriptively with Open-Jev, Laya, DiffusionGemma, and TF-IDF. Do not insert Clef, Clef-Flash, Nimble, or Tev1 into registered H6.

### Hosted Jev governance gate

The vendor enabled Zero Data Retention for the organization on 2026-10-01 and stated that only operational telemetry is retained under ZDR.

Vendor-side retention clarification is therefore no longer pending.

A separate institutional/data-use gate remains unresolved. ZDR does not by itself establish that credentialed MIMIC note text may be transmitted to the hosted service.

Do not add hosted clinical-note inference unless the applicable institutional/data-governance review is complete and the exact hosted configuration is frozen. If later permitted, hosted Jev remains post-registration exploratory and the integration should first be validated on nonrestricted material.

### OPUS synthetic work

Retain the existing OPUS workstream as supplementary synthetic construct-validity testing. It does not replace H8 human validation or H9 external clinical transport and must remain separate from registered MIMIC analyses.

## Track C - practical compression and manuscript synthesis

After the registered analyses are frozen, quantify the representation tradeoff across:

- dimensionality;
- discrimination and calibration;
- decision-curve changes;
- inference runtime and hardware needs;
- score stability;
- clinician construct agreement;
- cross-site/language transport;
- interpretability and auditability.

Then:

1. generate registered H1-H9 manuscript tables/figures from aggregate artifacts;
2. place Clef, Clef-Flash, Nimble, Tev1, any future hosted-Jev work, and OPUS in a clearly separate exploratory section;
3. audit every manuscript number back to exact code/job/artifact provenance;
4. choose the final claim from the corrected evidence rather than the original hypothesis;
5. prepare the journal submission package.

## Current manuscript framing

The corrected primary Open-Jev effects are near zero. H5 shows small positive TF-IDF increments and negative Open-Jev increments within a common logistic family. Unstripped-note and completed alternative-instrument H6 results have not established a consistent positive semantic increment.

The manuscript should therefore remain open to a limits/tradeoff framing: low-dimensional semantic measurements may be valuable for interpretability and compression even when predictive efficiency is lower than high-dimensional lexical text and incremental discrimination over strong structured physiology is limited.

H8 human construct validity and H9 external transport are essential to determining whether that framing is strong enough.

## Execution rules

- Keep frozen registration files unchanged.
- Validate new code/tasks on an exact commit before execution.
- Keep long scientific RunRelay jobs sequential on this project runner.
- Keep row-level restricted research data local and share only declared aggregate artifacts.
- Mark every analysis not in the frozen registration as exploratory in code, documentation, artifacts, tables, and manuscript text.
- Do not use documentation commits to silently change the exact code commit of an active scientific job.

## Immediate continuation point

H7 is frozen. Continue to H8 by freezing the random-note sample and complete clinician-rating/analysis contract before any ratings are collected. Human annotation remains gated on the Penn State IRB determination and applicable PhysioNet credential/DUA requirements.
