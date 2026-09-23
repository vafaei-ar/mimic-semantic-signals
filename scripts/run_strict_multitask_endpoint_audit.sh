#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
mkdir -p outputs/multitask_feasibility
.venv/bin/python src/52_audit_strict_multitask_endpoints.py \
  --root "$HOME/datasets/MIMIC/physionet.org/files" \
  --output outputs/multitask_feasibility/strict_endpoint_audit.json \
  --washout-hours 6
