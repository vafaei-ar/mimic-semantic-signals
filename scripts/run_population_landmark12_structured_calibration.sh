#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

BASE="data/real_mimic_local/population_landmark12_v1"
OUT="outputs/multitask_benchmark/population_landmark12_structured_calibration_v1.json"

PYTHONPATH=src .venv/bin/python src/94_evaluate_population_landmark12_structured.py \
  --base "$BASE" \
  --output "$OUT" \
  --folds 5 \
  --bootstrap-replicates 1000
