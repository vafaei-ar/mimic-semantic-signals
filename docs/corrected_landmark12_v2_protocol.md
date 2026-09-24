# Corrected 12-hour landmark cohort protocol v2

Status: **frozen before any v2 predictive performance is examined**.

This v2 lineage replaces the affected v1 manuscript-facing cohort definitions after the integrity audit `N7Q8V4R5`. All v1 outputs remain unchanged for provenance.

## Scientific role

The corrected primary analysis will use one fixed 12-hour ICU landmark framework across outcomes rather than rebuilding the earlier matched case-control benchmark. This removes the future-case control-pool problem and makes calibration/utility interpretable for the defined landmark cohort.

The estimand is a **12-hour ICU landmark cohort with complete 12-hour outcome ascertainment**, not literally every patient present at 12 hours.

## Common landmark

- landmark: 12 hours after ICU admission;
- prediction horizon: next 12 hours;
- unit: ICU-stay landmark;
- patient identity remains local and all later folds/bootstrap resamples must group by patient.

A stay must still be in the ICU at the landmark.

## Source-compatible outcome definitions

### Invasive ventilation

Primary v2 ventilation is restricted to ICU stays with `dbsource = metavision`.

Rationale: the high-specificity endpoint is MetaVision `PROCEDUREEVENTS_MV` item 224385. The v1 population mixed this endpoint with CareVue controls and then included `dbsource` as a predictor.

Endpoint:

- first MetaVision invasive-ventilation procedure item 224385 after the landmark.

Pre-landmark and control-horizon disqualifying evidence:

- procedure item 224385;
- MetaVision explicit/support chart items:
  - 223849;
  - 224684;
  - 224688;
  - 225306;
  - 225585;
  - 225588;
  - 225590;
  - 225592;
  - 226431;
  - 228069.

CareVue-only chart items 418, 619, 683, and 720 are not used in the MetaVision v2 risk set.

### Renal-replacement therapy

Primary v2 RRT is also restricted to `dbsource = metavision` so endpoint observability is internally consistent.

Endpoint and disqualifying evidence:

- MetaVision RRT procedure items 225441, 225802, 225803, 225805, 225809, 225955;
- MetaVision active RRT chart items 226499 and 227290.

Legacy/CareVue item 152 and legacy strict-output item IDs are not used in the primary MetaVision v2 definition.

### ICU death

ICU death is source-independent and retains all ICU `dbsource` values.

Endpoint:

- recorded death time occurring inside the ICU stay.

No source-system field will be used as a predictor in any v2 primary model.

## Symmetric landmark risk-set logic

For ventilation/RRT:

1. derive the first disqualifying evidence time per ICU stay;
2. exclude the stay if any disqualifying evidence occurs at or before the 12-hour landmark;
3. define a case if the first eligible endpoint occurs after the landmark and at or before 24 hours after ICU admission;
4. define a control only if:
   - no endpoint occurs in the horizon;
   - no disqualifying evidence occurs through the horizon end;
   - ICU observation continues through the full horizon end.

For ICU death:

- exclude deaths at or before the landmark;
- case = death after the landmark and through horizon end;
- control = no death through horizon end and ICU observation through horizon end.

A case need not remain in the ICU after the event through horizon end because its binary outcome is already observed. This is why the cohort is described as complete-outcome-ascertainment rather than an uncensored population sample.

No subject is globally removed because they become a case later. Multiple eligible ICU stays from the same patient may remain; patient-grouped inference is mandatory.

## MIMIC note hygiene

Load NOTEEVENTS prospectively with the following corrections:

1. strip outer whitespace from `CATEGORY` before category matching;
2. retain normalized bedside categories:
   - Physician
   - Consult
   - Nursing
   - Nursing/other
   - Respiratory
   - General
3. parse `ISERROR` numerically and exclude every non-zero value;
4. predictor availability time remains `max(CHARTTIME, STORETIME)` when STORETIME exists, otherwise CHARTTIME;
5. notes must be non-empty and prospectively available inside the ICU stay.

## Predictor-note selection

For every eligible outcome row, select the latest eligible bedside note in the 12 hours before the landmark.

**No outcome-language filter is applied before note selection.**

This is the critical correction to v1. Note existence, note category, and note age must not depend on whether the note contains outcome-related language.

Rows without a note remain in the primary cohort with `has_note = false`.

## Treatment-language sensitivity

Direct treatment/outcome language is clinically prospective information but can make intervention endpoints tautological. Therefore:

- the **primary v2 semantic/text analysis uses the prospectively available selected note without outcome-based note deletion**;
- a separately frozen sensitivity will use the **same selected note identity** and remove prespecified treatment/outcome-language spans from the text;
- that sensitivity may change text content but may not change `has_note`, selected note time, category, or cohort membership.

The sensitivity vocabulary will include the prior explicit terms plus common shorthand identified by the integrity audit, including `vent`, `BiPAP`, `HD`, `trialysis`, and `palliative`. Vasopressor shorthand will be handled in the separate vasopressor correction lineage.

## Documentation context

Primary semantic incremental models may adjust for:

- `has_note`;
- normalized note category;
- note age at the landmark.

They must **not** use ICU `dbsource`.

Documentation context will be reported separately from narrative semantic content.

## Semantic aggregation

For Open-Jev and Laya, evaluators must use the model runner's stored aggregate:

- maximum across chunks for the seven concern constructs;
- minimum across chunks for `reassuring_stability`.

Evaluators may not recompute the mean of `chunk_values`.

DiffusionGemma continues to use the corresponding stored max/min aggregate.

Because selected notes change under v2 note hygiene/selection, semantic inference must be rerun on the v2 note corpus. v1 row-level scores may not be remapped opportunistically.

## Structured comparator

The v1 11-variable structured model is too thin to support the final incremental-value claim.

Before any v2 predictive evaluation, a separate structured-feature protocol must freeze an enhanced prospective baseline. It will include the existing heart rate, MAP, respiratory rate, SpO2, lactate, creatinine, and WBC features plus a clinically standard expansion such as blood pressure, temperature, neurologic status, additional routine laboratory values, and demographics where valid.

No v2 semantic AUROC may be examined before that feature set is frozen.

## Primary and secondary analyses

Primary:

- enhanced structured baseline;
- structured + note context;
- + Open-Jev;
- + Laya;
- + TF-IDF;
- TF-IDF + Open-Jev;
- TF-IDF + Laya.

Secondary:

- note-available-only conditional analysis;
- treatment-language-stripped sensitivity using identical note identities;
- missingness-indicator sensitivity;
- DiffusionGemma replication after the corrected primary pipeline is stable.

## External validation corrections

External analyses are separate v2 lineages:

- eICU lab windows must use the full intended pre-anchor lookback, including valid negative ICU-relative offsets;
- Zigong leakage filtering must remove over-broad `气管` and generic `拔除` behavior and fix the ETT boundary;
- external v1 results remain provenance only until rebuilt.

## Guardrails

- preserve all v1 files;
- write v2 outputs to new paths only;
- no predictive performance during cohort construction;
- no outcome-based note deletion before note selection;
- no `dbsource` predictor;
- no matched case-control sampling in the corrected multi-outcome primary analysis;
- freeze enhanced structured features before semantic evaluation;
- group by patient for all cross-validation and resampling;
- explicitly label post-review corrections and v1 exploratory provenance in the manuscript.
