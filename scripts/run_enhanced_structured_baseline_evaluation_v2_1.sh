#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

PYTHONPATH=src .venv/bin/python src/107_evaluate_enhanced_structured_baseline_v2_1.py   --base "data/real_mimic_local/population_landmark12_v2_1"   --split-manifest "outputs/multitask_benchmark/enhanced_structured_cv_splits_v2_1.json"   --output "outputs/multitask_benchmark/enhanced_structured_baseline_evaluation_v2_1.json"   --bootstrap-replicates 1000
