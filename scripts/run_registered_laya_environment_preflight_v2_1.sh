#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
PYTHONPATH=src .venv/bin/python src/130_audit_registered_laya_environment_v2_1.py   --output "outputs/integrity/v2_1_registered_laya_environment_preflight.json"
