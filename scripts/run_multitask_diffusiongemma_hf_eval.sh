#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

BASE="data/real_mimic_local/multitask_benchmark_v1"
OUT="outputs/multitask_benchmark/diffusiongemma_hf_semantic_report_v1.json"

for outcome in invasive_ventilation renal_replacement_therapy icu_death; do
  test -f "$BASE/$outcome/diffusiongemma_hf_raw.jsonl"
  test -f "$BASE/$outcome/structured_features.csv"
done

.venv/bin/python src/67_evaluate_multitask_diffusiongemma_hf.py \
  --base "$BASE" \
  --output "$OUT" \
  --folds 5 \
  --repeats 20 \
  --bootstrap-replicates 2000 \
  --seed 20260923
