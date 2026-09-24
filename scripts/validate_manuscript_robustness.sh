#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
.venv/bin/python -m py_compile \
  src/runrelay_progress.py \
  src/22_run_open_jev_real_local.py \
  src/37_run_laya_real_local.py \
  src/43_evaluate_lexical_robustness.py \
  src/44_evaluate_nonlinear_structured_robustness.py \
  src/45_evaluate_transport_missingness_sensitivity.py \
  src/46_evaluate_nonlinear_rf_robustness.py \
  src/47_evaluate_treatment_language_sensitivity.py \
  src/48_evaluate_lead_time_sensitivity.py \
  src/49_evaluate_documentation_context_sensitivity.py \
  src/50_evaluate_semantic_scores_only.py \
  src/51_audit_multitask_endpoints.py \
  src/52_audit_strict_multitask_endpoints.py \
  src/53_refine_rrt_endpoint.py \
  src/54_build_multitask_benchmark.py \
  src/55_evaluate_multitask_semantics.py \
  src/56_summarize_multitask_lexical.py \
  src/57_audit_local_djev_readiness.py \
  src/58_evaluate_multitask_structured_ablations.py \
  src/59_summarize_multitask_rf.py \
  src/60_evaluate_multitask_sampling_calibration.py \
  src/61_evaluate_multitask_djev.py \
  src/62_diagnose_failed_djev_setup.py \
  src/63_smoke_diffusiongemma_hf_native.py \
  src/64_calibrate_diffusiongemma_hf_native.py \
  src/65_pilot_diffusiongemma_hf_native_real.py \
  src/66_run_diffusiongemma_hf_native_multitask.py \
  src/67_evaluate_multitask_diffusiongemma_hf.py \
  src/68_evaluate_multitask_diffusiongemma_lexical.py \
  src/69_audit_tuning_feasibility.py \
  src/70_build_multitask_tuning_cohorts.py \
  src/71_train_supervised_text_encoder.py \
  src/72_diagnose_supervised_text_encoder.py \
  src/73_diagnose_supervised_text_encoder_learning.py \
  src/74_probe_supervised_text_encoder_recipe.py \
  src/76_audit_supervised_text_encoder_v2_checkpoint.py

bash -n scripts/run_multitask_openjev.sh
bash -n scripts/run_multitask_laya.sh

bash -n scripts/run_multitask_semantic_eval.sh

bash -n scripts/run_multitask_lexical_robustness.sh

bash -n scripts/run_local_djev_readiness.sh

bash -n scripts/run_multitask_structured_ablations.sh

bash -n scripts/run_multitask_nonlinear_rf.sh

bash -n scripts/run_multitask_sampling_calibration.sh

bash -n scripts/setup_local_djev.sh

bash -n scripts/run_multitask_djev_local.sh

bash -n scripts/run_multitask_djev_eval.sh

bash -n scripts/run_multitask_next_phase.sh

bash -n scripts/run_djev_failure_diagnosis.sh

bash -n scripts/run_multitask_djev_recovery.sh

bash -n scripts/run_djev_cuda12_fp8_smoke.sh

bash -n scripts/run_diffusiongemma_hf_native_smoke.sh

bash -n scripts/run_diffusiongemma_hf_native_cached_smoke.sh

bash -n scripts/run_diffusiongemma_hf_native_graded_calibration.sh

bash -n scripts/run_diffusiongemma_hf_native_real_pilot.sh

bash -n scripts/run_multitask_diffusiongemma_hf_native.sh

bash -n scripts/run_multitask_diffusiongemma_hf_eval.sh

bash -n scripts/run_multitask_diffusiongemma_lexical.sh

bash -n scripts/run_tuning_feasibility_audit.sh

bash -n scripts/run_multitask_tuning_cohort_build.sh

bash -n scripts/run_supervised_text_encoder_smoke.sh

bash -n scripts/run_supervised_text_encoder_development.sh

bash -n scripts/run_supervised_text_encoder_diagnostic.sh

bash -n scripts/run_supervised_text_encoder_learning_diagnostic.sh

bash -n scripts/run_supervised_text_encoder_recipe_probe.sh

bash -n scripts/run_supervised_text_encoder_v2_smoke.sh

bash -n scripts/run_supervised_text_encoder_development_v2.sh

HELP_TEXT="$("./.venv/bin/python" src/71_train_supervised_text_encoder.py --help)"
for opt in --encoder-learning-rate --head-learning-rate --positive-class-weight --protocol --analysis-name; do
  printf '%s\\n' "$HELP_TEXT" | grep -F -- "$opt" >/dev/null
done

bash -n scripts/run_supervised_text_encoder_v2_checkpoint_audit.sh

.venv/bin/python -m py_compile src/77_evaluate_supervised_text_encoder_v2_final_test.py

bash -n scripts/run_supervised_text_encoder_v2_final_test.sh

.venv/bin/python -m py_compile src/30_inventory_zigong.py

bash -n scripts/run_zigong_inventory.sh

.venv/bin/python -m py_compile src/31_audit_zigong_vasopressor_endpoint.py

.venv/bin/python -m py_compile src/33_audit_zigong_time_origins.py

bash -n scripts/run_zigong_pressor_endpoint_audit.sh

bash -n scripts/run_zigong_time_origin_audit.sh

.venv/bin/python -m py_compile src/78_audit_zigong_nursing_clock_alignment.py

bash -n scripts/run_zigong_nursing_clock_alignment_audit.sh

.venv/bin/python -m py_compile src/79_audit_zigong_dictionary_times.py

bash -n scripts/run_zigong_dictionary_timing_audit.sh

.venv/bin/python -m py_compile src/80_audit_zigong_nursing_ventilation_fields.py

bash -n scripts/run_zigong_nursing_ventilation_field_audit.sh

.venv/bin/python -m py_compile src/81_audit_zigong_nursing_ventilation_endpoint.py

bash -n scripts/run_zigong_nursing_ventilation_endpoint_audit.sh

bash -n scripts/run_zigong_nursing_ventilation_endpoint_audit_24h.sh

.venv/bin/python -m py_compile src/82_build_zigong_ventilation24_cohort.py

bash -n scripts/run_build_zigong_ventilation24_cohort.sh

.venv/bin/python -m py_compile src/83_audit_zigong_tokenizers.py

bash -n scripts/run_zigong_tokenizer_language_audit.sh

.venv/bin/python -m py_compile src/84_audit_zigong_tokenizers_v2.py

bash -n scripts/run_zigong_tokenizer_language_audit_v2.sh

.venv/bin/python -m py_compile src/85_audit_zigong_diffusiongemma_tokenizer.py

bash -n scripts/run_zigong_diffusiongemma_tokenizer_audit.sh
