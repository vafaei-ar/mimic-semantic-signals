#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
bash scripts/setup_local_djev.sh
bash scripts/run_multitask_djev_local.sh
bash scripts/run_multitask_djev_eval.sh
