#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

BASE=data/real_mimic_local/multitask_benchmark_v1
OUT=outputs/multitask_benchmark/lexical
mkdir -p "$OUT"

for outcome in invasive_ventilation renal_replacement_therapy icu_death; do
  mkdir -p "$OUT/$outcome"
  .venv/bin/python src/43_evaluate_lexical_robustness.py \
    --features "$BASE/$outcome/structured_features.csv" \
    --cases "$BASE/$outcome/cases.jsonl" \
    --openjev "$BASE/$outcome/open_jev_raw.jsonl" \
    --laya "$BASE/$outcome/laya_raw.jsonl" \
    --output "$OUT/$outcome/report.json" \
    --folds 5 \
    --repeats 10 \
    --bootstrap-replicates 2000 \
    --max-features 10000
done

.venv/bin/python src/56_summarize_multitask_lexical.py \
  --input-root "$OUT" \
  --output outputs/multitask_benchmark/lexical_report_v1.json
