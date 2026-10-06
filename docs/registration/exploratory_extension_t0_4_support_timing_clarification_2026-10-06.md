# Exploratory extension implementation clarification: T0.4 support timing

Date frozen: 2026-10-06  
Branch: `extension-v2_1`  
Parent protocol: `docs/registration/exploratory_extension_protocol_v2_1_2026-10-04.md`  
Related deviation: `docs/registration/exploratory_extension_t0_4_fio2_definition_deviation_2026-10-06.md`

This clarification freezes operational details for the three executable T0.4 support-transition pairs before any T0.4 result is computed.

## Analysis populations and note time

Run T0.4 separately in each of the three primary MetaVision outcome populations. Include only rows with the frozen eligible note and registered Open-Jev score.

Use the frozen selected-note `note_time`, which is the prospective documentation-availability time used by the v2.1 cohort builder (storetime when available, otherwise the frozen prospective fallback logic). No outcome label or outcome event time is read.

## Vasoactive support

Use the exact frozen MetaVision vasoactive item IDs from `config/v2_1_context_feature_freeze.json`.

Keep non-cancelled/non-rewritten INPUTEVENTS_MV intervals with positive rate when rate is recorded.

Across all vasoactive agents within a stay, merge overlapping intervals and intervals separated by less than six hours. A merged episode start is a qualifying transition only when:

- it occurs at least six hours after ICU admission; and
- either it is the first observed episode or the previous merged episode ended at least six hours earlier.

Vasoactive support is ongoing at note time if any valid infusion interval covers the note time.

## High-flow and NIV support evidence

Use the exact frozen MetaVision respiratory item maps and regular expressions from `config/v2_1_context_feature_freeze.json`.

Positive evidence is defined exactly as in comparator D:

- high-flow: oxygen-device chart value matching the frozen high-flow regex;
- NIV: oxygen-device chart value matching the frozen NIV regex OR any chart event on a frozen MetaVision NIV item.

For these chart-derived supports, a qualifying transition is the first positive support-evidence timestamp after at least six hours with no positive evidence for that support. The first positive event in a stay qualifies only if it occurs at least six hours after ICU admission.

This is explicitly an evidence-based operationalization of support-free time, not a claim of continuously observed device state.

High-flow/NIV is classified as ongoing at note time if positive support evidence exists in the six hours before or at note time, matching the frozen comparator-D support window.

## Note-relative categories

For each note/support pair:

- prior = most recent qualifying transition in the 12 hours before note time;
- subsequent = first qualifying transition in the 12 hours after note time;
- category = prior only, subsequent only, both, or neither.

Boundary convention: exactly 12 hours is included; a transition exactly at note time is classified as prior.

## Score groups and shuffle

Use the registered construct score:

- hemodynamic concern for vasoactive support;
- respiratory concern for high-flow and NIV.

Within each outcome population and construct, compute the 25th and 75th percentiles from the real score distribution. Low = score <= Q1; high = score >= Q3.

For the shuffled reference, reuse the existing deterministic between-patient complete-vector permutation and outcome-specific seeds from the semantic alignment audit:

- ventilation: 20261031;
- RRT: 20261032;
- ICU death: 20261033.

Because the shuffle preserves the score distribution, use the same Q1/Q3 cutoffs.

## Bootstrap

For the primary high-score subsequent-only proportion among notes with any qualifying transition in the +/-12-hour window, use 2,000 patient-cluster bootstrap replicates, matching the Tier-0 bootstrap scale.

- seed: 20261006;
- resample source patients with replacement;
- keep all sampled stays/notes for each sampled patient;
- report the two-sided 95% percentile interval;
- no model refitting occurs because T0.4 is descriptive and label-free.

## Guardrails

- no clinical outcome labels are read;
- no invasive ventilation, RRT, or death event is treated as a support transition;
- the FiO2 arm is not executed under an invented threshold;
- this is descriptive timing evidence, not a prediction or causal claim.
