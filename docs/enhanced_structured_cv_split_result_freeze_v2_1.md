# v2.1 patient-grouped CV split result freeze

Updated: 2026-09-25

## Status

**Frozen before any v2.1 predictive performance is opened.**

Canonical RunRelay job:

- job: `T9R6M4N2 — Freeze v2.1 CV Splits`
- project commit: `2d74f4d6c327dc1ec7698db98c3d67258e033bb0`
- task: `freeze_enhanced_structured_cv_splits_v2_1`
- status: completed
- exit code: 0
- runtime: 62.409 seconds
- aggregate artifact: `outputs/multitask_benchmark/enhanced_structured_cv_splits_v2_1.json`
- artifact SHA-256: `b0bac28207ca07dec3539512eda856d2ead09ab8f7f704cfe8a4d6d800e27484`

No predictive model was fit or scored.

## Split design

- five patient-grouped folds per repeat;
- five frozen repeats;
- seeds: 20260924, 20260925, 20260926, 20260927, 20260928;
- grouping unit: source patient;
- row-level split files remain local;
- existing split files may be reused only when they are exactly identical to the deterministic assignment.

## Frozen split hashes

| Analysis | Source | Rows | Cases | Patients | Split SHA-256 |
| --- | --- | ---: | ---: | ---: | --- |
| Invasive ventilation | MetaVision | 11,116 | 279 | 8,982 | `30d6d4e591bfe3ff0dc736d8619dcead94f1c3880b160dbfed7efbffce727b35` |
| RRT | MetaVision | 19,395 | 314 | 15,080 | `1a2b8e23045ac79429bcb65b6ff3c382226be1fbab5a9460f2d8c1ca49bb5ee0` |
| ICU death confirmatory | MetaVision | 19,811 | 214 | 15,312 | `444a0dac02358d1d4eafe83b96d3804df30134de00e4b54509beb7bbbe411658` |
| ICU death replication | CareVue | 25,632 | 306 | 19,736 | `490c70902518a9620a9f3c0808f2275f56652e423e8820c78a8fa4d7dca30a2f` |

Every fold contains cases in every repeat. Downstream structured, semantic, lexical, and sensitivity analyses must load these exact source-specific split assignments rather than regenerate them.

## Confirmatory hierarchy

The three confirmatory outcome analyses are:

1. MetaVision ventilation;
2. MetaVision RRT;
3. MetaVision ICU death.

CareVue ICU death is a prespecified replication/sensitivity and is not a fourth member of the Holm confirmatory family.
