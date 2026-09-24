# Enhanced structured baseline mapping addendum v2.1

Updated: 2026-09-24

This addendum modifies the v2 structured mapping only where required by the second code review.

Base mapping:

- `docs/enhanced_structured_baseline_mapping_freeze_v2.md`

Post-review gate:

- `docs/06_POSTREVIEW_V2_1_CORRECTIONS.md`

## Population restriction

The v2.1 structured feature set is evaluated only on the corrected adult cohort:

- age at ICU admission >= 18 years;
- first care unit != NICU.

Age remains capped at 90 for modeling after eligibility is determined from the uncapped ICU-admission age.

## GCS verbal correction

The item IDs are unchanged:

- CareVue verbal GCS: 723;
- MetaVision verbal GCS: 223900.

However, rows representing an artificial airway are **not** interpreted as a physiologic verbal score of 1.

Treat as missing verbal GCS when the raw text value is:

- `1.0 ET/Trach`;
- `No Response-ETT`.

These rows may not create an implicit intubation/treatment predictor inside the GCS feature.

The remaining valid verbal GCS range is 1–5.

## All other primary 34-feature mappings

All other v2 item IDs, units, validity ranges, lookback windows, and aggregation rules remain unchanged for the core physiology comparator.

Treatment/support variables are not silently added to the core 34-feature set. They will be evaluated in a separately frozen treatment-context comparator after a model-free mapping audit.
