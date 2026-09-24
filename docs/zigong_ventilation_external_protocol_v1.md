# Zigong external narrative ventilation transport protocol v1

This protocol is frozen before any semantic-model performance is examined on Zigong.

## Scientific role

This is a **secondary external temporal-transport analysis** of narrative prediction of new invasive ventilation.

It is not an exact replication of the frozen MIMIC 12-hour ventilation benchmark because Zigong nursing narratives are effectively documented at approximately 24-hour cadence. The prespecified 12-hour feasibility audit found zero usable pre-event narratives within 12 hours. A 24-hour transport horizon is therefore used and must be reported as such.

This analysis does not alter or replace any frozen MIMIC zero-shot, tuning, or locked-test result.

## Source data

Zigong Fourth People's Hospital critical care infection database v1.1.

Only `dtNursingChart.csv` is used for prospective event timing and narrative timing. Static `dtBaseline.csv` identifiers are used only to enforce patient-level uniqueness.

The nursing clock is used only in **within-table relative time** from each encounter's first valid timed nursing row. No fixed correction is applied to `ChartTime`, and no medication-order, transfer, laboratory, or discharge clock is used to define the endpoint.

This restriction follows the frozen timing-feasibility decision in `docs/zigong_vasopressor_timing_feasibility_freeze.md`.

## Frozen outcome

Outcome: new invasive ventilation within 24 hours.

Qualifying event: the first nursing row satisfying both:

1. numeric endotracheal-tube depth between 10 and 40 cm, using `Endotracheal_intubation` when numeric and otherwise `Endotracheal_intubation_Depth`;
2. same-row numeric `Vt_setting` between 100 and 1000 mL.

Rationale: the tube-depth criterion identifies an endotracheal airway and the contemporaneous tidal-volume setting increases specificity for invasive mechanical ventilation. The broader explicit-airway-mode definition is not used because its first appearance can lag already-present ETT/ventilator evidence.

## Incident-event rules

- define encounter time zero as the first valid `ChartTime` in that nursing encounter;
- require the first qualifying ventilation event to occur at least 6 hours after encounter time zero;
- because the event is the first qualifying row, no prior row meeting the frozen event definition is allowed;
- exclude a case if `Extubation == True` occurs before the first qualifying event.

## Predictor narrative

For each eligible case:

- use the most recent nonempty `NURSING_DESC` strictly before the event and no more than 24 hours before the event;
- direct ventilation leakage terms are excluded before note selection;
- choose only one predictor narrative per case.

Frozen leakage screen, case-insensitive where applicable:

- Chinese: `插管`, `气管`, `气切`, `呼吸机`, `机械通气`, `拔管`, `拔除`
- English: `intubat`, `endotracheal`, `tracheost`, `ventilat`, `extubat`, `ETT`

No event-row or post-event narrative is permitted.

## Risk-set controls

Three controls per case, without replacement.

Control eligibility at the selected control narrative time:

- patient is not a case patient anywhere in the frozen case cohort;
- nonempty leakage-clean `NURSING_DESC`;
- no qualifying invasive-ventilation event at or before the narrative time;
- no qualifying event during the subsequent 24 hours;
- nursing observation remains available through narrative time + 24 hours.

Matching:

- use within-nursing elapsed time from each encounter's first valid timed row;
- prioritize controls whose narrative elapsed time is within 6 hours of the case narrative elapsed time;
- maximum allowed elapsed-time difference is 12 hours;
- deterministic seeded tie-breaking, seed 20260924;
- each control patient may be used once.

If a case cannot obtain three controls under the frozen criteria, drop the entire case match set.

## Cohort outputs

Patient-level notes and source identifiers remain local and are never declared as RunRelay artifacts.

The only shared artifact is an aggregate manifest reporting:

- eligible cases before and after note availability/exclusion rules;
- fully matched cases and controls;
- prediction lead-time distribution;
- elapsed-time matching distance;
- patient-overlap checks;
- blank-note and leakage-screen checks.

## Next gate before model scoring

After the cohort is frozen, perform a local aggregate language/tokenizer applicability audit for the already-frozen Open-Jev, Laya, and DiffusionGemma pipelines.

No Zigong outcome performance may be inspected before the cohort and language/preprocessing rules are frozen.
