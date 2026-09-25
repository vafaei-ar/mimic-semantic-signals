# 06 — Post-review v2.1 correction gate

Updated: 2026-09-24

This document records a second independent code review received after the corrected v2 cohort and enhanced structured baseline had been built, but before the structured-only result from `E8R7Q5M3` was opened or frozen.

## Result-handling rule

The pre-v2.1 job `E8R7Q5M3` subsequently terminated with exit code 124 after reaching the 240-minute timeout. It produced no declared performance artifact.

It is **not manuscript-facing** and will not be retried. The corrections below must be resolved before a fresh structured evaluation is run.

The v2.1 correction should be completed first, followed by a fresh structured evaluation on the corrected cohort/features.

## Review findings and disposition

| Finding | Code-review disposition | v2.1 action |
| --- | --- | --- |
| Adult/NICU restriction absent | **Confirmed structural problem** | Restrict all primary cohorts to adults at ICU admission; explicitly exclude NICU first-careunit stays; report exclusions |
| Intubated GCS verbal encoded as numeric 1 | **Confirmed bug** | Treat CareVue `1.0 ET/Trach` and MetaVision `No Response-ETT` verbal rows as missing, not GCS verbal 1 |
| Ventilation case endpoint narrower than control-disqualifying evidence | **Confirmed design asymmetry** | Keep high-specificity 224385 primary endpoint, but add prespecified explicit-intubation and broad-support endpoint sensitivities |
| Treatment-language regex ambiguity | **Confirmed** | Replace ambiguous bare `HD`/`RRT`, remove BiPAP from invasive-language stripping, catch reintubation and withdrawal-of-care phrasing |
| No treatment/support context in structured baseline | **Important design gap, not an implementation bug** | Add a prespecified secondary structured treatment-context comparator after a model-free mapping audit |
| Prospective timing uses chart/specimen time | **Important sensitivity issue** | Add storetime-constrained CHARTEVENTS sensitivity and 1–2 hour lab-availability lag sensitivity; note-storetime fallback sensitivity |
| “All numeric missing” includes always-present age | **Confirmed diagnostic bug** | Report all-physiology/lab/treatment-missing instead |
| CV split file overwritten and not hashed | **Confirmed reproducibility weakness** | Freeze/load exact split files and record SHA-256 |
| Control `event_time` can contain post-horizon endpoint | **Confirmed leakage hazard for future reuse** | Store `event_time` only for cases |
| No expected-count assertions | **Confirmed guardrail gap** | Freeze expected v2.1 cohort counts after first clean build and assert them downstream |
| “Calibration intercept” naming | **Confirmed terminology issue** | Report joint recalibration intercept separately from calibration-in-the-large |
| Bootstrap omits refit variance | **Known/disclosed limitation** | Keep disclosure; use repeated cross-fitting as split/training variability diagnostic |

## 1. Adult primary population

The current v2 cohort builder reads all ICU stays and the current structured extractor clips negative ages to zero. That means neonatal/pediatric ICU stays can enter the source-independent ICU-death cohort.

v2.1 primary eligibility:

- age at ICU admission >= 18 years;
- first care unit must not be NICU;
- age is calculated from ICU admission and DOB before the >89 deidentification cap;
- deidentified elderly ages remain eligible and are capped to 90 only for modeling.

The adult restriction applies to **all three outcomes**, not only ICU death, so the manuscript estimand is consistent.

## 2. GCS verbal airway handling

The current extractor uses numeric `valuenum` only.

For v2.1:

- CareVue item 723 with raw value `1.0 ET/Trach` is treated as missing verbal GCS;
- MetaVision item 223900 with raw value `No Response-ETT` is treated as missing verbal GCS;
- no airway/intubation flag is silently encoded inside the GCS verbal score;
- any explicit airway/treatment-context feature belongs in the separately frozen treatment-context comparator.

## 3. Ventilation endpoint sensitivity

The primary v2 endpoint remains the high-specificity MetaVision intubation procedure item 224385.

Two endpoint sensitivities are prespecified before opening corrected performance:

### A. Explicit-intubation evidence sensitivity

Case endpoint is the first of:

- procedure item 224385;
- explicit MetaVision intubation chart items:
  - 225306;
  - 225585;
  - 225588;
  - 225590;
  - 225592;
  - 226431;
  - 228069.

### B. Broad respiratory-support evidence sensitivity

Case endpoint is the first of the explicit-intubation evidence above or:

- 223849 Ventilator Mode;
- 224684 Tidal Volume (set);
- 224688 Respiratory Rate (Set).

This broad arm is intentionally a sensitivity because ventilator-setting evidence can include non-invasive support.

For every arm, case and control eligibility use the same arm-specific endpoint/disqualifying definition.

## 4. Treatment-language sensitivity vocabulary

The language-stripped analysis is a content sensitivity, not a cohort-selection filter.

Corrections before semantic inference:

### Invasive ventilation

Include invasive-specific terms such as:

- intubation/intubated/reintubated/re-intubated;
- endotracheal;
- mechanical ventilation;
- ventilator;
- ETT.

Do not treat `BiPAP` alone as direct invasive-ventilation language.

### RRT

Retain unambiguous terms:

- dialysis;
- hemodialysis/haemodialysis;
- CVVH/CRRT;
- hemofiltration/haemofiltration;
- renal replacement;
- trialysis.

Do not use bare case-insensitive `HD` or `RRT` as direct-treatment markers because they can mean hospital day and rapid response team.

### ICU death

Include withdrawal wording with an optional `of`, e.g. `withdrawal of care`, in addition to the previously frozen palliative/comfort/death terminology.

## 5. Structured treatment-context comparator

Detailed prespecification:

- `docs/structured_treatment_context_discovery_protocol_v2_1.md`

The 34-feature physiology baseline remains useful and should be preserved.

Before semantic claims are finalized, add a **secondary treatment-context structured comparator** using concept mappings frozen without outcome-performance inspection.

Candidate concepts for model-free dictionary/availability audit:

- FiO2 / oxygen concentration;
- oxygen delivery device / respiratory-support category;
- high-flow or non-invasive respiratory support where prospectively charted;
- pre-landmark vasoactive treatment exposure;
- pre-landmark sedative/analgesic exposure.

PEEP/ventilator settings require special care because they may overlap the ventilation endpoint/disqualifying definition.

The scientific purpose is to test whether a semantic increment is actually treatment/support information omitted from the physiology-only comparator.

## 6. Prospective timing sensitivities

Detailed prespecification:

- `docs/prospective_timing_sensitivity_protocol_v2_1.md`

Primary v2.1 extraction keeps the existing clinically conventional chart/specimen-time features for continuity, but manuscript-facing robustness should include:

1. **CHARTEVENTS storetime sensitivity**
   - measurement must be charted by the landmark;
   - if storetime exists, require storetime <= landmark.

2. **Laboratory availability lag**
   - shift laboratory availability by 1 hour and 2 hours in separate sensitivities;
   - no result with delayed availability after the landmark may be used.

3. **Note availability sensitivity**
   - primary: max(charttime, storetime) when storetime exists;
   - sensitivity: restrict to notes with storetime available, or apply a conservative delay to charttime-only fallback notes.

## 7. Reproducibility and reporting corrections

For v2.1 structured evaluation:

- split assignments are generated once per corrected cohort and then loaded unchanged;
- split files are hashed and their SHA-256 values appear in the aggregate result;
- downstream semantic/TF-IDF evaluation must load those exact split files;
- controls have `event_time = NA` even if a later endpoint occurs outside the prediction horizon;
- cohort/feature counts are frozen after the first clean v2.1 build and asserted downstream;
- report:
  - calibration-in-the-large;
  - joint logistic recalibration intercept;
  - calibration slope;
  as separate quantities.

## What remains unaffected

The second review does not reverse the earlier corrections:

- MetaVision-only ventilation/RRT source compatibility;
- note-category whitespace normalization;
- numeric error-flag parsing;
- note selection before outcome-language stripping;
- stored semantic max/min aggregation;
- patient-grouped inference;
- the need for a stronger structured comparator;
- the wording “12-hour ICU landmark cohort with complete 12-hour outcome ascertainment.”

## Next execution order

No new RunRelay job is authorized by this document.

When execution resumes:

1. validate the v2.1 cohort/feature code;
2. run the adult v2.1 cohort build;
3. freeze exact counts;
4. run the corrected v2.1 structured feature extraction;
5. freeze exact availability;
6. freeze exact patient-grouped split hashes;
7. rerun structured-only evaluation;
8. only then open corrected semantic/TF-IDF inference/evaluation;
9. run the treatment-language and timing sensitivities;
10. proceed to clinician validation and corrected external transport.


## Hard stop before registration

Real-label predictive performance is now executable only after an OSF registration record is present. This is enforced in the v2.1 evaluator and in each outcome-specific runner.

The permitted pre-registration execution set is limited to:

1. synthetic/static integrity tests;
2. E8 partial-output quarantine;
3. corrected adult cohort construction and descriptive freeze;
4. corrected structured feature extraction and note-identity freeze;
5. label-free treatment/documentation/source-proxy audits;
6. deterministic CV split freezing;
7. aggregate-count power/MDE planning;
8. synthetic-only refit-bootstrap runtime/null benchmarking.

No AUROC, AUPRC, calibration, Brier score, log loss, or decision-curve result on real outcome labels may be produced before registration.


## Ventilation explicit-endpoint sensitivity clarification

During inspection of the first adult v2.1 descriptive cohort manifest, the explicit-intubation sensitivity was found to have unintentionally relaxed the pre-landmark risk-set exclusion by using the explicit endpoint itself as the disqualifying definition.

This was corrected **before any predictive performance was run or opened**.

The explicit-intubation sensitivity now:

- uses the same broad pre-landmark ventilation exclusion/control rule as the primary ventilation cohort;
- broadens only the post-landmark case endpoint from procedure item 224385 to procedure or explicit intubation chart evidence;
- must preserve the same control count as the primary ventilation cohort.

The broad respiratory-support sensitivity remains symmetric by design: broad support evidence defines both the post-landmark case endpoint and the disqualifying/control rule.


## Death source-system proxy gate

The preregistration context audit `R3V8M5Q2` completed before any v2.1 clinical outcome performance was opened.

It showed that the mixed-source ICU-death comparator remains strongly source-identifying even after collapsing note categories:

- documentation-behavior source-prediction AUROC: 0.9597;
- current full-comparator source-prediction AUROC: 0.9888;
- preregistration diagnostic threshold: 0.80.

This is a **label-free source-system confounding diagnostic**, not mortality prediction performance.

Therefore the pooled all-source ICU-death comparator is **not frozen for registration**. CV split freezing for ICU death is deferred until a source-system strategy is chosen without inspecting mortality performance.

The next allowed step is a preregistration-only decomposition of source recoverability by structured, note-context, and documentation-behavior blocks, together with descriptive CareVue/MetaVision cohort counts. The source strategy must then be locked before any death predictive evaluation.
