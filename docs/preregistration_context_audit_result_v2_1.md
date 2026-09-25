# Preregistration context audit result v2.1

Updated: 2026-09-25

## Canonical run

- job: `R3V8M5Q2 — Audit v2.1 Context`
- exact project commit: `b1560d74ff10520640329b970af37cb098f2d52d`
- task: `audit_preregistration_context_v2_1`
- status: completed
- exit code: 0
- artifact: `outputs/multitask_benchmark/preregistration_context_audit_v2_1.json`
- artifact SHA-256: `3c02c3fff3eed289c46a4f7c04e04b82695a623bbcff1a4bfcf772405c56d5a3`

No clinical outcome performance was computed.

## Fixed-note identity hashes

The selected-note identities from the corrected v2.1 cohort are:

- invasive ventilation: `4a5f75dc9fd16fd0e3394c97d47d99d842230cc301ab01e4794ca969bd7271f3`
- RRT: `750f84b5f887928c90592137e5b0c7bb035530ce446a3542b3def0f9d5eab858`
- all-source ICU death: `a80ee31747ff0aa0d4d7d826a2b5516ce09f5dc9345c23a17b516783faf6ec77`

The ventilation and RRT hashes are suitable for downstream fixed-note corpus construction. The all-source death hash is retained as provenance but is not yet the confirmatory death note-frame hash because the mixed CareVue/MetaVision population failed the source-proxy gate.

## Documentation-behavior candidate block

The model-free audit constructed the following pre-landmark metadata candidates:

- note count in prior 12h;
- total note characters in prior 12h;
- latest-note character count;
- number of collapsed note-category groups;
- hours since latest note;
- gap between the two latest notes;
- nursing-note count;
- physician-note count;
- respiratory-note count;
- other-note count.

These are metadata-only features; no note text is used in the documentation-behavior block.

The audit identified 80,394 eligible bedside-note rows in the 12-hour pre-landmark windows across the deduplicated corrected ICU-stay frame.

## Collapsed note categories

For source-system auditing:

- Nursing and Nursing/other -> nursing;
- Physician and Consult -> physician;
- Respiratory -> respiratory;
- General and remaining eligible categories -> other.

This collapse did **not** sufficiently neutralize source-system information.

## ICU-death source-proxy gate

CareVue versus MetaVision was predicted without mortality labels.

- documentation behavior + note context source-prediction AUROC: **0.9597**;
- current core structured + documentation comparator source-prediction AUROC: **0.9888**;
- preregistration block threshold: **0.80**.

Therefore:

**The pooled all-source ICU-death rich comparator is blocked from registration in its current form.**

This is a source-system confounding diagnostic, not a mortality prediction result.

The source-system strategy must be revised and frozen before:

- ICU-death CV splits are frozen;
- the ICU-death power grid is finalized;
- any ICU-death predictive result is run.

## Code status

Both prespecified MIMIC-III code-status dictionary items were present:

- CareVue 128 — Code Status;
- MetaVision 223758 — Code Status.

The exact value mapping and pre-landmark availability remain to be frozen through the treatment-context availability audit.

## Treatment/support dictionary discovery

The R3 dictionary scan identified candidate mappings for:

- FiO2/oxygen fraction;
- oxygen flow;
- oxygen-delivery/NIV device fields;
- vasopressors;
- sedative/analgesic exposures;
- arterial-line/device context;
- code status.

These are **discovery candidates, not frozen predictors**.

In particular:

- free-text/CHARTEVENTS medication labels are not automatically accepted as infusion exposures;
- canonical INPUTEVENTS mappings are preferred for vasoactive and sedative treatment;
- invasive ventilation endpoint-defining fields remain excluded from ventilation predictors;
- device-driven streams are treatment/device context, not documentation behavior.

## Next gate

A source-proxy decomposition is required to determine whether the confirmatory death analysis should be:

1. MetaVision-only, with CareVue as prespecified replication/sensitivity; or
2. source-stratified with separate CareVue and MetaVision models and a prespecified endpoint-level combination rule.

No choice will be based on mortality-model performance.
