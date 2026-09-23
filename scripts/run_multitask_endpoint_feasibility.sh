#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
mkdir -p outputs/multitask_feasibility
.venv/bin/python src/51_audit_multitask_endpoints.py \
  --root "$HOME/datasets/MIMIC/physionet.org/files" \
  --output outputs/multitask_feasibility/endpoint_feasibility_report.json \
  --washout-hours 6
