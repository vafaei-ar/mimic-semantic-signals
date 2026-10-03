#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

bash scripts/require_osf_registration.sh

MIMIC_BASE="data/real_mimic_local/population_landmark12_v2_1"
ZIGONG_BASE="data/real_zigong_local/ventilation24_v1"

PYTHONPATH=src .venv/bin/python src/158_evaluate_h9_zigong_diffusiongemma_transport_v2_1.py \
  --mimic-base "$MIMIC_BASE" \
  --analysis-populations config/v2_1_analysis_population_contract.json \
  --mimic-dg "$MIMIC_BASE/invasive_ventilation/diffusiongemma_registered_v2_1_raw_local.jsonl" \
  --zigong-cases "$ZIGONG_BASE/cases.jsonl" \
  --zigong-dg "$ZIGONG_BASE/diffusiongemma_raw.jsonl" \
  --zigong-inference-report outputs/zigong_external/diffusiongemma_inference_report_v1.json \
  --output outputs/zigong_external/h9_diffusiongemma_external_transport_v2_1.json \
  --bootstrap-replicates 2000 \
  --seed 20260924
