#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

PYTHONPATH=src .venv/bin/python -m unittest tests.test_v2_1_integrity -v

.venv/bin/python -m py_compile \
  src/104_build_corrected_landmark12_v2_1_cohorts.py \
  src/105_build_enhanced_structured_baseline_v2_1.py \
  src/106_freeze_enhanced_structured_cv_splits_v2_1.py \
  src/107_evaluate_enhanced_structured_baseline_v2_1.py \
  src/108_quarantine_pre_registration_e8.py \
  src/109_audit_preregistration_context_v2_1.py \
  src/110_simulate_preregistration_power_v2_1.py \
  src/111_benchmark_refit_bootstrap_v2_1.py \
  src/112_audit_death_source_strategy_v2_1.py \
  src/113_audit_treatment_context_availability_v2_1.py \
  src/114_build_preregistration_context_features_v2_1.py \
  src/115_build_fixed_note_corpora_v2_1.py \
  src/116_audit_hgb_thread_runtime_v2_1.py \
  src/preregistration_stats.py \
  src/registration_gate.py \
  src/v2_1_registered_inference_contract.py

bash -n scripts/require_osf_registration.sh
bash -n scripts/run_quarantine_pre_registration_e8.sh
bash -n scripts/run_preregistration_context_audit_v2_1.sh
bash -n scripts/run_preregistration_power_v2_1.sh
bash -n scripts/run_refit_bootstrap_benchmark_v2_1.sh
bash -n scripts/run_death_source_strategy_audit_v2_1.sh
bash -n scripts/run_treatment_context_availability_audit_v2_1.sh
bash -n scripts/run_build_preregistration_context_features_v2_1.sh
bash -n scripts/run_build_fixed_note_corpora_v2_1.sh

mkdir -p outputs/integrity
PYTHONPATH=src .venv/bin/python - <<'PY'
import json
from pathlib import Path
out = Path("outputs/integrity/v2_1_preregistration_synthetic_checks.json")
out.write_text(json.dumps({
    "analysis": "v2.1 preregistration synthetic/static checks",
    "status": "passed",
    "real_clinical_data_read": False,
    "real_outcome_performance_computed": False,
    "validated_sources": [
        "104_build_corrected_landmark12_v2_1_cohorts.py",
        "105_build_enhanced_structured_baseline_v2_1.py",
        "106_freeze_enhanced_structured_cv_splits_v2_1.py",
        "107_evaluate_enhanced_structured_baseline_v2_1.py",
        "108_quarantine_pre_registration_e8.py",
        "109_audit_preregistration_context_v2_1.py",
        "110_simulate_preregistration_power_v2_1.py",
        "111_benchmark_refit_bootstrap_v2_1.py",
        "112_audit_death_source_strategy_v2_1.py",
        "113_audit_treatment_context_availability_v2_1.py",
        "114_build_preregistration_context_features_v2_1.py",
        "115_build_fixed_note_corpora_v2_1.py",
        "116_audit_hgb_thread_runtime_v2_1.py",
        "v2_1_registered_inference_contract.py"
    ],
    "registration_gate_expected_state": "locked_until_osf_approved_doi_hash_verified_and_verbatim_form_imported"
}, indent=2) + "\n", encoding="utf-8")
print(out.read_text())
PY

bash -n scripts/run_refit_bootstrap_benchmark_v2_1_ventilation.sh
bash -n scripts/run_refit_bootstrap_benchmark_v2_1_rrt.sh
bash -n scripts/run_refit_bootstrap_benchmark_v2_1_death.sh
bash -n scripts/run_hgb_thread_runtime_audit_v2_1.sh

bash -n scripts/set_hgb_thread_env_v2_1.sh
