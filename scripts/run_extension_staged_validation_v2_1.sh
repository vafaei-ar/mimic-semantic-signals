#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

.venv/bin/python -m py_compile   src/172_evaluate_extension_t1_tfidf_v2_1.py   src/173_cache_extension_embeddings_v2_1.py   src/174_evaluate_extension_t1_embedding_v2_1.py   src/175_evaluate_extension_t1_tfidf_unstripped_v2_1.py   src/176_evaluate_extension_t1_early_fusion_v2_1.py   src/177_evaluate_extension_t0_4_support_timing_v2_1.py   src/178_evaluate_extension_t1_decomposition_v2_1.py

bash scripts/run_extension_t1_embedding_selftest_v2_1.sh
bash scripts/run_extension_t1_tfidf_unstripped_selftest_v2_1.sh
bash scripts/run_extension_t1_early_fusion_selftest_v2_1.sh
bash scripts/run_extension_t0_4_selftest_v2_1.sh
bash scripts/run_extension_t1_decomposition_selftest_v2_1.sh
