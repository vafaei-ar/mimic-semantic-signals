# v2.1 patient-grouped CV split result freeze

Updated: 2026-09-25

## Status

**Frozen before any v2.1 predictive performance.**

Canonical RunRelay job:

- job: `T9R6M4N2 — Freeze v2.1 CV Splits`;
- project commit: `2d74f4d6c327dc1ec7698db98c3d67258e033bb0`;
- task: `freeze_enhanced_structured_cv_splits_v2_1`;
- status: completed;
- exit code: 0;
- runtime: 62.409 seconds;
- aggregate artifact: `outputs/multitask_benchmark/enhanced_structured_cv_splits_v2_1.json`;
- artifact SHA-256: `b0bac28207ca07dec3539512eda856d2ead09ab8f7f704cfe8a4d6d800e27484`.

No predictive model was fit or scored.

## Design

- 5 repeats;
- 5 folds per repeat;
- patient-grouped splitting;
- deterministic seeds: 20260924, 20260925, 20260926, 20260927, 20260928;
- repeat 1 is the primary fold partition for the decisive patient-cluster refit bootstrap;
- repeats 2–5 are prespecified split-stability analyses.

## Frozen split hashes

| Analysis | Source | Rows | Cases | Patients | Local split SHA-256 |
| --- | --- | ---: | ---: | ---: | --- |
| Invasive ventilation | MetaVision | 11,116 | 279 | 8,982 | `30d6d4e591bfe3ff0dc736d8619dcead94f1c3880b160dbfed7efbffce727b35` |
| RRT | MetaVision | 19,395 | 314 | 15,080 | `1a2b8e23045ac79429bcb65b6ff3c382226be1fbab5a9460f2d8c1ca49bb5ee0` |
| ICU death | MetaVision | 19,811 | 214 | 15,312 | `444a0dac02358d1d4eafe83b96d3804df30134de00e4b54509beb7bbbe411658` |
| ICU death replication | CareVue | 25,632 | 306 | 19,736 | `490c70902518a9620a9f3c0808f2275f56652e423e8820c78a8fa4d7dca30a2f` |

## Case balance

Across all five repeats:

- ventilation folds contain 55–56 cases each;
- RRT folds contain 62–63 cases each;
- MetaVision death folds contain 42–43 cases each;
- CareVue death folds contain 61–62 cases each.

The aggregate artifact records the exact row and case count for every fold in every repeat.

## Guardrails

- split files remain local protected row-level analysis files;
- existing split files are not overwritten unless the deterministic assignment is identical;
- confirmatory death is MetaVision-only;
- CareVue death uses a separate split and remains replication/sensitivity;
- no result-driven resplitting is permitted after registration.
