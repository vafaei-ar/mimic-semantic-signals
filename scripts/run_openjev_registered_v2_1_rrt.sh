#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

bash scripts/require_osf_registration.sh

BASE="data/real_mimic_local/population_landmark12_v2_1/renal_replacement_therapy"
CASES="$BASE/fixed_notes_stripped_v2_1_local.jsonl"
RAW="$BASE/openjev_registered_v2_1_raw_local.jsonl"
REPORT="outputs/multitask_benchmark/openjev_registered_v2_1_rrt.json"

PYTHONPATH=src .venv/bin/python src/118_run_registered_openjev_v2_1.py \
  --cases "$CASES" \
  --output "$RAW" \
  --expected 7709 \
  --device cuda \
  --questions-per-pack 4 \
  --progress-phase v2_1_openjev_rrt

PYTHONPATH=src .venv/bin/python src/96_summarize_population_semantic_inference.py \
  --raw "$RAW" \
  --expected 7709 \
  --model open_jev_registered_v2_1 \
  --output "$REPORT"
