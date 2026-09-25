# v2.1 preregistration power/MDE planning result

Updated: 2026-09-25

## Status

**Frozen planning calculation; not a predictive result.**

Canonical RunRelay job:

- job: `V9R6M4N2 — Simulate v2.1 Power Grid`;
- project commit: `2d74f4d6c327dc1ec7698db98c3d67258e033bb0`;
- task: `simulate_preregistration_power_v2_1`;
- status: completed;
- exit code: 0;
- runtime: 1.764 seconds;
- artifact: `outputs/multitask_benchmark/preregistration_power_v2_1.json`;
- artifact SHA-256: `2dcc4c23fc222f5db6aa123cfd2b33e96278ce46ae4e478adacaefb9f89ee08a`.

No v2.1 predictions or real-label model performance were used.

## Inputs and method

Inputs:

- frozen confirmatory case/control counts;
- exact note-available case/control counts;
- v1 structured AUROCs used only as planning anchors:
  - ventilation 0.707;
  - RRT 0.948;
  - ICU death 0.793.

The death planning anchor comes from known v1 work and is not a MetaVision-specific v2.1 estimate.

Method:

- Hanley–McNeil AUC variance approximation;
- assumed paired-prediction correlations 0.80, 0.90, 0.95;
- one-sided normal approximation;
- alpha 0.05 and Holm first-step alpha 0.05/3;
- target power 80% and 90%.

This is a planning calculation only. It is **not** the primary inferential method.

## Key 80% MDEs at Holm first-step alpha

### Full confirmatory cohorts

| Outcome | rho=0.80 | rho=0.90 | rho=0.95 |
| --- | ---: | ---: | ---: |
| Ventilation | 0.0328 | 0.0233 | 0.0165 |
| RRT | 0.0156 | 0.0113 | 0.0081 |
| ICU death | 0.0338 | 0.0241 | 0.0172 |

### Note-available conditional samples

| Outcome | Note cases | rho=0.80 | rho=0.90 | rho=0.95 |
| --- | ---: | ---: | ---: | ---: |
| Ventilation | 135 | 0.0469 | 0.0334 | 0.0237 |
| RRT | 143 | 0.0232 | 0.0170 | 0.0123 |
| ICU death | 83 | 0.0536 | 0.0385 | 0.0275 |

## Prespecified interpretation

The planning grid does **not** justify changing the confirmatory estimand after results are seen.

It does establish the following before performance:

1. the full-cohort outcome-specific Open-Jev contrasts remain the confirmatory analyses;
2. effect estimates and their refit-bootstrap intervals are scientifically important even when Holm-adjusted significance is not reached;
3. ventilation and ICU-death effects in the range previously seen in exploratory v1 work may be difficult to detect unless paired model predictions are highly correlated;
4. note-available-only analyses are prespecified secondary/descriptive analyses, not alternative confirmatory rescue analyses;
5. null or imprecise results must not be interpreted as evidence that the true incremental effect is exactly zero.

No pooled cross-outcome primary estimand is introduced post hoc to recover power.
