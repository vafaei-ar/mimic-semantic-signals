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
  src/117_evaluate_rich_comparator_v2_1.py \
  src/118_run_registered_openjev_v2_1.py \
  src/119_audit_registered_openjev_environment_v2_1.py \
  src/120_evaluate_h1_ventilation_openjev_v2_1.py \
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
        "117_evaluate_rich_comparator_v2_1.py",
        "118_run_registered_openjev_v2_1.py",
        "119_audit_registered_openjev_environment_v2_1.py",
        "120_evaluate_h1_ventilation_openjev_v2_1.py",
        "139_audit_h6_broad_ventilation_inputs_v2_1.py",
        "140_prepare_h6_broad_ventilation_v2_1.py",
        "141_evaluate_h6_broad_ventilation_v2_1.py",
        "142_prepare_h6_chartevents_storetime_v2_1.py",
        "143_evaluate_h6_chartevents_storetime_ventilation_v2_1.py",
        "144_evaluate_h6_chartevents_storetime_rrt_v2_1.py",
        "145_evaluate_h6_chartevents_storetime_death_v2_1.py",
        "146_prepare_h6_lab_lag_v2_1.py",
        "147_evaluate_h6_lab_lag_1h_ventilation_v2_1.py",
        "148_evaluate_h6_lab_lag_1h_rrt_v2_1.py",
        "149_evaluate_h6_lab_lag_1h_death_v2_1.py",
        "150_evaluate_h6_lab_lag_2h_ventilation_v2_1.py",
        "151_evaluate_h6_lab_lag_2h_rrt_v2_1.py",
        "152_evaluate_h6_lab_lag_2h_death_v2_1.py",
        "153_audit_h6_note_availability_v2_1.py",
        "154_evaluate_h6_carevue_death_openjev_v2_1.py",
        "155_evaluate_h7_patient_shuffled_openjev_v2_1.py",
        "156_prepare_h8_clinician_validation_v2_1.py",
        "157_evaluate_h8_clinician_validation_v2_1.py",
        "158_evaluate_h9_zigong_diffusiongemma_transport_v2_1.py",
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
bash -n scripts/run_rich_comparator_evaluation_v2_1_ventilation.sh
bash -n scripts/run_rich_comparator_evaluation_v2_1_rrt.sh
bash -n scripts/run_rich_comparator_evaluation_v2_1_death.sh
bash -n scripts/run_openjev_registered_v2_1_ventilation.sh
bash -n scripts/run_openjev_registered_v2_1_rrt.sh
bash -n scripts/run_openjev_registered_v2_1_death.sh
bash -n scripts/run_registered_openjev_environment_preflight_v2_1.sh
bash -n scripts/run_h1_openjev_v2_1_ventilation.sh
bash -n scripts/run_h2_openjev_v2_1_rrt.sh
bash -n scripts/run_h3_openjev_v2_1_death.sh
bash -n scripts/run_h4_six_construct_v2_1_ventilation.sh
bash -n scripts/run_h4_six_construct_v2_1_death.sh
bash -n scripts/run_h5_lexical_v2_1_ventilation.sh
bash -n scripts/run_h5_lexical_v2_1_death.sh
bash -n scripts/run_h5_lexical_v2_1_rrt.sh
bash -n scripts/run_h4_six_construct_v2_1_rrt.sh

bash -n scripts/set_hgb_thread_env_v2_1.sh

.venv/bin/python -m py_compile src/127_evaluate_h6_unstripped_ventilation_v2_1.py
bash -n scripts/run_h6_unstripped_openjev_inference_v2_1_ventilation.sh
bash -n scripts/run_h6_unstripped_openjev_eval_v2_1_ventilation.sh
.venv/bin/python -m py_compile src/128_evaluate_h6_unstripped_rrt_v2_1.py
.venv/bin/python -m py_compile src/129_evaluate_h6_unstripped_death_v2_1.py
bash -n scripts/run_h6_unstripped_openjev_inference_v2_1_rrt.sh
bash -n scripts/run_h6_unstripped_openjev_eval_v2_1_rrt.sh
bash -n scripts/run_h6_unstripped_openjev_inference_v2_1_death.sh
bash -n scripts/run_h6_unstripped_openjev_eval_v2_1_death.sh
.venv/bin/python -m py_compile src/130_audit_registered_laya_environment_v2_1.py
.venv/bin/python -m py_compile src/131_evaluate_h6_laya_ventilation_v2_1.py
.venv/bin/python -m py_compile src/132_evaluate_h6_laya_rrt_v2_1.py
.venv/bin/python -m py_compile src/133_evaluate_h6_laya_death_v2_1.py
bash -n scripts/run_registered_laya_environment_preflight_v2_1.sh
bash -n scripts/run_h6_laya_inference_v2_1_ventilation.sh
bash -n scripts/run_h6_laya_inference_v2_1_rrt.sh
bash -n scripts/run_h6_laya_inference_v2_1_death.sh
bash -n scripts/run_h6_laya_eval_v2_1_ventilation.sh
bash -n scripts/run_h6_laya_eval_v2_1_rrt.sh
bash -n scripts/run_h6_laya_eval_v2_1_death.sh
.venv/bin/python -m py_compile src/134_audit_registered_diffusiongemma_environment_v2_1.py
.venv/bin/python -m py_compile src/135_run_registered_diffusiongemma_v2_1.py
.venv/bin/python -m py_compile src/136_evaluate_h6_diffusiongemma_ventilation_v2_1.py
.venv/bin/python -m py_compile src/137_evaluate_h6_diffusiongemma_rrt_v2_1.py
.venv/bin/python -m py_compile src/138_evaluate_h6_diffusiongemma_death_v2_1.py
.venv/bin/python -m py_compile src/139_audit_h6_broad_ventilation_inputs_v2_1.py
.venv/bin/python -m py_compile src/140_prepare_h6_broad_ventilation_v2_1.py
.venv/bin/python -m py_compile src/141_evaluate_h6_broad_ventilation_v2_1.py
.venv/bin/python -m py_compile src/142_prepare_h6_chartevents_storetime_v2_1.py
.venv/bin/python -m py_compile src/143_evaluate_h6_chartevents_storetime_ventilation_v2_1.py
.venv/bin/python -m py_compile src/144_evaluate_h6_chartevents_storetime_rrt_v2_1.py
.venv/bin/python -m py_compile src/145_evaluate_h6_chartevents_storetime_death_v2_1.py
.venv/bin/python -m py_compile src/146_prepare_h6_lab_lag_v2_1.py
.venv/bin/python -m py_compile src/147_evaluate_h6_lab_lag_1h_ventilation_v2_1.py
.venv/bin/python -m py_compile src/148_evaluate_h6_lab_lag_1h_rrt_v2_1.py
.venv/bin/python -m py_compile src/149_evaluate_h6_lab_lag_1h_death_v2_1.py
.venv/bin/python -m py_compile src/150_evaluate_h6_lab_lag_2h_ventilation_v2_1.py
.venv/bin/python -m py_compile src/151_evaluate_h6_lab_lag_2h_rrt_v2_1.py
.venv/bin/python -m py_compile src/152_evaluate_h6_lab_lag_2h_death_v2_1.py
.venv/bin/python -m py_compile src/153_audit_h6_note_availability_v2_1.py
.venv/bin/python -m py_compile src/154_evaluate_h6_carevue_death_openjev_v2_1.py
.venv/bin/python -m py_compile src/155_evaluate_h7_patient_shuffled_openjev_v2_1.py
.venv/bin/python -m py_compile src/156_prepare_h8_clinician_validation_v2_1.py
.venv/bin/python -m py_compile src/157_evaluate_h8_clinician_validation_v2_1.py
.venv/bin/python -m py_compile src/158_evaluate_h9_zigong_diffusiongemma_transport_v2_1.py
PYTHONPATH=src .venv/bin/python - <<'PY'
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

p = Path("src/155_evaluate_h7_patient_shuffled_openjev_v2_1.py")
spec = importlib.util.spec_from_file_location("h7shuffle", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

if mod.SHUFFLE_SEED != 20260929:
    raise SystemExit("H7 shuffle seed changed")
if mod.RISK_DECILES != 10:
    raise SystemExit("H7 risk-decile count changed")

# Synthetic-only check: 20 patients, two patients per decile, one note row each.
subjects = np.arange(100, 120, dtype=int)
risks = np.linspace(0.01, 0.99, 20)
has_note = np.ones(20, dtype=int)
patient_deciles, _ = mod.balanced_patient_risk_deciles(subjects, risks, has_note)
sem = pd.DataFrame({
    name: np.arange(20, dtype=float) + j / 100.0
    for j, name in enumerate(mod.h1.SEMANTIC_NAMES)
})
shuf, report = mod.shuffle_semantic_vectors_between_patients(
    sem, subjects, has_note, patient_deciles
)
if report["same_patient_assignments"] != 0:
    raise SystemExit("H7 synthetic shuffle retained same-patient assignment")
if not report["marginal_semantic_values_preserved_exactly"]:
    raise SystemExit("H7 synthetic shuffle changed semantic marginals")
for name in mod.h1.SEMANTIC_NAMES:
    if not np.array_equal(np.sort(sem[name].to_numpy()), np.sort(shuf[name].to_numpy())):
        raise SystemExit(f"H7 marginal preservation failed for {name}")
PY
PYTHONPATH=src .venv/bin/python - <<'PY'
import importlib.util
import json
from pathlib import Path
import numpy as np

from semantic_schema import SEMANTIC_CONSTRUCTS

freeze = json.loads(Path("config/v2_1_h8_clinician_validation_freeze.json").read_text())
if freeze["sampling_frame"]["sample_size"] != 200:
    raise SystemExit("H8 sample size changed")
if freeze["sampling_frame"]["seed"] != 20261003:
    raise SystemExit("H8 sampling seed changed")
if freeze["raters"]["primary_rater_count"] != 3:
    raise SystemExit("H8 primary rater count changed")
if freeze["constructs"] != SEMANTIC_CONSTRUCTS:
    raise SystemExit("H8 frozen construct wording differs from semantic_schema.py")
if freeze["uncertainty"]["valid_replicates_target"] != 2000:
    raise SystemExit("H8 bootstrap target changed")

p = Path("src/157_evaluate_h8_clinician_validation_v2_1.py")
spec = importlib.util.spec_from_file_location("h8eval", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

perfect = np.array([[0.,0.,0.],[25.,25.,25.],[50.,50.,50.],[75.,75.,75.],[100.,100.,100.]])
icc21, icc23 = mod.icc2_absolute(perfect)
if not (abs(icc21 - 1.0) < 1e-12 and abs(icc23 - 1.0) < 1e-12):
    raise SystemExit(f"H8 ICC synthetic check failed: {icc21}, {icc23}")
rho = mod.safe_spearman(np.arange(10, dtype=float), np.arange(10, dtype=float))
if abs(rho - 1.0) > 1e-12:
    raise SystemExit(f"H8 Spearman synthetic check failed: {rho}")
PY
PYTHONPATH=src .venv/bin/python - <<'PY'
import importlib.util
from pathlib import Path

p = Path("src/158_evaluate_h9_zigong_diffusiongemma_transport_v2_1.py")
spec = importlib.util.spec_from_file_location("h9transport", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
if mod.OUTCOME != "invasive_ventilation":
    raise SystemExit("H9 outcome changed")
if len(mod.SEMANTIC_NAMES) != 8:
    raise SystemExit("H9 semantic construct count changed")
text = p.read_text(encoding="utf-8")
required = [
    'len(out) != 340',
    'int(out["label"].sum()) != 85',
    'n_boot: int',
    'MIMIC training uses the full registered corrected v2.1 ventilation cohort',
    'LogisticRegression(',
    'solver="liblinear"',
    'C=1.0',
    'max_iter=3000',
]
for needle in required:
    if needle not in text:
        raise SystemExit(f"H9 frozen implementation check missing: {needle}")
PY
PYTHONPATH=src .venv/bin/python - <<'PY'
import importlib.util
from pathlib import Path
p = Path("src/153_audit_h6_note_availability_v2_1.py")
spec = importlib.util.spec_from_file_location("noteavail", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
if mod.FALLBACK_QUANTILE != 0.90:
    raise SystemExit("note-availability fallback quantile is not frozen at 0.90")
if mod.SENSITIVITIES != ("storetime_only", "fallback_delay"):
    raise SystemExit("note-availability sensitivity definitions changed")
PY
PYTHONPATH=src .venv/bin/python - <<'PY'
import importlib.util
from pathlib import Path
p = Path("src/146_prepare_h6_lab_lag_v2_1.py")
spec = importlib.util.spec_from_file_location("lablagprep", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
expected = tuple(f"{name}_last" for name in mod.base_mod.LAB_IDS)
if tuple(mod.LAB_FEATURES) != expected:
    raise SystemExit(f"LAB_FEATURES mismatch: {mod.LAB_FEATURES!r} != {expected!r}")
PY
bash -n scripts/run_registered_diffusiongemma_environment_preflight_v2_1.sh
bash -n scripts/run_h6_diffusiongemma_inference_v2_1_ventilation.sh
bash -n scripts/run_h6_diffusiongemma_inference_v2_1_rrt.sh
bash -n scripts/run_h6_diffusiongemma_inference_v2_1_death.sh
bash -n scripts/run_h6_diffusiongemma_eval_v2_1_ventilation.sh
bash -n scripts/run_h6_diffusiongemma_eval_v2_1_rrt.sh
bash -n scripts/run_h6_diffusiongemma_eval_v2_1_death.sh
bash -n scripts/run_h6_broad_ventilation_input_audit_v2_1.sh
bash -n scripts/run_h6_broad_ventilation_prepare_v2_1.sh
bash -n scripts/run_h6_broad_openjev_inference_v2_1_ventilation.sh
bash -n scripts/run_h6_broad_openjev_eval_v2_1_ventilation.sh
bash -n scripts/run_h6_chartevents_storetime_prepare_v2_1.sh
bash -n scripts/run_h6_chartevents_storetime_eval_v2_1_ventilation.sh
bash -n scripts/run_h6_chartevents_storetime_eval_v2_1_rrt.sh
bash -n scripts/run_h6_chartevents_storetime_eval_v2_1_death.sh
bash -n scripts/run_h6_lab_lag_prepare_v2_1.sh
bash -n scripts/run_h6_lab_lag_1h_eval_v2_1_ventilation.sh
bash -n scripts/run_h6_lab_lag_1h_eval_v2_1_rrt.sh
bash -n scripts/run_h6_lab_lag_1h_eval_v2_1_death.sh
bash -n scripts/run_h6_lab_lag_2h_eval_v2_1_ventilation.sh
bash -n scripts/run_h6_lab_lag_2h_eval_v2_1_rrt.sh
bash -n scripts/run_h6_lab_lag_2h_eval_v2_1_death.sh
bash -n scripts/run_h6_note_availability_audit_v2_1.sh
bash -n scripts/run_h6_carevue_openjev_inference_v2_1_death.sh
bash -n scripts/run_h6_carevue_openjev_eval_v2_1_death.sh
bash -n scripts/run_h7_patient_shuffled_v2_1_ventilation.sh
bash -n scripts/run_h7_patient_shuffled_v2_1_rrt.sh
bash -n scripts/run_h7_patient_shuffled_v2_1_death_metavision.sh
bash -n scripts/run_h7_patient_shuffled_v2_1_death_carevue.sh
bash -n scripts/run_h8_clinician_validation_prepare_v2_1.sh
bash -n scripts/run_h8_clinician_validation_eval_v2_1.sh
bash -n scripts/run_h9_zigong_diffusiongemma_transport_v2_1.sh
