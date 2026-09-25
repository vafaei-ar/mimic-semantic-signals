# Structured treatment-context discovery protocol v2.1

Status: **prespecified before corrected v2.1 predictive performance is opened**.

Purpose: determine whether apparent narrative/semantic incremental value is partly explained by prospectively available treatment and respiratory-support information that is absent from the core 34-feature physiology baseline.

This is a **secondary comparator**, not a replacement for the core physiology model.

## Principle

The treatment-context feature set must be frozen through a model-free dictionary/availability audit.

Do not choose item IDs, lookback windows, encodings, or missingness thresholds using outcome performance.

## Candidate concepts

### Respiratory support

Prespecified candidates:

- latest FiO2 / oxygen concentration in the prior 6 hours;
- latest oxygen-flow rate in the prior 6 hours where clinically coherent;
- latest oxygen-delivery/support device category in the prior 6 hours;
- high-flow nasal oxygen indicator;
- non-invasive positive-pressure ventilation indicator.

For invasive-ventilation analyses:

- pre-landmark invasive-airway/ventilator evidence remains endpoint/disqualifying evidence rather than a predictor;
- do not add an invasive-ventilation flag that simply recreates the endpoint;
- PEEP/ventilator-mode variables require separate adjudication because they can overlap endpoint evidence.

### Vasoactive treatment

Prespecified candidates:

- any active norepinephrine;
- epinephrine;
- phenylephrine;
- dopamine;
- vasopressin;

within a prospectively available pre-landmark window.

A compact secondary representation may include:

- any vasoactive agent active at landmark;
- number of active vasoactive agents.

Exact medication item mappings and infusion-time rules must be frozen before performance.

### Sedative/analgesic treatment

Prespecified candidate exposures:

- propofol;
- midazolam;
- dexmedetomidine;
- fentanyl or equivalent ICU analgesic exposure if mapping is unambiguous.

Purpose: control for treatment intensity/state that may be described explicitly in notes.

Do not infer indication from the medication.

## Dictionary audit

The model-free audit should report:

- exact local dictionary labels and source systems;
- candidate item IDs;
- prospective time fields;
- aggregate availability in each corrected v2.1 risk set;
- ambiguity/endpoint-overlap flags.

Do not report performance by outcome label during mapping selection.

## Inclusion rules

Include a concept only when:

- clinical meaning is unambiguous;
- timing is prospectively interpretable;
- mapping is compatible with the relevant source-system risk set;
- it is not simply an alternate encoding of the outcome endpoint;
- availability is non-trivial without using an outcome-conditioned threshold.

## Planned comparators

Later semantic analyses should distinguish:

1. core structured physiology;
2. core structured + treatment/support context;
3. core structured + note documentation context;
4. semantic/lexical additions on top of each relevant structured comparator.

For ventilation, a semantic increment that disappears after adding respiratory-support context should be described as narrative recovery of omitted treatment/support information rather than unique latent deterioration signal.

## Guardrails

- no outcome-performance inspection during mapping;
- no dbsource predictor;
- no post-landmark treatment information;
- no endpoint-defining invasive ventilation variable as a predictor in the ventilation primary model;
- preserve the core 34-feature baseline unchanged for continuity.
