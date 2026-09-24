#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

ROOT="$HOME/datasets/MIMIC/physionet.org/files"
LOCAL_OUT="data/real_mimic_local/multitask_tuning_v1"
MANIFEST="outputs/multitask_benchmark/tuning_cohort_manifest_v1.json"

PYTHONPATH=src .venv/bin/python src/70_build_multitask_tuning_cohorts.py \
  --root "$ROOT" \
  --local-output-root "$LOCAL_OUT" \
  --manifest "$MANIFEST" \
  --controls-per-case 3 \
  --split-seed 20260924 \
  --matching-seed 20260924 \
  --washout-hours 6 \
  --vital-lookback-hours 6 \
  --lab-lookback-hours 24
