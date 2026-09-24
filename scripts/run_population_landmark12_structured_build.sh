#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

LOCAL_ROOT="data/real_mimic_local/population_landmark12_v1"
OUT="outputs/multitask_benchmark/population_landmark12_structured_features_v1.json"

PYTHONPATH=src .venv/bin/python src/93_build_population_landmark12_structured.py \
  --root "$HOME/datasets/MIMIC/physionet.org/files" \
  --local-root "$LOCAL_ROOT" \
  --manifest "$OUT" \
  --vital-lookback-hours 6 \
  --lab-lookback-hours 24
