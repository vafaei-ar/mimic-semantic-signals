#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
mkdir -p outputs/multitask_benchmark
.venv/bin/python src/61_evaluate_multitask_djev.py --base data/real_mimic_local/multitask_benchmark_v1 --output outputs/multitask_benchmark/djev_semantic_report_v1.json --folds 5 --repeats 20 --bootstrap-replicates 2000
