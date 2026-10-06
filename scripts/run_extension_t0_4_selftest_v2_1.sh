#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
PYTHONPATH=src .venv/bin/python src/177_evaluate_extension_t0_4_support_timing_v2_1.py --self-test
