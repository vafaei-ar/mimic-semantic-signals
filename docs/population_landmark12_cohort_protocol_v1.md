# Population-representative 12-hour landmark cohort protocol v1

This protocol is frozen before any model performance, calibration, or decision-curve analysis is examined in the representative landmark population.

## Landmark selection

The landmark is fixed at **12 hours after ICU admission**.

Selection used only the model-free feasibility audit `Q7K4R9M3`:

- artifact: `outputs/multitask_benchmark/population_landmark_feasibility_v1.json`
- SHA-256: `2a780dfbf0dc92a83511e63a5ea255454f4d60869a1ed6c6fc0c3a01e05b6b26`

The 12-hour landmark was selected because it provides a common clinically early landmark with substantially better prospective note coverage than 6 hours while retaining materially more future cases than 24 or 36 hours across all three outcomes.

No model prediction or performance was used in landmark selection.

## Outcomes and horizon

Frozen outcomes:

- invasive ventilation within the next 12 hours
- renal-replacement therapy within the next 12 hours
- ICU death within the next 12 hours

Endpoint evidence, disqualifying evidence, 6-hour incident washout, and endpoint-specific language exclusions are inherited unchanged from the frozen multitask benchmark.

## Population risk set

For each outcome, include every ICU stay that at the 12-hour landmark:

1. remains in the ICU;
2. is not excluded by the frozen prevalent/disqualifying endpoint rules;
3. is free of endpoint/disqualifying evidence through the landmark; and
4. has observable outcome status through the next 12 hours:
   - a case has the first eligible endpoint event after the landmark and within 12 hours;
   - a control has no such event and remains under ICU observation through the full 12-hour horizon.

No case-control sampling or matching is performed.

The primary unit is an ICU-stay landmark snapshot. Patient identity remains local so later uncertainty estimation and cross-validation can keep all stays from the same patient together.

## Prospective note handling

The population cohort includes stays with and without an eligible note.

For each outcome:

- prospective availability uses max(CHARTTIME, STORETIME) when STORETIME exists, otherwise CHARTTIME;
- apply the same frozen endpoint-language exclusion before note selection;
- search the 12 hours before the landmark;
- if one or more eligible notes exist, select the latest prospectively available note;
- otherwise retain the stay with `has_note = false`.

Semantic inference may be performed only for rows with `has_note = true`.

Future population-level models must handle unavailable semantic scores explicitly rather than dropping those stays after outcome labels are known.

## Expected aggregate counts from the frozen feasibility audit

### Invasive ventilation

- observable stays: 28,699
- future cases: 282
- observed controls: 28,417
- note-available stays: 19,426
- note-available cases: 124
- note-available controls: 19,302

### Renal-replacement therapy

- observable stays: 48,831
- future cases: 391
- observed controls: 48,440
- note-available stays: 33,834
- note-available cases: 155
- note-available controls: 33,679

### ICU death

- observable stays: 49,555
- future cases: 537
- observed controls: 49,018
- note-available stays: 33,749
- note-available cases: 302
- note-available controls: 33,447

The builder must reproduce these counts exactly or fail.

## Local outputs

For each outcome, local-only files may include:

- all population landmark rows with source identifiers and outcome labels;
- note availability and selected note timing;
- note text only for note-available rows in a separate model-input JSONL.

Only an aggregate manifest may be declared as a RunRelay artifact.

## Guardrails for the next stage

- no model inference during cohort construction;
- no case-control sampling;
- no post-outcome note selection;
- no landmark modification after model performance is observed;
- population calibration and decision curves must operate on the full observable risk set, not only the note-available subset;
- patients must be grouped across folds/bootstrap resamples in any inferential analysis.
