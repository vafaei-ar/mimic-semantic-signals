#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
mkdir -p outputs/multitask_benchmark
mkdir -p data/real_mimic_local/multitask_benchmark_v1
.venv/bin/python src/54_build_multitask_benchmark.py \
  --root "$HOME/datasets/MIMIC/physionet.org/files" \
  --local-output-root data/real_mimic_local/multitask_benchmark_v1 \
  --manifest outputs/multitask_benchmark/cohort_manifest_v1.json \
  --controls-per-case 3 \
  --washout-hours 6 \
  --vital-lookback-hours 6 \
  --lab-lookback-hours 24
