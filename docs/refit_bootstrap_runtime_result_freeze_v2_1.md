# Exact refit-bootstrap runtime benchmark freeze v2.1

Updated: 2026-09-25

## Status

**Frozen before v2.1 predictive performance and before OSF registration.**

The initial combined benchmark `W9R6M4N2` failed by timeout after 14,401.6 seconds while still in the ventilation stage and produced no artifact. It combined exact full-size model refitting with repeated null-model refits and is superseded for runtime estimation.

The redesigned benchmark was validated by `X4R7M2Q8` and executed as:

- job: `Y5R7M2Q8 — Benchmark Vent Refit Runtime`;
- project commit: `4d39e8400722f8611a4d04a528125c29251a91e6`;
- task: `benchmark_refit_bootstrap_v2_1_ventilation`;
- status: completed;
- exit code: 0;
- runtime: 5,472.465 seconds;
- artifact: `outputs/multitask_benchmark/refit_bootstrap_benchmark_v2_1_ventilation.json`;
- artifact SHA-256: `7a2e2aadf5b26f8abe49b71f1e77a4a61d5cb9cd79568c56370121a309d422fe`.

No real predictors or real outcome labels were used.

## Exact runtime result

One full-size synthetic ventilation patient-cluster refit-bootstrap replicate, using the frozen five-fold HGB comparison, required:

- total: **5,470.3 seconds** (~91.2 minutes);
- fold 1: 1,088.7 s;
- fold 2: 1,108.5 s;
- fold 3: 1,080.6 s;
- fold 4: 1,106.4 s;
- fold 5: 1,085.0 s.

At that rate, 500 serial replicates would require approximately **759.8 hours for ventilation alone**. Ventilation is the smallest of the three confirmatory cohorts, so this is sufficient to establish that the planned 500-replicate exact refit bootstrap is not operationally realistic on the bound workstation with the frozen HGB model.

## Null-calibration check

The redesigned benchmark separated exact fitting runtime from cheap statistical calibration of the previously proposed centered-bootstrap p-value rule.

Across 2,000 synthetic null trials with 500 cheap bootstrap draws per trial:

- mean p-value: 0.4985;
- median p-value: 0.4900;
- rejection rate at alpha 0.05: 0.0520;
- rejection rate at 0.05/3: 0.0155;
- minimum p-value: 0.001996.

This confirms the formula itself behaved as intended under the synthetic null. It does **not** solve the computational infeasibility of exact model refitting.

## Preregistration consequence

The original 500-refit inferential plan was amended **before OSF registration and before any v2.1 predictive performance was examined**.

The replacement primary inference is frozen in:

- `config/v2_1_primary_inference_freeze.json`.

The original plan remains in:

- `config/v2_1_refit_bootstrap_inference_freeze.json`

with status `superseded_before_registration`.

The replacement is estimation-first: repeat-1 out-of-fold delta-AUROC with a 5,000-replicate patient-cluster bootstrap of the paired frozen predictions, plus repeats 2–5 as explicit refit/split-stability estimates. No confirmatory p-values or Holm decision rule are used.
