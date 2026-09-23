#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
.venv/bin/python -m py_compile \
  src/runrelay_progress.py \
  src/43_evaluate_lexical_robustness.py \
  src/44_evaluate_nonlinear_structured_robustness.py \
  src/45_evaluate_transport_missingness_sensitivity.py \
  src/46_evaluate_nonlinear_rf_robustness.py \
  src/47_evaluate_treatment_language_sensitivity.py \
  src/48_evaluate_lead_time_sensitivity.py \
  src/49_evaluate_documentation_context_sensitivity.py \
  src/50_evaluate_semantic_scores_only.py \
  src/51_audit_multitask_endpoints.py \
  src/52_audit_strict_multitask_endpoints.py
