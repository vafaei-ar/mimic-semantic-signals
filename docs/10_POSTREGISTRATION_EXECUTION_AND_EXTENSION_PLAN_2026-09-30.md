# Post-registration execution and extension plan

Updated: 2026-10-01

This is the authoritative forward plan after OSF registration ahxn9, DOI 10.17605/OSF.IO/AHXN9. It does not modify the frozen registration. Anything not named in the registration is explicitly post-registration exploratory.

## Current checkpoint

Completed registered work:

- H1-H3 primary stripped-note Open-Jev analyses for all three outcomes;
- H4 six-construct analyses for all three outcomes;
- H5 common-logistic lexical comparisons for all three outcomes;
- H6 unstripped-note Open-Jev sensitivity for all three outcomes;
- H6 Laya alternative-instrument sensitivity for all three outcomes;
- H6 DiffusionGemma invasive-ventilation inference/evaluation;
- H6 DiffusionGemma RRT inference, 7,709/7,709 notes with zero failures and zero label access.

DiffusionGemma ventilation result:

- comparator AUROC 0.72468;
- augmented AUROC 0.71657;
- delta AUROC -0.00811;
- 95% refit-bootstrap interval -0.02030 to +0.01445;
- 500/500 valid refit-bootstrap replicates, zero replacements.

Current registered execution:

- F7K3Q9MV - evaluate_h6_diffusiongemma_v2_1_rrt
- exact scientific commit: 097bf046a1c7eceb50d71d75e82e79f3993acb00
- frozen rich-comparator HGB procedure with 500 patient-cluster refit-bootstrap replicates; aggregate result only.

Documentation-only commits made while this job runs do not alter its exact-commit execution.

## Track A - finish all registered analyses

### A1. Complete H6 DiffusionGemma

1. RRT inference is complete and clean.
2. Finish the running RRT evaluation using the frozen rich-comparator HGB procedure and 500 patient-cluster refit-bootstrap replicates.
3. Run MetaVision ICU-death DiffusionGemma inference.
4. If inference is clean, run MetaVision ICU-death evaluation.
5. Freeze the three-outcome DiffusionGemma H6 result document.

Do not select a preferred semantic instrument post hoc based on point estimates.

### A2. Complete remaining H6 sensitivities

Run the registered sensitivities without changing definitions in response to observed performance:

- ventilation explicit-intubation endpoint;
- ventilation broad respiratory-support endpoint;
- CHARTEVENTS storetime constraint;
- 1-hour laboratory lag;
- 2-hour laboratory lag;
- note-availability/timing sensitivity;
- separate CareVue ICU-death replication/sensitivity.

Report MetaVision and CareVue death separately without pooling.

### A3. H7 shuffled negative control

Run the registered patient-shuffled negative control within comparator-risk strata using the frozen definitions and aggregate-only reporting.

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

This track is not part of OSF registration ahxn9 and begins only after the registered critical path is frozen.

### Nimble 9B and Tev1 4B

Add two local Jev-style decision instruments through Ollama:

- Nimble 9B;
- Tev1 4B.

Before clinical inference, freeze:

- Ollama version;
- exact model tag and immutable digest;
- the eight-construct question/response schema;
- deterministic chunking and cross-chunk aggregation;
- failure/retry behavior;
- local-only inference and safe aggregate reporting.

First run label-free completion, score-resolution, chunk-coverage, and cross-instrument agreement diagnostics. Then estimate clinical increments using the frozen cohorts, splits, and rich comparator.

Compare descriptively with Open-Jev, Laya, DiffusionGemma, and TF-IDF. Do not insert these exploratory models into registered H6.

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
2. place Nimble, Tev1, any future hosted-Jev work, and OPUS in a clearly separate exploratory section;
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

Wait for F7K3Q9MV to become terminal and inspect its canonical declared aggregate artifact. If clean, freeze the RRT DiffusionGemma result and continue sequentially to MetaVision ICU-death DiffusionGemma inference/evaluation before moving to the remaining H6 sensitivities.
