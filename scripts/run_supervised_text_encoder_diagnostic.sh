#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONPATH=src .venv/bin/python src/72_diagnose_supervised_text_encoder.py
