# ICU-death source-system strategy freeze v2.1

Updated: 2026-09-25

## Status

**Frozen before any v2.1 mortality prediction performance is opened.**

Canonical diagnostic job:

- job: `X9R4Q2M6 — Audit Death Source Strategy`
- project commit: `9b6483dd20bed03b468629078f6b9f4ee70fcd7d`
- task: `audit_death_source_strategy_v2_1`
- status: completed
- exit code: 0
- runtime: 113.824 seconds
- artifact: `outputs/multitask_benchmark/death_source_strategy_audit_v2_1.json`
- artifact SHA-256: `02c180e471a0b25dbe7a5ba43d56a3c4ad9b8770212d82d598122b13e6c50081`

No mortality AUROC, AUPRC, calibration, Brier score, log loss, or decision curve was computed.

## Source-system diagnostic

CareVue versus MetaVision was predicted with 5-fold patient-grouped regularized logistic regression.

| Feature block | Source-prediction AUROC |
| --- | ---: |
| Latest note category only | 0.8528 |
| Note context without category | 0.8226 |
| Documentation behavior without category | 0.9527 |
| Documentation behavior with category | 0.9528 |
| Core structured values only | 0.7672 |
| Core structured + missingness | 0.8126 |
| Core structured + documentation, no note category | 0.9795 |
| Current full comparator | 0.9796 |

The preregistration source-proxy threshold was 0.80. The pooled all-source death comparator therefore fails the source-proxy gate.

The result shows that the problem is not limited to one note-category label. It persists through note availability/timing, documentation behavior, structured missingness, and their combination.

## Frozen confirmatory death population

The primary/confirmatory ICU-death analysis is restricted to **MetaVision** stays.

MetaVision death cohort:

- rows: 19,811;
- unique patients: 15,312;
- cases: 214;
- controls: 19,597;
- prevalence: 1.0802%;
- note-available rows: 7,889;
- note coverage: 39.82%;
- case-note coverage: 38.79%;
- control-note coverage: 39.83%.

This choice is based on source-system comparability and was made before mortality model performance was observed.

It also aligns the confirmatory death analysis with the ventilation and RRT analyses, which are already MetaVision-only.

## Prespecified CareVue replication/sensitivity

CareVue remains a prespecified within-source replication/sensitivity analysis rather than being discarded.

CareVue death cohort:

- rows: 25,632;
- unique patients: 19,736;
- cases: 306;
- controls: 25,326;
- prevalence: 1.1938%;
- note-available rows: 23,272;
- note coverage: 90.79%;
- case-note coverage: 92.48%;
- control-note coverage: 90.77%.

The CareVue result will be estimated separately using the same conceptual comparison and will not be pooled with MetaVision by default.

If the two source systems disagree, that heterogeneity will be reported rather than averaged away post hoc.

## Rows outside the two source systems

The original all-source adult death cohort contains 45,571 rows. CareVue plus MetaVision account for 45,443 rows; 128 rows have neither source label in the source-specific diagnostic frame.

These rows are retained in the all-source cohort provenance but are not part of either source-specific death analysis.

## Documentation-behavior consequence

No cross-source normalization is used for the confirmatory death analysis.

Instead:

- ventilation: MetaVision only;
- RRT: MetaVision only;
- confirmatory death: MetaVision only;
- CareVue death: separate replication/sensitivity.

This avoids asking the model to operate across documentation systems whose behavior and missingness patterns are readily distinguishable.

The previously proposed `doc_last_note_gap_hours` candidate is dropped from the frozen documentation-behavior block because the R3 version was all-missing due to an implementation defect. Other metadata candidates remain eligible for model-free availability freezing.

## Statistical hierarchy

For the three-outcome confirmatory family:

- ventilation primary population: frozen MetaVision cohort;
- RRT primary population: frozen MetaVision cohort;
- ICU-death primary population: MetaVision subset defined here.

Holm multiplicity control will apply to these three outcome-level primary semantic comparisons.

CareVue death is a prespecified replication/sensitivity and is not an additional member of the three-test confirmatory family.

## Guardrails

- no `dbsource` predictor;
- no pooled cross-source death comparator in the confirmatory analysis;
- no mortality model performance informed this decision;
- source-specific split hashes must be frozen after the treatment/documentation comparator is finalized;
- power/MDE planning must use the MetaVision death counts for the confirmatory death hypothesis.
