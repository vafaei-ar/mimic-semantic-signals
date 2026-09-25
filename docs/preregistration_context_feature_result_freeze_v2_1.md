# Preregistration context feature result freeze v2.1

Updated: 2026-09-25

## Status

**Frozen for preregistration and downstream split/corpus planning.**

Canonical RunRelay job:

- job: `G8R6Q4M2 — Rebuild v2.1 Context Features`
- exact project commit: `7af5679eecb162b1d6f5819744680f395732bf97`
- task: `build_preregistration_context_features_v2_1`
- status: completed
- exit code: 0
- runtime: 530.908 seconds
- aggregate artifact: `outputs/multitask_benchmark/preregistration_context_features_v2_1.json`
- artifact SHA-256: `04cd6ab090518ad570909e57705d1331ceefeb632327666c9c4fa238588eabbf`

No clinical outcome model was fit or scored and no outcome label was used to select, transform, or drop a context feature.

## Final FiO2 cleaning

Target unit: percent.

Frozen rule:

- `0 < value <= 1`: multiply by 100;
- `20 <= value <= 100`: retain;
- all other numeric values: missing.

Aggregate cleaning diagnostics:

### CareVue
- numeric candidate rows: 26,245;
- fraction-scale rows converted: 26,210;
- percent-scale rows retained: 35;
- invalid/out-of-range rows rejected: 0.

### MetaVision
- numeric candidate rows: 26,787;
- fraction-scale rows converted: 9;
- percent-scale rows retained: 26,673;
- invalid/out-of-range rows rejected: 105.

All final FiO2 features are within the frozen 20–100% range.

## Final documentation-behavior block

Included:

- `doc_note_count_12h`;
- `doc_note_chars_total_12h`;
- `doc_note_chars_latest_12h`;
- `doc_note_category_groups_12h`;
- `doc_nursing_note_count_12h`;
- `doc_physician_note_count_12h`;
- `doc_respiratory_note_count_12h`;
- `doc_other_note_count_12h`.

Excluded:

- `doc_last_note_gap_hours` — original implementation was all-missing due to index alignment;
- `doc_hours_since_last_note` — exactly duplicates selected-note age under the same note eligibility/timing definition.

Ordinary note context remains:

- `has_note`;
- selected-note age at landmark;
- collapsed selected-note category.

## Frozen context feature files

### Invasive ventilation — MetaVision
- rows: 11,116;
- unique patients: 8,982;
- context feature count: 19;
- local context file SHA-256: `171e39595d8acadd595abfabb0a423fbb306899b347386d3595866da04ed5ab0`;
- note-identity SHA-256: `4a5f75dc9fd16fd0e3394c97d47d99d842230cc301ab01e4794ca969bd7271f3`;
- FiO2 nonmissing: 1,084 / 11,116 (9.75%);
- FiO2 range: 21–100%.

### RRT — MetaVision
- rows: 19,395;
- unique patients: 15,080;
- context feature count: 19;
- local context file SHA-256: `d008836347be7958e7e56227ea66e9b7dbaaeef1ea9f985456d850a1b6a09843`;
- note-identity SHA-256: `750f84b5f887928c90592137e5b0c7bb035530ce446a3542b3def0f9d5eab858`;
- FiO2 nonmissing: 8,575 / 19,395 (44.21%);
- FiO2 range: 21–100%.

### ICU death — MetaVision confirmatory
- rows: 19,811;
- unique patients: 15,312;
- context feature count: 23;
- local context file SHA-256: `57990b9292f3a7efa1e4ae9626641141aa974cb4bcec109a38e887323444fec8`;
- note-identity SHA-256: `9d604176b53dac81f8a5e2d08e26dedcbea1f9e604baf200565d50a2e89b97dd`;
- FiO2 nonmissing: 8,795 / 19,811 (44.39%);
- FiO2 range: 21–100%;
- code-status available: 51.07%;
- code-status limitation indicator: 4.05%;
- comfort/no-CPR indicator: 0.13%.

### ICU death — CareVue replication
- rows: 25,632;
- unique patients: 19,736;
- context feature count: 23;
- local context file SHA-256: `c98009cc5497608c8a8942a0ac7ab4920ded99b1c140c0967472c35bf4a99229`;
- note-identity SHA-256: `bc1c29e740b418cb0a5ad477e4de6be16ec9ce8d031fe8b6c2b1db2cce11bfc1`;
- FiO2 nonmissing: 12,032 / 25,632 (46.94%);
- FiO2 range: approximately 21–100%;
- code-status available: 85.84%;
- code-status limitation indicator: 5.97%;
- comfort/no-CPR indicator: 0.37%.

## Treatment/support summary

The frozen context layer contains:

- latest valid FiO2 in prior 6h;
- latest oxygen flow in prior 6h;
- high-flow oxygen indicator;
- NIV indicator;
- vasoactive exposure/state and active-agent count;
- sedative/analgesic exposure/state and agent count;
- ICU-death code-status indicators;
- documentation-behavior metadata;
- ordinary note context.

No invasive ventilator/intubation endpoint-defining item is included in the primary ventilation context block.

## Superseded context build

`E9R6Q4M2` completed successfully but its row-level hashes are superseded because raw FiO2 was not yet normalized to a single physiologic scale and `doc_hours_since_last_note` duplicated selected-note age. E9 remains provenance only.

## Downstream gate

This context layer may now be used for:

1. fixed-note corpus materialization;
2. deterministic patient-grouped split freezing;
3. aggregate-count power/MDE planning;
4. synthetic-only refit-bootstrap benchmarking;
5. drafting the post-review confirmatory SAP.

It is **not authorization** to run real-label predictive, semantic, lexical, calibration, or decision-curve analyses before OSF registration.
