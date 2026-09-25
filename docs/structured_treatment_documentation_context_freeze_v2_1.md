# Structured treatment and documentation context freeze v2.1

Updated: 2026-09-25

## Status

**Frozen for preregistration feature materialization.**

Canonical availability audit:

- job: `A7R4Q2M6 — Audit Treatment Context`
- exact project commit: `58238190dd69e5d1e37216b0acfd6ee9e247eb55`
- task: `audit_treatment_context_availability_v2_1`
- status: completed
- exit code: 0
- runtime: 546.958 seconds
- artifact: `outputs/multitask_benchmark/treatment_context_availability_audit_v2_1.json`
- artifact SHA-256: `5775b15b0ab553d78099e7bfa6108da85c4c81be649a04d0e0032277a9b66428`

No clinical outcome performance was computed and no concept was selected using outcome performance.

## Confirmatory source system

The confirmatory ventilation, RRT, and ICU-death analyses are MetaVision-only. The treatment-context representation therefore uses MetaVision timing semantics for the confirmatory family.

CareVue ICU death remains a separate replication/sensitivity and uses source-compatible CareVue exposure semantics.

All extraction must enforce source-specific item-ID maps. The availability audit observed a few cross-era item IDs in otherwise MetaVision risk sets; these are not accepted merely because they appear in the table.

## Frozen treatment/support block

### Respiratory context

Use the prior 6 hours ending at the landmark.

1. **Latest FiO2**
   - MetaVision: item 223835.
   - CareVue replication: items 189, 190, 191, 727, 2981, 3420, 3422, 7570.
   - normalize to percent before selecting the latest valid value: values in (0,1] are multiplied by 100; values in [20,100] are retained; all other numeric values are treated as missing.
   - preserve missingness; do not force room-air values when none are charted.

2. **Latest oxygen flow**
   - MetaVision: items 223834, 227287, 227582.
   - CareVue replication: items 470, 471.
   - preserve missingness.

3. **High-flow oxygen indicator**
   - derive from the source-specific oxygen-delivery-device field;
   - positive strings include high-flow, HFNC, Vapotherm, or Optiflow variants;
   - binary any evidence in the prior 6 hours.

4. **Non-invasive ventilation indicator**
   - source-specific dedicated BiPAP/CPAP candidate items plus compatible delivery-device strings;
   - binary any evidence in the prior 6 hours.

Do **not** include invasive ventilator mode, PEEP, set tidal volume, set respiratory rate, or intubation/airway evidence in the primary ventilation treatment block. Those remain endpoint/disqualifying evidence.

### Vasoactive treatment

Frozen agents:

- norepinephrine;
- epinephrine;
- phenylephrine;
- dopamine;
- vasopressin.

Confirmatory MetaVision representation:

- `vasoactive_active_at_landmark`: any mapped non-cancelled infusion with starttime <= landmark < endtime and positive rate when rate is recorded;
- `vasoactive_agent_count_at_landmark`: number of distinct active mapped agents.

CareVue death replication:

- `vasoactive_recent_6h`: any mapped candidate exposure charted in the prior 6 hours with positive rate when rate is recorded;
- `vasoactive_agent_count_recent_6h`: number of distinct mapped agents in that window.

The CareVue representation is explicitly an exposure measure, not a claim that the infusion was active exactly at the landmark.

### Sedative/analgesic treatment

Frozen agents:

- propofol;
- midazolam;
- dexmedetomidine;
- fentanyl.

Confirmatory MetaVision representation:

- `sedative_active_at_landmark`;
- `sedative_agent_count_at_landmark`.

CareVue death replication:

- `sedative_recent_6h`;
- `sedative_agent_count_recent_6h`.

No indication is inferred from the medication.

### Code status

Code status is included only in the ICU-death treatment/context comparator.

Use the last source-specific code-status value charted at or before the landmark:

- CareVue item 128;
- MetaVision item 223758.

Frozen numeric encoding:

- `code_status_available`;
- `code_status_limitation`: DNR, DNI, or combined DNR/DNI wording;
- `code_status_comfort_or_no_cpr`: comfort-measures or CPR-not-indicated wording;
- `code_status_other`: other/remarks or uncategorized nonempty values.

Full-code values are the reference state: available=1 and the three non-full-code indicators=0. No prior code-status row is represented by all four indicators=0.

## Model-free availability supporting this freeze

### MetaVision confirmatory cohorts

| Concept | Ventilation | RRT | ICU death |
| --- | ---: | ---: | ---: |
| FiO2 available | 9.9% | 44.4% | 44.6% |
| Oxygen flow available | 59.2% | 44.5% | 44.4% |
| Oxygen device available | 83.6% | 87.5% | 87.5% |
| NIV evidence | 1.89% | 1.46% | 1.50% |
| Active vasoactive therapy | 6.49% | 15.34% | 15.65% |
| Active sedative/analgesic therapy | 0.10% | 22.36% | 22.55% |
| Code status available | 48.8% | 51.0% | 51.1% |

Code status is reported above for completeness but enters only the death comparator.

### CareVue death replication

- FiO2 available: 47.5%;
- oxygen flow available: 45.6%;
- oxygen device available: 54.9%;
- recent 6-hour vasoactive exposure: 26.5%;
- recent 6-hour sedative/analgesic exposure: 32.8%;
- code status available: 85.9%.

The large source differences are one reason CareVue is not pooled with MetaVision.

## Frozen documentation-behavior block

Use note metadata only; do not use note text.

Prior 12-hour features:

- `doc_note_count_12h`;
- `doc_note_chars_total_12h`;
- `doc_note_chars_latest_12h`;
- `doc_note_category_groups_12h`;
- `doc_nursing_note_count_12h`;
- `doc_physician_note_count_12h`;
- `doc_respiratory_note_count_12h`;
- `doc_other_note_count_12h`.

The previously proposed `doc_last_note_gap_hours` is **excluded**. Its first implementation was all-missing because of index misalignment and it is unnecessary for the frozen primary documentation-behavior block.

`doc_hours_since_last_note` is also excluded from the documentation-behavior block because, under the same eligible note categories and timing rule, it is exactly the selected-note age already carried in ordinary note context. This avoids duplicating the same predictor under two names.

Ordinary note context remains separate:

- `has_note`;
- selected-note age at landmark;
- collapsed selected-note category: nursing, physician, respiratory, other.

This is a CONCERN-inspired documentation-metadata comparator, not a replication of the proprietary/implementation-specific CONCERN feature set. Device-driven physiologic sampling frequency is deliberately not counted as documentation behavior.

## Comparator hierarchy

The primary semantic comparison will ultimately add stripped Open-Jev scores to the richest prespecified comparator:

1. core 34-feature structured physiology;
2. treatment/support context frozen here;
3. documentation-behavior metadata frozen here;
4. ordinary note context.

No source-system indicator is included.

## Guardrails

- no post-landmark information;
- no outcome-conditioned feature selection;
- no `dbsource` predictor;
- no endpoint-defining invasive-ventilation variable in the ventilation treatment block;
- source-specific item IDs are enforced;
- CareVue and MetaVision medication timing semantics are not silently equated;
- all features must be materialized and aggregate-checked before CV split/power execution is considered registration-ready.
