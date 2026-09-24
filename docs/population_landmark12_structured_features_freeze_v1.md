# Population landmark structured-feature freeze v1

Canonical RunRelay job: `V4M7R2Q8`

- exact commit: `b52c58d2de43d7a29884ca1dcb16f3c8e4731aa6`
- task: `build_population_landmark12_structured`
- artifact: `outputs/multitask_benchmark/population_landmark12_structured_features_v1.json`
- artifact SHA-256: `74a5a75ae8e371c9700902f6e416ffcd1ab7e02ee888216c942fe23ccdec3c3b`
- exit code: 0

All frozen population cohorts were processed successfully with the same 11 structured variables used in the matched benchmark.

Aggregate missingness:

- invasive ventilation: 17.23% overall; 4.09% among cases
- RRT: 11.55% overall; 2.91% among cases
- ICU death: 11.46% overall; 7.11% among cases

Only 305–307 rows per outcome have all 11 features missing.

The low case missingness relative to controls is itself part of the observed data-generating process and is retained through training-fold imputation plus explicit missingness indicators. No complete-case restriction is permitted.

No predictive performance was examined before this freeze.
