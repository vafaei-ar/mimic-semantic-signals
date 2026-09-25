#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

PYTHONPATH=src .venv/bin/python src/108_quarantine_pre_registration_e8.py   --report "outputs/integrity/e8_pre_registration_quarantine.json"
