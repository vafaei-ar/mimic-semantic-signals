#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
.venv/bin/python src/45_evaluate_transport_missingness_sensitivity.py \
  --mimic-features outputs/external_validation/mimic_exact6h_structured_riskset_features.csv \
  --eicu-features outputs/external_validation/eicu_structured_riskset_features.csv \
  --nwicu-features outputs/external_validation/nwicu_structured_riskset_features.csv \
  --reference-report outputs/external_validation/structured_transport_report.json \
  --output outputs/external_validation/structured_transport_values_only_sensitivity.json \
  --folds 5 \
  --repeats 10 \
  --bootstrap-replicates 2000
