# Frozen multi-outcome semantic benchmark protocol v1

Frozen before any Open-Jev, Laya, DiffusionGemma-Jev, TF-IDF, or structured-model performance is examined for the new outcomes.

## Scientific question

Do compact semantic scores extracted from prospectively available bedside notes carry reusable predictive information across clinically distinct deterioration outcomes, beyond contemporaneous structured EHR physiology?

The previously completed vasopressor analysis remains a frozen 6-hour case study. The new cross-domain benchmark adds three outcomes selected from timestamp validity, clinical specificity, event counts, prospective-note coverage, and leakage risk only.

## Local-only model policy

All credentialed clinical-note inference remains on the bound local workstation.

Models:
- Open-Jev DeBERTa
- Laya typed-decisions
- DiffusionGemma-Jev through a localhost-only Jev-compatible server

No MIMIC or other restricted note text is sent to Cloud Run or another remote inference API.

## Shared design

- MIMIC-III ICU stays.
- Incident endpoint washout: first 6 hours after ICU admission.
- New-outcome prediction horizon: 12 hours.
- Case note: closest eligible bedside note prospectively available within 0-12 hours before the event.
- Prospective note availability: max(CHARTTIME, STORETIME) when STORETIME exists; CHARTTIME fallback otherwise.
- Empty/whitespace notes excluded before matching.
- Direct endpoint-adjacent language is excluded before matching for both cases and controls.
- Controls are risk-set snapshots with no prior endpoint evidence, no endpoint/disqualifying evidence in the following 12 hours, and ICU observation through the full horizon.
- One case admission per patient.
- 1:3 matching without replacement by control patient.
- Same dbsource required.
- Priority to same note category and ICU elapsed-time distance <=6 hours; maximum elapsed-time distance 12 hours.
- Structured comparator uses the same contemporaneous feature-extraction style as the frozen vasopressor analysis.

## Outcome 1: vasopressor initiation

Already frozen separately.

- Horizon: 6 hours.
- Canonical drugs: norepinephrine, epinephrine, phenylephrine, dopamine, vasopressin.
- Primary frozen v5 cohort and all previously reported robustness analyses remain unchanged.

## Outcome 2: new invasive ventilation

Primary endpoint:
- MetaVision PROCEDUREEVENTS_MV item 224385, label "Intubation".

Prevalent/disqualifying ventilation evidence:
- explicit intubation chart evidence;
- explicit Intubation procedure;
- ventilator-support charting (ventilator mode, set tidal volume, set respiratory rate).

A patient/stay with any of those ventilation signals during the first 6 ICU hours is not incident-eligible.

Why procedure-only is frozen:
- the strict endpoint audit found 1,050 incident subjects;
- adding explicit intubation chart items produced the exact same 1,050 cases;
- generic ventilator settings are therefore unnecessary as endpoint events and are retained only to screen existing ventilation / false controls.

Primary prediction horizon: 12 hours.

Direct note-language exclusion:
- intubat*
- endotracheal
- mechanical ventilation
- ventilator
- ETT

## Outcome 3: new renal-replacement therapy

Primary endpoint:
- named RRT procedures in PROCEDUREEVENTS_MV:
  - Hemodialysis
  - Dialysis - CRRT
  - Dialysis - CVVHD
  - Peritoneal Dialysis
  - Dialysis - CVVHDF
  - Dialysis - SCUF
- plus active RRT charting:
  - Dialysis Type
  - Hemodialysis Output
  - CRRT mode

Prevalent/disqualifying RRT evidence during the first 6 ICU hours additionally includes a very narrow set of exact CareVue output labels ("dialysis", "hemodialysis", "peritoneal dialysis") as a conservative exclusion screen only.

Why output events are not endpoint events:
- after removing obvious off/out/removal bookkeeping, strict output events still showed essentially no temporal concordance with RRT procedures/active charting;
- they are therefore unsuitable as initiation timestamps.

Primary prediction horizon: 12 hours.

Direct note-language exclusion:
- dialysis
- hemodialysis / haemodialysis
- CVVH*
- CRRT
- hemofiltration / haemofiltration
- renal replacement

## Outcome 4: ICU death

Primary endpoint:
- ADMISSIONS.DEATHTIME occurring during the ICU stay, after the 6-hour incident washout.

Primary prediction horizon: 12 hours.

Broad end-of-life language is excluded before matching:
- dying / death / deceased
- comfort care / comfort measures
- CMO
- withdraw* care/support/treatment
- hospice
- DNR / DNI
- do not resuscitate / do not intubate
- goals of care

This intentionally makes the primary death task more conservative by reducing direct documentation of impending death or limitation-of-treatment decisions.

## Planned zero-shot model comparison after cohort freeze

For each outcome:
- structured EHR only
- 8 semantic scores only
- structured EHR + semantic scores
- TF-IDF only
- structured EHR + TF-IDF
- structured EHR + TF-IDF + semantic scores

Semantic models are evaluated independently:
- Open-Jev
- Laya
- local DiffusionGemma-Jev

No endpoint definition, horizon, leakage exclusion, or matching rule will be changed based on model performance.
