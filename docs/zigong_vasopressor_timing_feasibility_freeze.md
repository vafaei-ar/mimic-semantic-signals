# Zigong vasopressor timing feasibility freeze

## Decision

Do not construct a prospective Zigong vasopressor cohort by combining nursing `ChartTime` with physician-order, transfer, laboratory, or discharge clocks.

Do not apply an empirical fixed nursing-time correction.

This decision is frozen before any external semantic-model performance is examined.

## Evidence

### Dataset documentation

The local `datDictionary.csv` states:

- `dtNursingChart.ChartTime`: measured in hours after hospital admission
- `dtDrugs.Drug_time`: prescription time measured in hours after hospital admission
- `dtTransfer.StartTime` and `StopTime`: hours offset from hospital admission
- `dtLab.LabTime`: hours offset from hospital admission
- `dtBaseline.ICU_discharge_time` and `DISCHARGE_DATE_TIME`: hours offset from hospital admission

Therefore these clocks are intended to share the same origin.

### Empirical inconsistency

Aggregate audits found:

- 2,080 of 2,597 patients with nursing records had a negative first nursing `ChartTime`.
- First nursing chart time preceded first ICU-transfer start by a median 23.3 hours.
- High-specificity nursing vasopressor administration-like mentions preceded first pressor orders by a median about 19.4 hours.
- A fixed offset scan did not identify a uniquely defensible correction:
  - +24 hours gave the broadest practical same-agent order alignment, with 64.8% within 6 hours and 91.7% within 12 hours;
  - +42 hours minimized median nearest-order distance, but had poorer broad alignment.

The offset optimizing one criterion therefore differs from the offset optimizing another.

## Interpretation

The nursing clock is inconsistent with its documented hospital-admission origin. The available evidence does not establish whether this reflects a constant transformation, a source-system export defect, multiple source-system origins, or another data-processing issue.

Because an empirically chosen correction would be outcome-adjacent and insufficiently justified, it must not be used to create a cross-table prospective vasopressor endpoint.

## Allowed next steps

External narrative feasibility may continue only through analyses that do not depend on aligning nursing `ChartTime` to another table.

Preferred route:

1. use relative chronology entirely within `dtNursingChart.csv`;
2. audit structured nursing fields that can define a prospective event independently of `NURSING_DESC`;
3. prioritize new invasive ventilation because it overlaps the frozen MIMIC multi-outcome benchmark;
4. freeze the event definition and risk-set construction before any semantic-model performance is examined.

Physician pressor orders may remain a secondary descriptive variable, but not the primary administration endpoint.
