# External-review integrity audit protocol v1

Status: frozen before executing the audit.

This audit was triggered by an external code review after completion of the v1 population semantic analyses. It is diagnostic and does not alter any frozen endpoint, cohort, model, or result. The purpose is to determine which review findings are factual, quantify their scope using local data, and define a corrected v2 analysis before any further manuscript-facing inference.

## Code-level findings already requiring audit

The repository review identified the following implementation concerns:

1. invasive-ventilation endpoint ascertainment uses MetaVision PROCEDUREEVENTS item 224385 as the endpoint while the population includes both MetaVision and CareVue stays;
2. population note context includes ICU `dbsource`;
3. outcome-language exclusion is applied before selecting the latest eligible note;
4. matched cases and controls use asymmetric disqualifying-evidence logic, and subjects who can contribute an eligible case are removed from the control pool;
5. Open-Jev/Laya inference stores max/min chunk aggregation but several v1 evaluators recompute semantic values as the mean of `chunk_values`;
6. MIMIC note category and `iserror` filters do not normalize whitespace/numeric representation;
7. eICU laboratory lookback is clipped at ICU admission whereas MIMIC/NWICU can use pre-ICU laboratory values inside the lookback window;
8. the Zigong leakage regex contains broad Chinese substrings and a doubled-backslash ETT boundary pattern.

## Local aggregate checks

The audit will report only aggregate counts and summaries.

### MIMIC population endpoint/source checks

For each population outcome:

- cases and controls by ICU `dbsource`;
- note coverage by label using the current language exclusion;
- note coverage by label before outcome-language exclusion;
- number and fraction of stays whose eligible latest note is lost or shifted because of language exclusion;
- among cases, number discharged before the end of the nominal 12-hour horizon after the landmark.

### Raw NOTEEVENTS hygiene checks

Report:

- exact category values that differ after `.strip()`, with counts;
- counts for exact `Physician`, `Physician `, `Respiratory`, and `Respiratory ` values if present;
- observed non-null `iserror` string representations and counts;
- number that the current `astype(str) != "1"` rule would fail to remove compared with a numeric nonzero rule.

### Leakage-screen shorthand checks

On the currently selected local notes, count notes containing prespecified common shorthand not covered by the current canonical screens:

- vasopressor: levo, neo, vaso, pitressin;
- ventilation: vent, BiPAP;
- RRT: HD, trialysis;
- ICU death: palliative.

No note text will be shared.

### Semantic aggregation and truncation checks

For Open-Jev and Laya raw outputs:

- fraction with stored max/min aggregate different from the mean of `chunk_values`;
- absolute aggregate-vs-mean difference summary;
- fraction of notes whose token length exceeds the maximum text coverage implied by the frozen chunk settings.

This is descriptive only. No semantic inference will be rerun.

### eICU lab-window check

Reconstruct the existing selected eICU risk-set snapshots deterministically and report the number of relevant laboratory observations that:

- fall within the intended 24-hour pre-anchor lookback;
- have negative ICU-relative offsets;
- are therefore excluded only because of the current lower-bound clip at zero.

No patient-level output is shared.

### Zigong leakage-regex check

Report:

- whether the current regex matches the literal string `ETT`;
- counts of notes excluded by the broad `气管` token when the text contains `支气管`;
- counts excluded by generic `拔除` without a specific airway/ventilation term;
- aggregate current exclusion counts.

## Interpretation rule

The audit may invalidate or qualify v1 analyses. If a code-level issue affects cohort membership, endpoint observability, semantic values, or external feature windows, corrected results must be rebuilt as a separate v2 lineage. V1 files remain for provenance and must not be overwritten.
