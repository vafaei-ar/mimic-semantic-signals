#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

PYTHONPATH=src .venv/bin/python src/109_audit_preregistration_context_v2_1.py   --root "$HOME/datasets/MIMIC/physionet.org/files"   --local-root "data/real_mimic_local/population_landmark12_v2_1"   --output "outputs/multitask_benchmark/preregistration_context_audit_v2_1.json"
