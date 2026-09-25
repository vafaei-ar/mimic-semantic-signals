#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

PYTHONPATH=src .venv/bin/python src/110_simulate_preregistration_power_v2_1.py   --cohort-manifest "outputs/multitask_benchmark/population_landmark12_cohort_manifest_v2_1.json"   --output "outputs/multitask_benchmark/preregistration_power_v2_1.json"
