#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

TOTAL=36117
BASE="data/real_mimic_local/population_landmark12_v1/semantic_unique_notes_v1"
CASES="$BASE/cases.jsonl"
RAW="$BASE/laya_raw.jsonl"
REPORT="outputs/multitask_benchmark/population_landmark12_laya_inference_v1.json"

test -f "$CASES"

.venv/bin/python src/37_run_laya_real_local.py \
  --cases "$CASES" \
  --output "$RAW" \
  --device cuda \
  --chunk-tokens 600 \
  --chunk-overlap 100 \
  --max-chunks 8 \
  --progress-offset 0 \
  --progress-total "$TOTAL" \
  --progress-phase laya_population_landmark12

.venv/bin/python src/96_summarize_population_semantic_inference.py \
  --raw "$RAW" \
  --expected "$TOTAL" \
  --model laya \
  --output "$REPORT"
