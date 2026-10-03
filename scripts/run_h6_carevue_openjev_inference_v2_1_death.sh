#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

bash scripts/require_osf_registration.sh

BASE="data/real_mimic_local/population_landmark12_v2_1/icu_death"
CASES="$BASE/fixed_notes_stripped_v2_1_carevue_local.jsonl"
RAW="$BASE/openjev_registered_v2_1_carevue_raw_local.jsonl"
REPORT="outputs/multitask_benchmark/h6_carevue_openjev_inference_v2_1_death.json"

PYTHONPATH=src .venv/bin/python src/118_run_registered_openjev_v2_1.py \
  --cases "$CASES" \
  --output "$RAW" \
  --expected 23272 \
  --device cuda \
  --questions-per-pack 4 \
  --progress-phase v2_1_h6_carevue_openjev_inference

PYTHONPATH=src .venv/bin/python src/96_summarize_population_semantic_inference.py \
  --raw "$RAW" \
  --expected 23272 \
  --model open_jev_registered_v2_1_carevue \
  --output "$REPORT"
