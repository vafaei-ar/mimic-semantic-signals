#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

PYTHONPATH=src .venv/bin/python src/113_audit_treatment_context_availability_v2_1.py \
  --root "$HOME/datasets/MIMIC/physionet.org/files" \
  --local-root "data/real_mimic_local/population_landmark12_v2_1" \
  --output "outputs/multitask_benchmark/treatment_context_availability_audit_v2_1.json"
