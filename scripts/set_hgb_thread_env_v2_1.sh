#!/usr/bin/env bash
# Frozen v2.1 CPU thread contract for HGB/BLAS workloads.
# The workstation exposes 112 CPUs to OpenMP even when RunRelay admits a 4-core task.
# Explicit limits prevent severe oversubscription observed in Y5R7M2Q8.
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export MKL_NUM_THREADS=4
export NUMEXPR_NUM_THREADS=4
