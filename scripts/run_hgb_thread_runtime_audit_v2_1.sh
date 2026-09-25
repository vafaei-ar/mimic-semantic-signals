#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
mkdir -p outputs/integrity
PYTHONPATH=src .venv/bin/python src/116_audit_hgb_thread_runtime_v2_1.py   --output outputs/integrity/v2_1_hgb_thread_runtime_audit.json
