#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
mkdir -p outputs/multitask_benchmark
.venv/bin/python src/58_evaluate_multitask_structured_ablations.py --base data/real_mimic_local/multitask_benchmark_v1 --output outputs/multitask_benchmark/structured_ablation_report_v1.json --folds 5 --repeats 20 --bootstrap-replicates 2000
