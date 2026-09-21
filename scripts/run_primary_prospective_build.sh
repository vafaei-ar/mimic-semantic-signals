#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
mkdir -p data/real_mimic_local/vasopressor_incremental_v4_prospective
mkdir -p outputs/vasopressor_incremental_v4_prospective
.venv/bin/python src/28_build_vasopressor_incremental_pilot.py \
  --root "$HOME/datasets/MIMIC/physionet.org/files" \
  --cases-output data/real_mimic_local/vasopressor_incremental_v4_prospective/cases.jsonl \
  --features-output data/real_mimic_local/vasopressor_incremental_v4_prospective/structured_features.csv \
  --manifest outputs/vasopressor_incremental_v4_prospective/cohort_manifest.json \
  --controls-per-case 3 \
  --prediction-horizon-hours 6 \
  --vital-lookback-hours 6 \
  --lab-lookback-hours 24
