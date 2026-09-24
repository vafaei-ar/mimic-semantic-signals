#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

BASE="data/real_mimic_local/multitask_tuning_v1"
CKPT="data/local_models/postfreeze_tuned/openjev_deberta_multitask_v1/best_model.pt"
OUT="outputs/multitask_benchmark/supervised_text_encoder_learning_diagnostic_v1.json"

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONPATH=src .venv/bin/python src/73_diagnose_supervised_text_encoder_learning.py   --base "$BASE"   --checkpoint "$CKPT"   --output "$OUT"   --seed 20260924
