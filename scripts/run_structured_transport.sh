#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

.venv/bin/python src/42_evaluate_structured_transport.py \
  --mimic-features outputs/external_validation/mimic_exact6h_structured_riskset_features.csv \
  --eicu-features outputs/external_validation/eicu_structured_riskset_features.csv \
  --nwicu-features outputs/external_validation/nwicu_structured_riskset_features.csv \
  --output outputs/external_validation/structured_transport_report.json \
  --folds 5 \
  --repeats 10 \
  --bootstrap-replicates 2000
