#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
mkdir -p outputs/multitask_benchmark
.venv/bin/python src/57_audit_local_djev_readiness.py \
  --output outputs/multitask_benchmark/local_djev_readiness.json
