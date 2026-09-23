#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
mkdir -p outputs/multitask_feasibility
.venv/bin/python src/53_refine_rrt_endpoint.py \
  --root "$HOME/datasets/MIMIC/physionet.org/files" \
  --output outputs/multitask_feasibility/rrt_endpoint_refinement.json \
  --washout-hours 6
