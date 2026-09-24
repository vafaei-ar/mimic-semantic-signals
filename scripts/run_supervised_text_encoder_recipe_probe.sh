#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

BASE="data/real_mimic_local/multitask_tuning_v1"
OUT="outputs/multitask_benchmark/supervised_text_encoder_recipe_probe_v1.json"

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONPATH=src .venv/bin/python src/74_probe_supervised_text_encoder_recipe.py   --base "$BASE"   --output "$OUT"   --seed 20260924
