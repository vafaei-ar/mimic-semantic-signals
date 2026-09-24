#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

BASE="data/real_mimic_local/multitask_benchmark_v1"
OUT="outputs/multitask_benchmark/diffusiongemma_lexical_report_v1.json"

for outcome in invasive_ventilation renal_replacement_therapy icu_death; do
  test -f "$BASE/$outcome/cases.jsonl"
  test -f "$BASE/$outcome/structured_features.csv"
  test -f "$BASE/$outcome/diffusiongemma_hf_raw.jsonl"
done

.venv/bin/python src/68_evaluate_multitask_diffusiongemma_lexical.py \
  --base "$BASE" \
  --output "$OUT" \
  --folds 5 \
  --repeats 10 \
  --bootstrap-replicates 2000 \
  --max-features 10000 \
  --seed 20260921
