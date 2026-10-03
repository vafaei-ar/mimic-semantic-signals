# 12 - Minimal path to submission

Updated: 2026-10-03

This document supersedes the earlier 2026-10-03 missingness-resilience and new-model publication-sprint plan for Paper 1.

The governing constraint is now explicit: this is a single-author, unfunded study with no resources for independent clinician annotation, paid validation, or a broad new-model program. The goal is the shortest credible path to submission without adding new scientific scope.

This plan does not modify the frozen OSF registration. Registered analyses already completed remain preserved. Deviations are documented separately.

## Paper 1 scope

Paper 1 is a preregistered evaluation of whether eight low-dimensional LLM-derived semantic scores from prospectively available ICU bedside notes improve deterioration discrimination beyond a strong structured EHR comparator.

The corrected evidence is predominantly null:

- H1-H3 Open-Jev increments are near zero;
- H6 instrument, timing, endpoint, and source sensitivities do not overturn that result;
- H7 patient-shuffled controls do not show a reproducible positive increment;
- H5 shows small positive TF-IDF increments and negative Open-Jev increments within the common logistic family.

The paper will explain why earlier exploratory v1 estimates were more optimistic and will emphasize the integrity-audit/correction process.

## Registered deviations before submission

Two dated deviation records are required and are now part of the repository:

- `docs/registration/deviation_h8_not_performed_2026-10-03.md`
- `docs/registration/deviation_h9_partial_execution_2026-10-03.md`

H8 is not performed. No clinician construct-validity claim is allowed.

The existing Zigong result is a post-registration modified DiffusionGemma-only transport analysis using the legacy frozen 24-hour cohort. The registered translated arm was not performed. Zigong is not part of the central evidentiary claim.

## Only remaining computational work

### A. Label-free semantic alignment audit

Before a null semantic increment is treated as scientifically interpretable, perform one label-free audit on the three primary MetaVision cohorts.

Among note-available rows, report:

- association of `hemodynamic_concern` with `treat_vasoactive_any`;
- association of `respiratory_concern` with `treat_niv_any_6h`, `treat_high_flow_any_6h`, and `treat_fio2_last_6h`;
- association of `reassuring_stability` with the same hemodynamic/respiratory state variables;
- correlation between chunks evaluated and note length;
- the construct-state associations after a deterministic between-patient shuffle of complete semantic score vectors.

The alignment audit must not read outcome labels.

Interpretation rule: real construct-state associations should show the clinically expected direction and should materially exceed the shuffled references. If they do not, stop manuscript interpretation of the null and investigate alignment/inference provenance before any further analysis.

### B. Semantic-only discrimination, exploratory

As a separate post-registration exploratory analysis, evaluate the eight Open-Jev scores alone among note-available rows only.

Use the frozen patient-grouped partitions and the same HGB specification. Report AUROC/AUPRC across the five frozen repeats. Do not bootstrap.

Purpose: distinguish semantic scores that contain prognostic information but are redundant with structured EHR state from semantic scores that carry little outcome discrimination on their own.

### C. Comparator decomposition, exploratory

Using the full frozen primary cohorts, frozen patient-grouped partitions, and the same HGB specification, fit four nested comparator levels:

- A: the frozen 34-feature physiology/laboratory/urine block only;
- B: A plus treatment/support context and death-only code status;
- C: B plus documentation-behavior features;
- D: C plus ordinary note context, the registered rich comparator.

At each level report:

- comparator AUROC/AUPRC;
- comparator + Open-Jev AUROC/AUPRC;
- Open-Jev delta AUROC/AUPRC;
- results for all five frozen partitions.

Do not run a new 500-replicate bootstrap.

The level-A augmented model necessarily exposes semantic availability through missing semantic values on no-note rows; this is part of the descriptive decomposition and must be acknowledged when interpreting attenuation across levels.

Do not mix the HGB decomposition numerically with TF-IDF estimates from a different learner family as if they were directly comparable. Retain H5 as the representation comparison within a common L2-logistic family.

## Optional work

A short quantitative v1 attribution sequence may be run only if it can reuse existing artifacts/code with negligible delay. Otherwise explain qualitatively how the integrity review changed source restrictions, note selection, semantic aggregation, and comparator strength.

No optional analysis should delay writing.

## Explicitly cut from Paper 1

Do not run before initial submission:

- structured-data missingness-resilience experiments;
- Clef, Clef-Flash, Nimble, Tev1, hosted Jev, or any other new decision-model panel;
- OPUS synthetic construct-validity work;
- a Zigong cohort rebuild;
- the registered translated Zigong arm;
- synthetic substitutes for H8 clinicians;
- new datasets or external cohorts;
- eICU/NWICU reruns;
- semantic trajectories;
- broad equity extensions;
- rebuilt vasopressor analyses;
- a new supervised encoder;
- any additional sensitivity not directly required by a concrete integrity problem.

These are revision, future-study, or Paper 2 candidates.

## Provenance and registration audit

Before manuscript lock:

1. create one provenance index for every manuscript-facing number with exact code commit, job, artifact path/hash, cohort/input hashes, and registered/exploratory/deviation status;
2. preserve the v1 integrity-review history;
3. retain the completed OSF scientific-text comparison in `docs/registration/osf_attachment_text_verification_2026-10-03.md`; the frozen OSF PDFs match the exact registered-source word sequence after formatting-only normalization.

The byte mismatch is already verified in `docs/registration/osf_attachment_verification_2026-09-28.md`: the OSF-hosted PDF hashes differ from the earlier local package hashes while the manifest is byte-identical. What remains is a text-level extraction/diff to substantiate the existing statement that visible scientific content matches.

## Manuscript framing

The central claim should be narrow:

> In preregistered corrected MIMIC-III analyses, eight low-dimensional semantic scores derived from prospectively available bedside notes did not consistently improve short-horizon deterioration discrimination beyond a strong structured EHR comparator.

The paper may additionally show, if supported by the remaining exploratory analyses, whether the semantic scores carry standalone prognostic information and whether their apparent value attenuates as treatment, documentation behavior, and note context are added to the comparator.

Do not call the semantic representation clinically interpretable because H8 human construct validation was not performed.

## Core figure

Primary figure: delta AUROC with uncertainty for the registered H1-H3 analyses, principal H6 semantic-instrument/source sensitivities, and H7 shuffled controls.

Comparator decomposition and semantic-only results should be secondary/exploratory figures or panels.

## Limitations that must be explicit

- single-center MIMIC-III data from an older care era;
- MetaVision-only confirmatory populations;
- no human construct validation;
- registered external transport not completed as planned;
- descriptive legacy-cohort Zigong DiffusionGemma result is not central evidence;
- very strong structured comparators, especially RRT and ICU death, leave limited room for discrimination gains;
- post-registration explanatory analyses are exploratory.

## Reporting and submission

Use TRIPOD+AI and TRIPOD-LLM as reporting cross-checks.

Preferred submission ladder under the no-author-APC constraint:

1. JAMIA, using the standard subscription route if open-access support is unavailable;
2. PLOS Digital Health if Penn State institutional coverage is confirmed for the corresponding-author affiliation;
3. a methods-oriented hybrid/subscription fallback with no mandatory author APC.

No journal requiring an unavoidable author-paid APC should be used.

Post a medRxiv preprint at journal submission if consistent with the selected journal's current policy.

AI-tool use and assistance should be disclosed exactly as required by the target journal. Clean inaccurate or irrelevant tool fingerprints from exported files, but do not conceal provenance or make false authorship claims.

## Stop condition

The research phase ends when:

- the H8 and H9 deviations are logged;
- the label-free alignment audit passes scientific review;
- semantic-only discrimination and comparator decomposition are complete;
- the OSF text-level PDF comparison is recorded (complete 2026-10-03);
- the manuscript-number provenance index is complete.

Then write, generate the central figure/supplement/checklists, and submit. No additional analysis is permitted without a concrete integrity or reviewer-driven reason.


## Execution checkpoint, 2026-10-03

The label-free semantic alignment audit is complete at job `V3K7R2M9` and exact commit `3f3eb770e9d2b60726bb34868481e651f669672e`.

The matched hemodynamic and respiratory constructs show consistently stronger expected-direction associations with corresponding structured support states than between-patient shuffled semantic vectors. Semantic/note case IDs matched exactly and the shuffled reference had zero same-patient donor assignments. This is sufficient for the narrow integrity purpose of excluding gross score-to-stay misalignment.

`reassuring_stability` was weak/inconsistent and should not be treated as construct-validated.

The semantic-only discrimination and four-level HGB comparator decomposition are the only active predictive analysis and are being executed together under the bounded exploratory task `evaluate_submission_exploratory_v2_1`. No additional predictive experiment should be introduced after that task completes.


## Research-phase closure, 2026-10-03

The bounded Paper 1 computational work is complete.

- H8 deviation: logged.
- H9 deviation: logged.
- Label-free semantic alignment audit: complete and passed its narrow gross-alignment purpose.
- Semantic-only discrimination: complete.
- Four-level HGB comparator decomposition: complete.
- OSF attachment scientific-text verification: complete.
- Paper 1 provenance index: created and current.

The final explanatory result is:

- ventilation semantic-only AUROC 0.60257; Open-Jev delta AUROC +0.02032 over the 34-feature structured comparator, +0.01137 after treatment/support, -0.00172 after documentation behavior, and -0.00005 with the registered rich comparator;
- RRT semantic-only AUROC 0.44790 with essentially zero incremental AUROC at every comparator level;
- MetaVision death semantic-only AUROC 0.65682 but no positive incremental AUROC even over structured physiology alone (level A delta -0.00428).

For ventilation, the positive early-level increment cannot be assigned purely to semantic content because semantic-score missingness also reveals note availability before documentation/note context is explicitly represented. Its disappearance after documentation behavior is therefore interpreted as evidence that apparent narrative value is substantially absorbed by documentation-process/context information, not as causal mediation.

**No further predictive experiment is permitted before initial submission unless a concrete integrity defect is discovered.**

The remaining work is manuscript production: final figure/table generation, manuscript and supplement drafting, TRIPOD+AI/TRIPOD-LLM cross-checks, journal-specific disclosure/metadata review, preprint preparation, and submission.
