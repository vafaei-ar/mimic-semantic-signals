#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

TOTAL=36117
BASE="data/real_mimic_local/population_landmark12_v1/semantic_unique_notes_v1"
CASES="$BASE/cases.jsonl"
RAW="$BASE/open_jev_raw.jsonl"
REPORT="outputs/multitask_benchmark/population_landmark12_openjev_inference_v1.json"

test -f "$CASES"

.venv/bin/python src/22_run_open_jev_real_local.py \
  --cases "$CASES" \
  --output "$RAW" \
  --device cuda \
  --chunk-tokens 220 \
  --chunk-overlap 40 \
  --max-chunks 8 \
  --progress-offset 0 \
  --progress-total "$TOTAL" \
  --progress-phase openjev_population_landmark12

.venv/bin/python src/96_summarize_population_semantic_inference.py \
  --raw "$RAW" \
  --expected "$TOTAL" \
  --model open_jev \
  --output "$REPORT"
