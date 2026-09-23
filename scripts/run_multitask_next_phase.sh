#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
bash scripts/run_multitask_structured_ablations.sh
bash scripts/run_multitask_sampling_calibration.sh
bash scripts/run_multitask_nonlinear_rf.sh
bash scripts/setup_local_djev.sh
bash scripts/run_multitask_djev_local.sh
bash scripts/run_multitask_djev_eval.sh
