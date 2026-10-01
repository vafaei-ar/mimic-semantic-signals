# Post-registration execution and extension plan

Updated: 2026-09-30

This is the forward plan after OSF registration `ahxn9` (DOI `10.17605/OSF.IO/AHXN9`). It does not modify the frozen registration. Anything not named in the OSF registration is explicitly post-registration exploratory work.

## Current checkpoint

Registered H1-H3 primary Open-Jev analyses, H4 six-construct analyses, and H5 lexical comparisons are complete for all three outcomes.

H6 unstripped-note sensitivity is complete for invasive ventilation and RRT. MetaVision ICU-death evaluation job `T4N7R9V2` is the current running step.

## Track A: finish all registered analyses

1. Finish and freeze the three-outcome H6 unstripped-note results.
2. Run H6 with the registered alternative semantic instruments:
   - Laya;
   - DiffusionGemma.
   Use the same frozen cohorts, comparator features, patient-grouped splits, note identities, and downstream estimands.
3. Run the prespecified ventilation endpoint sensitivities:
   - explicit-intubation evidence;
   - broad respiratory-support evidence.
4. Run the prespecified prospective-timing sensitivities:
   - CHARTEVENTS storetime constraint;
   - 1-hour laboratory lag;
   - 2-hour laboratory lag;
   - note-availability sensitivity.
5. Run the separate CareVue ICU-death replication and report it beside MetaVision without pooling.
6. Run H7, the registered comparator-risk-decile patient-shuffled negative control.
7. Run H8 blinded clinician construct validation after freezing the note sample, rater instructions, rating scales, adjudication/missing rules, and agreement summaries.
8. Run H9 corrected Zigong external validation using the registered translated-English and native-Chinese arms.
9. Freeze one authoritative H1-H9 result index containing exact commits, RunRelay job IDs, artifact hashes, cohort hashes, split hashes, and model/instrument versions.

No registered definition should be changed in response to observed performance. Any implementation departure must be documented as a deviation.

## Track B: post-registration exploratory decision-model extension

This track is not part of OSF registration `ahxn9`.

### Nimble 9B and Tev1 4B

Add two local Jev-style decision instruments through Ollama:

- Nimble 9B;
- Tev1 4B.

Before inference, freeze:

- Ollama version;
- exact model tag and immutable model digest;
- the existing eight-construct question/response schema;
- deterministic chunking and cross-chunk aggregation;
- failure/retry behavior;
- local-only inference and safe aggregate reporting.

The preferred exploratory comparison uses the same frozen stripped-note corpus and the same rich-comparator/frozen-split downstream framework as H1-H3. The registered Open-Jev 220-token chunks, 40-token overlap, and maximum-eight-chunk rule are the default reference unless a pre-inference tokenizer/runtime audit requires a documented model-specific change.

First run label-free completion, score-resolution, chunk-coverage, and cross-instrument agreement diagnostics. Then estimate clinical increments using the frozen cohorts and folds. Compare these results descriptively with Open-Jev, Laya, DiffusionGemma, and TF-IDF.

### Hosted Jev governance gate

Hosted Jev remains outside the registered analysis and outside the current restricted-data execution path.

A vendor clarification request about Zero Data Retention and retained telemetry is pending. Do not add hosted clinical-note inference unless the required institutional/data-governance review is complete and the exact hosted configuration is frozen. If a hosted comparison later becomes permissible, label it post-registration exploratory and first validate the integration on nonrestricted material.

### OPUS synthetic work

Retain the existing OPUS workstream as supplementary synthetic construct-validity testing. It does not replace external clinical validation and must remain separate from registered MIMIC analyses.

## Track C: practical compression and manuscript synthesis

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

A second external narrative cohort can be added later if a suitable dataset and governance path become available. It is additional validation, not a substitute for registered Zigong.

## Execution rules

- Keep frozen registration files unchanged.
- Validate new code/tasks on an exact commit before execution.
- Keep long scientific RunRelay jobs sequential on this project runner.
- Keep row-level restricted research data local and share only declared aggregate artifacts.
- Mark every analysis not in the frozen registration as exploratory in code, documentation, artifacts, tables, and manuscript text.

## Immediate continuation point

Wait for `T4N7R9V2` to become terminal and inspect its canonical artifact. If clean, continue with the remaining registered H6 sensitivity program, beginning with the alternative semantic-instrument implementation/validation path.
