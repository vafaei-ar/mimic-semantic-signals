#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

for outcome in invasive_ventilation renal_replacement_therapy icu_death; do
  echo "=== Laya zero-shot: $outcome ==="
  .venv/bin/python src/37_run_laya_real_local.py \
    --cases "data/real_mimic_local/multitask_benchmark_v1/$outcome/cases.jsonl" \
    --output "data/real_mimic_local/multitask_benchmark_v1/$outcome/laya_raw.jsonl" \
    --device cuda
done
