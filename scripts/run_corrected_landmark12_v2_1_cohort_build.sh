#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

PYTHONPATH=src .venv/bin/python src/104_build_corrected_landmark12_v2_1_cohorts.py   --root "$HOME/datasets/MIMIC/physionet.org/files"   --local-output-root "data/real_mimic_local/population_landmark12_v2_1"   --manifest "outputs/multitask_benchmark/population_landmark12_cohort_manifest_v2_1.json"
