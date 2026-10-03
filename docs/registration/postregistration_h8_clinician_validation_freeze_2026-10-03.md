# H8 clinician construct-validation freeze v2.1

Updated: 2026-10-03

## Status

**Frozen before any clinician rating is collected.**

This document resolves implementation details left open by OSF registration `ahxn9` without changing H8's scientific question. The registration specifies a random sample of frozen notes, blinded clinician ratings of the eight registered constructs, inter-rater reliability, same-construct versus cross-construct model-human association, and clinician 12-hour deterioration probabilities.

## Sampling frame

H8 uses the **frozen stripped-note MetaVision ICU-death corpus** as the single note frame.

Rationale: it is the largest registered primary MetaVision note frame and avoids duplicate-note/corpus ambiguity across outcome-specific corpora. H8 is construct validation rather than outcome-specific predictive validation.

- frame: 7,889 note-available MetaVision ICU-death rows;
- source file: `data/real_mimic_local/population_landmark12_v2_1/icu_death/fixed_notes_stripped_v2_1_local.jsonl`;
- frozen corpus SHA-256: `8e60221c0c5db1074c0f14f5bd39b78252d0e5388bec8c3ca90b992c5a1a4aba`;
- sample size: **200 notes**;
- sampling: uniform random sampling without replacement from the sorted frozen case-id frame;
- random seed: **20261003**;
- outcome labels, model scores, comparator predictions, and H1-H7 results are not read or used for sampling.

The 200-note size is a pragmatic estimation sample intended to support stable multi-rater reliability and correlation estimates while keeping the manual annotation burden feasible. H8 remains estimation-first and has no success threshold.

## Raters and governance

The primary H8 panel contains **three independent clinician raters**, each rating all 200 notes.

Before any restricted note text is shown to a rater:

1. the Penn State IRB determination for the annotation activity must be documented;
2. each rater must satisfy the applicable PhysioNet credential and MIMIC-III DUA requirements;
3. note access must remain inside an approved local/institutional environment;
4. note text must not be transmitted through RunRelay, GitHub, external hosted LLMs, or other unapproved services.

The preparation task may freeze the sample and create local packets before the human-access gate is cleared, but those packets must not be distributed to raters until the gate is documented.

## Blinding

Raters see only:

- a pseudonymous `sample_id`;
- the exact frozen **stripped note text** seen by the registered Open-Jev primary instrument;
- the frozen construct definitions and rating instructions.

Raters do **not** see:

- patient/case identifiers;
- outcome labels;
- comparator predictions or risk strata;
- Open-Jev, Laya, DiffusionGemma, TF-IDF, or other model scores;
- H1-H7 results;
- other raters' scores.

Each rater receives the same 200 notes in an independently permuted order.

## Rating scale

For each construct, rate **0 to 100**:

- 0 = definitely absent / no evidence for the construct;
- 25 = weak evidence;
- 50 = uncertain or moderate evidence;
- 75 = strong evidence;
- 100 = definitely present / very strong evidence.

Intermediate integer values are allowed.

For `reassuring_stability`, higher values mean stronger evidence that the patient is clinically stable or reassuring without a new acute concern.

Each rater also provides a **0 to 100 percent probability of clinically important deterioration within the next 12 hours**, based only on the note.

A field may be left missing only when the construct or probability is genuinely not assessable from the note.

## Frozen construct wording

The eight construct questions and true/false criteria are copied exactly from `src/semantic_schema.py` and frozen in `config/v2_1_h8_clinician_validation_freeze.json`.

## Missingness and adjudication

- No rating is imputed.
- A note-construct clinician aggregate is computed when at least **2 of 3** raters provide a numeric rating.
- If fewer than 2 raters provide a rating, that note-construct pair is excluded from that construct's model-human association and its denominator is reported.
- ICC calculations use notes with complete ratings from all three raters for the relevant construct.
- The primary quantitative analysis uses **no consensus adjudication** and no post-rating reconciliation.
- Obvious data-entry errors may be corrected only with an audit trail and before model scores are joined to ratings.
- Any qualitative adjudication performed later is supplementary and cannot replace primary raw ratings.

## Primary H8 summaries

### 1. Inter-rater reliability

For each of the eight constructs and the 12-hour deterioration probability:

- two-way random-effects absolute-agreement ICC for a single rater, ICC(2,1);
- two-way random-effects absolute-agreement ICC for the mean of three raters, ICC(2,3);
- pairwise rater Spearman correlations as descriptive robustness summaries.

### 2. Same-construct model-human association

For each construct:

- clinician target = mean of available numeric ratings when at least two raters rated the construct;
- model target = the registered stripped-note Open-Jev score for the same note and same construct;
- association = Spearman rank correlation.

The primary H8 hypothesis is descriptive/directional: matched construct correlations should be positive.

### 3. Cross-construct discrimination

Construct an 8 x 8 Spearman matrix between Open-Jev construct scores and clinician aggregate construct ratings.

For each model construct report:

- matched diagonal correlation;
- mean signed off-diagonal correlation across the other seven clinician constructs;
- maximum signed off-diagonal correlation;
- diagonal-minus-mean-off-diagonal difference;
- rank of the matched correlation among the eight clinician constructs.

Also report the mean diagonal correlation and mean off-diagonal correlation across the full matrix.

No p-values or binary success criterion are used.

### 4. Clinician deterioration-probability association

Report Spearman correlations between each Open-Jev construct and the clinicians' mean 12-hour deterioration probability. This is descriptive; `reassuring_stability` is expected to have the opposite direction from concern constructs.

## Uncertainty

Use **2,000 patient-cluster bootstrap replicates** with seed `20261003`.

Resample source patients with replacement, retain all sampled H8 notes belonging to each sampled patient, and recompute:

- per-construct matched model-human Spearman correlations;
- diagonal-minus-off-diagonal summaries;
- global mean diagonal and mean off-diagonal correlations;
- ICC summaries when mathematically defined;
- deterioration-probability associations.

Report two-sided 95% percentile intervals. Degenerate bootstrap estimates are omitted and the valid-replicate count is reported; no replacement tuning is performed after ratings are seen.

## Primary instrument

H8's registered confirmatory model-human comparison uses the **primary stripped-note Open-Jev scores only**. Laya, DiffusionGemma, Clef, Clef-Flash, Nimble, Tev1, TF-IDF, and hosted Jev are not part of the registered H8 primary analysis.

## Data handling

Local restricted files include the selected note text, sample-to-case linkage, rater packets, raw clinician ratings, and row-level model-human joins. None is a shareable RunRelay artifact.

Shareable H8 artifacts may contain only aggregate counts, reliability/association summaries, hashes, and provenance.
