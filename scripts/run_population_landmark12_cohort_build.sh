#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

LOCAL_ROOT="data/real_mimic_local/population_landmark12_v1"
MANIFEST="outputs/multitask_benchmark/population_landmark12_cohort_manifest_v1.json"

PYTHONPATH=src .venv/bin/python src/92_build_population_landmark12_cohorts.py \
  --root "$HOME/datasets/MIMIC/physionet.org/files" \
  --local-output-root "$LOCAL_ROOT" \
  --manifest "$MANIFEST"
