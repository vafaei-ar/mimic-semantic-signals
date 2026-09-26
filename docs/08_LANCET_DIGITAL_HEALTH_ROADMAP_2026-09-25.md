# Lancet Digital Health roadmap — current checkpoint

Updated: 2026-09-26

## Current position

The project has moved from exploratory v1 analyses through integrity review, v2/v2.1 redesign, and external OSF submission. No v2.1 real-label predictive performance has been opened.

OSF submission:

- registration: `ahxn9`, Secondary Data Preregistration;
- submitted: 2026-09-25 15:53 America/New_York;
- cited repository commit: `873897e6c934cea3d558b6518ac1e399f9f75387`;
- manifest SHA-256: `22ac9f815309d81ebf03d279087848e33f8c0a16b563efe8af114a196194fc7d`;
- current repository status: pending approval;
- DOI: pending/not yet recorded.

Post-submission synthetic/static lock validation:

- `V4N8Q2R7 — Validate Post-OSF Locks`;
- exact commit `296e082e8ee9b01211fa50b1be2f026edcb31bdf`;
- completed, exit 0;
- no real clinical data read;
- no real outcome performance computed;
- artifact SHA-256 `4860c207938e332eab8385ab3084d7cc5fe34f957e9db40a857920ef7d680ae6`.

The repository remains fail-closed until OSF approval, DOI recording, OSF-hosted attachment hash verification, verbatim submitted-form import/verification, and exact-commit validation.

The detailed readiness record is `docs/07_PREREGISTRATION_READINESS_2026-09-25.md`.

## What we did and why

### 1. Exploratory v1: establish whether prospective notes contain useful deterioration signal

We started with vasopressor initiation and then expanded to invasive ventilation, RRT, and ICU death. Open-Jev, Laya, and DiffusionGemma were treated as semantic measurement instruments producing a small set of interpretable scores.

The exploratory work showed that narrative text contains prospective signal for some outcomes and that the incremental value is strongly outcome dependent. RRT repeatedly behaved as a useful negative case because structured renal physiology was already highly informative.

A critical finding was that high-dimensional lexical TF-IDF was often stronger than the eight semantic scores. This changed the scientific framing from “semantic models discover unique predictive information” to a more defensible question: whether low-dimensional, clinically interpretable semantic measurements provide useful compression of narrative information.

These v1 numerical performance estimates are now provenance only, not manuscript-facing evidence.

### 2. Integrity review: test whether the original results survived code and cohort scrutiny

An external review identified serious vulnerabilities. Local aggregate audits confirmed several of them, including source-system outcome observability, note-category whitespace and error-flag handling, inconsistent semantic chunk aggregation, an eICU laboratory-window bug, and an invalid Zigong leakage regex.

We therefore placed v1 under an integrity hold rather than patching around the results.

### 3. v2/v2.1 redesign: rebuild the estimand before rerunning prediction

The corrected lineage uses a fixed 12-hour ICU landmark and complete 12-hour outcome ascertainment. Major corrections include:

- source-compatible primary populations;
- adult eligibility and NICU exclusion;
- corrected ETT/tracheostomy handling in GCS verbal;
- normalized note categories and error flags;
- note selection before language stripping;
- no `dbsource` predictor;
- consistent stored max/min semantic aggregation;
- a stronger 34-feature structured physiology/laboratory/urine comparator;
- frozen treatment/documentation context features;
- fixed note corpora;
- exact patient-grouped split files and hashes;
- prespecified ventilation endpoint, language, timing, and treatment-context sensitivities.

The confirmatory primary populations are now MetaVision-only:

| Outcome | Rows | Cases |
| --- | ---: | ---: |
| Invasive ventilation | 11,116 | 279 |
| RRT | 19,395 | 314 |
| ICU death | 19,811 | 214 |

CareVue ICU death is retained as a separate prespecified replication/sensitivity: 25,632 rows and 306 cases.

### 4. Preregistration-first inference: stop seeing performance while design choices remain open

Before any corrected performance was opened, we audited source-system recoverability, treatment/documentation context, fixed-note identity, power/precision, and inference feasibility.

An initial runtime benchmark made the full refit bootstrap appear computationally unrealistic, but a preregistration-safe audit identified OpenMP/BLAS thread oversubscription as the cause. With the explicit four-thread contract, an exact five-fold synthetic refit replicate completed in about 11.21 seconds and the refit-bootstrap plan was restored before registration.

The operative registered confirmatory plan uses:

- repeat-1 out-of-fold delta-AUROC as the primary estimand;
- 500 patient-cluster **refit-bootstrap** replicates of the full repeat-1 five-fold cross-fitting procedure;
- repeats 2-5 as separate refit/fold-partition stability analyses;
- a fixed four-thread HGB/OpenMP/BLAS execution contract;
- no confirmatory p-values;
- no Holm testing;
- no binary success/failure rule based only on whether an interval crosses zero.

This is an estimation-first design.

## What we have learned so far

The strongest conclusions currently supported by the whole project, without promoting invalidated v1 numbers, are:

1. Prospective ICU narrative documentation contains predictive information, but its value is outcome dependent.
2. High-dimensional lexical text can capture more predictive signal than eight compact semantic scores.
3. The scientific value of the semantic representation therefore depends on compression, interpretability, stability, transport, and human construct validity, not on winning a model leaderboard.
4. Documentation process and source-system artifacts can create large apparent gains if the cohort and comparator are not designed carefully.
5. External transport evidence from the v1 lineage is not yet sufficient for a strong portability claim because affected eICU and Zigong analyses require corrected reruns.
6. The corrected v2.1 confirmatory analysis has not yet produced real-label performance. This is deliberate and protects the remaining analysis from further result-driven design changes.

## Lancet Digital Health path

The immediate next step is **not a real-label prediction job**. The OSF approval and verification gate must close first.

The ordered plan is:

1. Wait for OSF registration `ahxn9` approval and record its DOI.
2. Re-download the three OSF-hosted registration files and verify their SHA-256 values.
3. Import and verify the submitted OSF form text verbatim, then validate the exact resulting commit.
4. Execute the frozen v2.1 structured-only analyses one outcome at a time under the four-thread contract.
5. Run semantic and TF-IDF analyses on the identical frozen splits and fixed-note corpora.
6. Run the prespecified endpoint, treatment-language, timing, and treatment-context sensitivities.
7. Perform blinded multi-rater clinician construct validation of the eight semantic constructs.
8. Run the separate OPUS synthetic construct-validity/stress-test workstream after freezing its own public-data protocol.
9. Correct and repeat affected external clinical validation analyses, and add a second external narrative cohort if feasible.
10. Quantify the practical value of compression: dimensionality, compute, stability, interpretability, and transport.
11. Lock the manuscript claim only after these results are known.

### New complementary synthetic construct-validity workstream

The public synthetic OPUS doctor-patient conversation dataset is being considered as a controlled stress-test corpus for the frozen eight semantic constructs. Its role is to test discriminant validity and directional response to prespecified clinical-state perturbations.

This workstream is **not** part of the registered v2.1 MIMIC confirmatory analysis, is **not** external clinical validation, and has generated no Medical JEV results yet. It must not be used for fine-tuning the frozen instruments in this validation role.

See `docs/09_OPUS_SYNTHETIC_CONSTRUCT_VALIDITY_PLAN_2026-09-26.md`.

## Decision rule for the paper narrative

The manuscript should follow the corrected evidence rather than protect the original hypothesis.

If compact semantic scores retain meaningful incremental information beyond strong nonlinear structured/context comparators and show clinician validity and transport, the paper can support a broader claim about interpretable narrative measurements.

If semantic increments are small or disappear while TF-IDF remains strong, the paper should pivot to **interpretable low-dimensional compression of lexical clinical signal**, with explicit limits on predictive efficiency.

A Lancet Digital Health submission remains an aspirational target, but the key remaining requirements are human construct validity, corrected external transport, and a clear demonstration that compression provides value beyond simply reducing AUROC.

## Authoritative files

Read in this order:

1. `docs/07_PREREGISTRATION_READINESS_2026-09-25.md`
2. `docs/06_POSTREVIEW_V2_1_CORRECTIONS.md`
3. `docs/03_V2_ANALYSIS_LINEAGE.md`
4. `docs/04_V1_PROVENANCE_AND_HOLD.md`
5. `docs/05_EXTERNAL_VALIDATION_STATUS.md`

Detailed protocol, freeze, contract, and artifact-hash documents remain authoritative when they contain more specific definitions than this synthesis.
