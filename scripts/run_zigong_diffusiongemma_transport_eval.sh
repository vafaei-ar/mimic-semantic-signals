#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

MIMIC_BASE="data/real_mimic_local/multitask_benchmark_v1/invasive_ventilation"
ZIGONG_BASE="data/real_zigong_local/ventilation24_v1"
OUT="outputs/zigong_external/diffusiongemma_external_transport_v1.json"

test -f "$MIMIC_BASE/structured_features.csv"
test -f "$MIMIC_BASE/diffusiongemma_hf_raw.jsonl"
test -f "$ZIGONG_BASE/cases.jsonl"
test -f "$ZIGONG_BASE/diffusiongemma_raw.jsonl"

PYTHONPATH=src .venv/bin/python src/90_evaluate_zigong_diffusiongemma_transport.py \
  --mimic-features "$MIMIC_BASE/structured_features.csv" \
  --mimic-dg "$MIMIC_BASE/diffusiongemma_hf_raw.jsonl" \
  --zigong-cases "$ZIGONG_BASE/cases.jsonl" \
  --zigong-dg "$ZIGONG_BASE/diffusiongemma_raw.jsonl" \
  --output "$OUT" \
  --bootstrap-replicates 2000 \
  --seed 20260924
