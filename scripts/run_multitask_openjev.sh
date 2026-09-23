#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

for outcome in invasive_ventilation renal_replacement_therapy icu_death; do
  echo "=== Open-Jev zero-shot: $outcome ==="
  .venv/bin/python src/22_run_open_jev_real_local.py \
    --cases "data/real_mimic_local/multitask_benchmark_v1/$outcome/cases.jsonl" \
    --output "data/real_mimic_local/multitask_benchmark_v1/$outcome/open_jev_raw.jsonl" \
    --device cuda
done
