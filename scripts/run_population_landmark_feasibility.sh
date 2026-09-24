#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

OUT="outputs/multitask_benchmark/population_landmark_feasibility_v1.json"

PYTHONPATH=src .venv/bin/python src/91_audit_population_landmark_feasibility.py \
  --root "$HOME/datasets/MIMIC/physionet.org/files" \
  --output "$OUT" \
  --washout-hours 6 \
  --horizon-hours 12 \
  --note-lookback-hours 12
