# Enhanced structured baseline discovery protocol v2

Status: frozen before any v2 predictive performance is examined.

The corrected v2 cohorts are frozen in `docs/corrected_landmark12_v2_cohort_result_freeze.md`. The purpose of this stage is only to identify defensible MIMIC-III item mappings and prospective availability for a stronger structured comparator.

No outcome association, AUROC, AUPRC, calibration, model coefficient, or semantic result may be computed during this discovery stage.

## Prespecified clinical concepts

The enhanced baseline candidate set is fixed at the concept level before dictionary/availability inspection.

### Demographics

- age at ICU admission;
- sex.

### Vital/bedside physiology

Using the latest value in the 6 hours before the 12-hour landmark, plus within-window change where repeated values exist:

- heart rate;
- systolic blood pressure;
- diastolic blood pressure;
- mean arterial pressure;
- respiratory rate;
- oxygen saturation;
- temperature.

### Neurologic status

Using the latest prospectively charted value in the 6 hours before landmark:

- Glasgow Coma Scale total when directly charted;
- otherwise components (eye, verbal, motor) may be retained separately if exact mappings are more reliable than a derived total.

No outcome-based choice between total versus components is permitted.

### Routine laboratory physiology

Using the latest value in the 24 hours before landmark:

- lactate;
- creatinine;
- blood urea nitrogen / urea nitrogen;
- white blood cell count;
- hemoglobin;
- platelet count;
- sodium;
- potassium;
- bicarbonate / total CO2;
- chloride;
- glucose;
- total bilirubin;
- INR;
- pH.

### Renal output

- total urine output in the 6 hours before the landmark, using output-event items explicitly representing urine volume;
- if body weight can be prospectively and unambiguously mapped without additional endpoint-dependent choices, a weight-normalized urine-output rate may be reported as a secondary structured feature, but raw 6-hour total remains the prespecified primary renal-output feature.

## Dictionary audit

The audit must inspect `D_ITEMS` and `D_LABITEMS` and report candidate item IDs, labels, source system, table link, category, fluid, and unit metadata where available.

Dictionary matching is for mapping discovery only. The audit may use broad label patterns, but the final feature mapping must be frozen manually from clinically coherent candidates before extraction.

## Availability audit

For each candidate item mapping, report model-free aggregate availability in the corrected v2 risk sets before the 12-hour landmark:

- number and fraction of unique ICU stays/admissions with at least one value inside the relevant lookback;
- source-system coverage;
- observed units and value-count summaries sufficient to identify obvious duplicate/unusable mappings.

Do not stratify availability by outcome label. The goal is data-source feasibility, not predictive screening.

## Inclusion rule for the final baseline

A clinical concept remains in the final baseline when:

1. the dictionary mapping is clinically unambiguous;
2. timing is prospectively available by the 12-hour landmark;
3. the item is compatible with the source population in which it will be used;
4. it has non-trivial availability in at least one corrected outcome cohort.

No minimum missingness threshold is used to cherry-pick features. Missing values will later be handled by training-fold imputation plus explicit missingness indicators.

If a concept cannot be mapped unambiguously, it is excluded with the reason documented.

## Guardrails

- no predictive model fitting;
- no label-conditioned feature selection;
- no outcome-performance metrics;
- no semantic/text inference;
- exact item IDs must be frozen after this audit and before feature extraction/evaluation;
- `dbsource` is never a predictive feature.
