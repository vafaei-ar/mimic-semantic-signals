# Population-representative landmark feasibility protocol v1

This protocol is frozen before any population-calibration or decision-curve model performance is examined.

## Purpose

The existing MIMIC benchmark cohorts use 1:3 matched case-control sampling and therefore have an artificial 25% prevalence. They are appropriate for discrimination and matched comparisons, but not for population calibration, absolute-risk interpretation, or decision-curve net benefit.

Before building any representative analysis cohort, audit whether fixed ICU landmarks can provide adequate prospective note coverage and event counts under the already frozen endpoint definitions.

## Scope

Outcomes:

- invasive ventilation within 12 hours
- renal-replacement therapy within 12 hours
- ICU death within 12 hours

Frozen endpoint definitions, event evidence, 6-hour incident washout, bedside-note categories, prospective note availability rule, and endpoint-specific note-language exclusions are inherited from `src/54_build_multitask_benchmark.py`.

No model inference or model performance is examined in this feasibility audit.

## Candidate landmarks

Audit fixed times after ICU admission:

- 6 hours
- 12 hours
- 24 hours
- 36 hours

These landmarks are evaluated for feasibility only. No landmark is selected using model performance.

## Risk-set definition at each landmark

For each ICU stay and outcome:

1. the patient must still be in the ICU at the landmark;
2. ventilation/RRT stays with frozen endpoint-disqualifying evidence before the 6-hour washout are excluded;
3. the stay must be free of endpoint/disqualifying evidence through the landmark;
4. a case is an eligible first endpoint event occurring after the landmark and within the next 12 hours;
5. an event-free control must remain under ICU observation through the full 12-hour horizon;
6. cases may have an event before the end of the 12-hour horizon and therefore do not need to remain in the ICU after that event.

The audit operates at the ICU-stay snapshot level and reports both stay counts and unique-patient counts. Any later inferential analysis must cluster uncertainty by patient.

## Predictor-note availability

For each outcome and landmark:

- consider only prospectively available bedside notes using max(CHARTTIME, STORETIME), with CHARTTIME fallback;
- apply the same outcome-specific leakage-language exclusion as the frozen benchmark;
- use the latest eligible note available during the 12 hours before the landmark;
- if no eligible note exists in that window, the stay is counted as note-unavailable;
- no note text or patient identifier is shared in the artifact.

## Reported feasibility quantities

For every outcome × landmark:

- at-risk stays at the landmark;
- unique at-risk patients;
- outcome-observable stays;
- cases within 12 hours;
- observed controls;
- event prevalence before note restriction;
- stays with an eligible prospective note;
- note-available cases and controls;
- event prevalence in the note-available analytic population;
- note coverage overall and separately among cases/controls;
- note age at landmark;
- case note-to-event lead time.

## Guardrails

- no semantic, lexical, structured, or supervised model is scored;
- no calibration or decision curve is computed;
- no landmark is selected from predictive performance;
- this audit does not modify any frozen matched cohort.

After reviewing feasibility counts, a landmark may be frozen for a separate representative-risk analysis. If no landmark has adequate data, population calibration/decision-curve claims remain out of scope.
