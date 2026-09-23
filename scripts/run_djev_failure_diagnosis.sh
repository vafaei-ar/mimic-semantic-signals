#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
mkdir -p outputs/multitask_benchmark
.venv/bin/python src/62_diagnose_failed_djev_setup.py --output outputs/multitask_benchmark/djev_failure_diagnosis.json
