#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

PYTHONPATH=src .venv/bin/python src/103_evaluate_enhanced_structured_baseline_v2.py   --base "data/real_mimic_local/population_landmark12_v2"   --output "outputs/multitask_benchmark/enhanced_structured_baseline_evaluation_v2.json"   --folds 5   --bootstrap-replicates 1000
