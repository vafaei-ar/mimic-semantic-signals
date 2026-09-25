# Integrity review hold: v1 manuscript-facing results

Updated: 2026-09-24

## Status

The integrity audit is **complete**.

Authoritative audit result:

- `docs/external_review_integrity_audit_result_freeze_v1.md`

Current corrected lineage:

- `docs/03_V2_ANALYSIS_LINEAGE.md`

The hold remains in force for affected v1 manuscript-facing estimates until the corrected v2 analyses are complete and frozen.

## Confirmed issues

The audit confirmed:

1. **Ventilation endpoint/source observability**
   - the v1 ventilation endpoint was overwhelmingly MetaVision-observable;
   - v1 population cohorts included many CareVue controls;
   - `dbsource` could therefore encode endpoint observability.

2. **Outcome-language filtering changed note identity/availability**
   - notes containing endpoint-language patterns were removed before the latest eligible note was selected;
   - this changed note availability and note age in an outcome-dependent way.

3. **Matched case/control asymmetry**
   - the old matched analysis used different disqualifying-evidence logic for cases and controls;
   - future case subjects were globally removed from the control pool.

4. **Open-Jev/Laya aggregation inconsistency**
   - inference stored max/min chunk aggregation;
   - several v1 evaluators recomputed the mean of `chunk_values`.

5. **MIMIC note normalization**
   - Physician and Respiratory categories had trailing spaces and were excluded by exact untrimmed matching;
   - numeric `ISERROR=1.0` rows were missed by the old string comparison.

6. **External-validation implementation**
   - eICU labs were clipped at ICU hour zero, removing 40.3% of intended relevant pre-anchor lab rows;
   - the Zigong leakage regex was over-broad and the ETT boundary pattern was broken.

## v1 result families on hold

Do not use as final manuscript headline evidence:

- matched vasopressor semantic increments;
- matched multi-outcome semantic/model-family comparisons;
- v1 population ventilation/context effects;
- v1 population semantic estimates as current primary estimates;
- eICU v1 transport estimates affected by the lab-window bug;
- Zigong v1 narrative transport estimates from the old leakage filter.

The original files remain unchanged for provenance.

## Corrective status

The corrected v2 program completed the first rebuild:

- source-compatible cohort rebuild;
- corrected note normalization;
- note selection before language sensitivity;
- removal of `dbsource` from the predictive feature set;
- enhanced 34-feature structured mapping;
- local structured feature extraction.

A second code review then identified an adult/NICU eligibility gap and ETT-coded GCS-verbal bug upstream of model fitting. The active manuscript gate is therefore the post-review **v2.1 correction**, not the pre-v2.1 structured result.

See `docs/06_POSTREVIEW_V2_1_CORRECTIONS.md`.

See:

- `docs/02_CURRENT_SCIENTIFIC_STATUS.md`
- `docs/03_V2_ANALYSIS_LINEAGE.md`

## Interpretation rule

A v1 result may be cited only as historical/exploratory provenance unless a current v2 freeze explicitly rehabilitates the same claim.

Do not present the old ventilation documentation-context jump as a biological or workflow signal. The audit established that source-system observability was a major component.
