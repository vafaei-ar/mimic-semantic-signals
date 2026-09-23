#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
mkdir -p outputs/multitask_benchmark
.venv/bin/python src/60_evaluate_multitask_sampling_calibration.py --base data/real_mimic_local/multitask_benchmark_v1 --output outputs/multitask_benchmark/sampling_calibration_report_v1.json --folds 5 --repeats 10
