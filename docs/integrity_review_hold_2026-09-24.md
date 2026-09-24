# Integrity review hold: v1 manuscript-facing results

Updated: 2026-09-24

An external code review identified implementation and cohort-definition issues after completion of the v1 analyses. Several concerns are confirmed directly from the repository code. A local aggregate audit is in progress under the frozen protocol `docs/external_review_integrity_audit_protocol_v1.md`.

Until the audit is complete and a corrected v2 protocol is frozen, the affected v1 results must be treated as provenance/exploratory results rather than manuscript-ready confirmatory evidence.

## Code-confirmed issues

1. **Ventilation endpoint/source observability**
   - the invasive-ventilation endpoint uses MetaVision `PROCEDUREEVENTS_MV` item 224385 as endpoint evidence;
   - population cohorts include both MetaVision and CareVue stays;
   - population note-context models include ICU `dbsource`;
   - therefore source system can encode endpoint observability.

2. **Outcome-language exclusion precedes note selection**
   - notes containing endpoint-language patterns are removed before the latest eligible note is selected;
   - this can make note availability and note age outcome-dependent.

3. **Matched case/control asymmetry**
   - incident cases are screened for disqualifying evidence before the washout boundary;
   - controls are screened for disqualifying evidence through each prediction horizon;
   - eligible case subjects are removed from the control pool entirely, so earlier valid risk-set snapshots from future cases cannot serve as controls.

4. **Open-Jev/Laya chunk aggregation mismatch**
   - inference stores max-across-chunks for concern constructs and min for reassuring stability;
   - v1 vasopressor and multitask evaluators instead use the mean of `chunk_values`;
   - DiffusionGemma evaluation uses its stored max/min aggregate.
   - The population semantic evaluator uses stored `noul` values and is not affected by this specific evaluator bug.

5. **Note normalization**
   - current MIMIC note loaders compare category values without trimming whitespace;
   - the current `iserror` filter compares string values to exactly `"1"` rather than using numeric nonzero status.

6. **External-validation implementation**
   - eICU laboratory lookback is clipped at ICU-relative hour zero, unlike MIMIC/NWICU lookbacks;
   - the Zigong leakage regex includes broad Chinese substrings and a doubled-backslash ETT boundary pattern.

## Result families currently on hold

The following v1 result families should not be used as final manuscript headline estimates until corrected:

- matched vasopressor semantic estimates;
- matched multi-outcome Open-Jev/Laya comparisons;
- population ventilation analyses involving note context/source;
- structured eICU transport estimates that depend on the current lab window;
- Zigong narrative transport estimates built from the current leakage filter.

The original v1 files remain unchanged for provenance.

## Documentation-process sensitivity

RunRelay job `K5Q8V7R3` completed successfully and is retained as a post-result diagnostic only.

For invasive ventilation:

- structured → + note availability: ΔAUROC +0.0276;
- + category/source after note availability: ΔAUROC +0.1247;
- + note age after category/source: ΔAUROC +0.00012.

This result should not be interpreted as evidence that documentation process itself is clinically predictive until the source-system observability problem is removed.

## Next gate

Complete the aggregate integrity audit. Then freeze one corrected v2 protocol that fixes endpoint observability, note-selection/leakage logic, case-control risk-set symmetry, semantic aggregation, note normalization, and external-data implementation differences before rerunning any manuscript-facing models.
