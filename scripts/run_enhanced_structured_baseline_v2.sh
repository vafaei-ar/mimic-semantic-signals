#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

PYTHONPATH=src .venv/bin/python src/102_build_enhanced_structured_baseline_v2.py   --root "$HOME/datasets/MIMIC/physionet.org/files"   --local-root "data/real_mimic_local/population_landmark12_v2"   --manifest "outputs/multitask_benchmark/enhanced_structured_baseline_features_v2.json"
