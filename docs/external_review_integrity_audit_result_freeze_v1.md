# External-review integrity audit result freeze v1

Canonical RunRelay job: `N7Q8V4R5`

- task: `audit_external_review_integrity`
- exact project commit: `c85aeaa5e3c8725ba03fdb2e9cc3fc834fef7212`
- artifact: `outputs/integrity/external_review_integrity_audit_v1.json`
- artifact SHA-256: `c7c91a33f9ab41ed1efa87dc9efc09ade8a9624efe50ce88db89e82b5932e0a8`
- exit code: 0
- runtime: 823.945 seconds
- protocol: `docs/external_review_integrity_audit_protocol_v1.md`

This document freezes the aggregate integrity audit triggered by external code review. It does not overwrite any v1 analysis. It defines which v1 result families require corrected v2 lineage before manuscript use.

## 1. Ventilation source-system observability is confirmed

Population ventilation labels by ICU source:

| dbsource | Controls | Cases |
| --- | ---: | ---: |
| CareVue | 17,233 | 1 |
| MetaVision | 11,107 | 280 |
| both | 77 | 1 |

Thus 280/282 ventilation cases are MetaVision while a large fraction of controls are CareVue. The v1 population context model included `dbsource`, so source system can encode endpoint observability. The large ventilation context gain is not interpretable as documentation-process signal.

## 2. Outcome-language filtering changes note availability and note identity

The v1 population builder removed notes containing outcome-language patterns before selecting the latest eligible note.

### Ventilation

- controls with any eligible note before filtering: 70.24%; after filtering: 67.92%;
- cases: 46.45% before; 43.97% after;
- 657 controls and 7 cases lose all eligible notes;
- 627 controls and 13 cases shift to an older note.

### RRT

- controls: 70.50% before; 69.53% after;
- cases: 52.43% before; 39.64% after;
- 472 controls and 50 cases lose all eligible notes;
- 225 controls and 29 cases shift to an older note.

### ICU death

- controls: 70.26% before; 68.23% after;
- cases: 71.14% before; 56.24% after;
- 994 controls and 80 cases lose all eligible notes;
- 492 controls and 60 cases shift to an older note.

The effect is large and strongly label-dependent for RRT and death. Note availability and note age from the v1 pipeline therefore partly encode the language-exclusion rule.

## 3. MIMIC note normalization bugs are confirmed

Across 2,083,180 NOTEEVENTS rows:

- `Physician `: 141,624 rows;
- exact `Physician`: 0 rows;
- `Respiratory `: 31,739 rows;
- exact `Respiratory`: 0 rows.

Because v1 compares categories without trimming whitespace, Physician and Respiratory notes are excluded.

The non-null `ISERROR` representation is `1.0` for 886 rows. The v1 string comparison against exactly `"1"` misses all 886 error rows.

## 4. Shorthand omissions are non-trivial

Among already selected v1 matched notes:

- ventilation shorthand `vent|BiPAP`: 46/1,460 notes, including 24/365 cases;
- RRT shorthand `HD|trialysis`: 170/2,332 notes, including 143/583 cases;
- death shorthand `palliative`: 20/8,240 notes.

The vasopressor shorthand audit could not be completed from the expected local selected-note path and remains unresolved.

## 5. Open-Jev/Laya aggregation inconsistency is confirmed

Inference stores max-across-chunks for concern constructs and min for reassuring stability. Several v1 evaluators instead use the mean of `chunk_values`.

Fraction of construct values where stored aggregate differs from the mean:

| Outcome | Open-Jev | Laya |
| --- | ---: | ---: |
| Ventilation | 63.63% | 21.23% |
| RRT | 54.16% | 15.55% |
| ICU death | 48.92% | 10.32% |
| Population unique notes | 66.27% | 19.63% |

For Open-Jev, the 95th percentile absolute stored-minus-mean difference is approximately 0.054–0.069 across outcome cohorts. This is not a negligible implementation detail.

Chunk truncation itself is rare under the frozen token limits:

- Open-Jev: 2 ventilation, 6 RRT, 14 death, and 27/36,117 population notes exceed the nominal maximum token coverage;
- Laya: essentially none.

Therefore the main semantic implementation problem is aggregation inconsistency, not truncation.

## 6. eICU lab-window mismatch is substantial

Among 34,116 selected eICU snapshots:

- 92,616 relevant lab rows fall inside the intended 24-hour pre-anchor lookback;
- 37,330 have negative ICU-relative offsets;
- all 37,330 are excluded solely by the v1 lower-bound clip at ICU hour zero.

Thus **40.31%** of intended relevant eICU lab rows are removed by the implementation difference. Structured transport involving these features requires corrected v2 evaluation.

## 7. Zigong leakage filter is over-broad and the ETT boundary is broken

Across 623,812 nursing-description rows:

- current regex excludes 261,164 rows;
- current regex does **not** match literal `ETT`;
- 562 excluded rows contain the bronchus term `支气管`, captured by broad `气管`;
- 3,090 rows are excluded by generic `拔除` without another specific airway/ventilation term.

The v1 Zigong narrative cohort and transport estimate require rebuilding under a corrected leakage policy.

## 8. Horizon observability wording

Cases discharged before the nominal 12-hour horizon end:

- ventilation: 4/282;
- RRT: 29/391;
- ICU death: 360/537.

This is not automatically an endpoint bug because cases are observed once the event occurs, whereas event-free controls require full horizon observation. However, the resulting estimand is a landmark cohort with complete outcome ascertainment, not literally every patient present at the landmark. Manuscript terminology must reflect this.

## Frozen decision

The following v1 result families are exploratory/provenance only until corrected:

- matched Open-Jev/Laya vasopressor and multi-outcome results that use mean chunk aggregation;
- all ventilation population analyses involving source-system context or the current endpoint-risk-set mixture;
- population note-context analyses affected by preselection language filtering;
- eICU structured transport using the clipped lab window;
- Zigong narrative transport from the current leakage filter.

The current population semantic evaluator uses stored Open-Jev/Laya aggregate values and is not affected by the mean-vs-max evaluator bug, but its cohorts remain affected by endpoint/source, note-normalization, and language-selection issues.

## Required v2 principles

1. preserve all v1 artifacts unchanged;
2. define source-compatible outcome ascertainment before modeling;
3. normalize MIMIC note categories and error flags;
4. choose the predictor note before any leakage-language sensitivity;
5. do not make note availability depend on treatment-language exclusion;
6. use stored model aggregation consistently;
7. use symmetric risk-set eligibility where matched risk sets remain in use;
8. correct external feature windows and leakage filters;
9. strengthen the structured baseline;
10. freeze corrected cohorts and modeling protocol before examining v2 predictive performance.
