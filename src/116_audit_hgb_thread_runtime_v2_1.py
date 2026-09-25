from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT111 = ROOT / "src" / "111_benchmark_refit_bootstrap_v2_1.py"
THREAD_KEYS = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
)


def load_benchmark_module():
    spec = importlib.util.spec_from_file_location("benchmark111", SCRIPT111)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load script 111")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def affinity_count() -> int | None:
    try:
        return len(os.sched_getaffinity(0))
    except Exception:
        return None


def thread_info():
    try:
        from threadpoolctl import threadpool_info
        return threadpool_info()
    except Exception as exc:
        return [{"error": repr(exc)}]


def worker_one_fold(output: Path) -> None:
    mod = load_benchmark_module()
    from sklearn.ensemble import HistGradientBoostingClassifier

    n = 11116
    prevalence = 279 / 11116
    note_coverage = 0.4047
    x, semantics, y, subjects, folds = mod.make_synthetic(
        n=n,
        prevalence=prevalence,
        note_coverage=note_coverage,
        seed=20260925,
    )
    rng = np.random.default_rng(8000)
    split_indices = mod.patient_cluster_refit_indices(subjects, folds, rng)
    fold = sorted(split_indices)[0]
    tr, te = split_indices[fold]

    params = dict(
        learning_rate=0.05,
        max_iter=300,
        max_leaf_nodes=15,
        min_samples_leaf=50,
        l2_regularization=1.0,
        early_stopping=False,
        random_state=20260924,
    )
    before = thread_info()
    t0 = time.perf_counter()
    base = HistGradientBoostingClassifier(**params)
    aug = HistGradientBoostingClassifier(**params)
    base.fit(x[tr], y[tr])
    aug.fit(np.column_stack([x[tr], semantics[tr]]), y[tr])
    _ = base.predict_proba(x[te])[:, 1]
    _ = aug.predict_proba(np.column_stack([x[te], semantics[te]]))[:, 1]
    seconds = float(time.perf_counter() - t0)
    after = thread_info()

    report = {
        "kind": "one_fold_two_hgb_fits",
        "seconds": seconds,
        "train_rows_with_bootstrap_multiplicity": int(len(tr)),
        "test_rows_with_bootstrap_multiplicity": int(len(te)),
        "os_cpu_count": os.cpu_count(),
        "affinity_cpu_count": affinity_count(),
        "thread_env": {k: os.environ.get(k) for k in THREAD_KEYS},
        "threadpool_info_before": before,
        "threadpool_info_after": after,
    }
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def worker_full(output: Path) -> None:
    mod = load_benchmark_module()
    n = 11116
    prevalence = 279 / 11116
    note_coverage = 0.4047
    x, semantics, y, subjects, folds = mod.make_synthetic(
        n=n,
        prevalence=prevalence,
        note_coverage=note_coverage,
        seed=20260925,
    )
    before = thread_info()
    t0 = time.perf_counter()
    delta = mod.fit_delta(
        x,
        semantics,
        y,
        subjects,
        folds,
        seed=8000,
        bootstrap=True,
    )
    seconds = float(time.perf_counter() - t0)
    after = thread_info()
    report = {
        "kind": "full_exact_refit_bootstrap_replicate",
        "seconds": seconds,
        "synthetic_delta_auroc": float(delta),
        "projected_500_replicate_hours_serial": float(seconds * 500 / 3600.0),
        "os_cpu_count": os.cpu_count(),
        "affinity_cpu_count": affinity_count(),
        "thread_env": {k: os.environ.get(k) for k in THREAD_KEYS},
        "threadpool_info_before": before,
        "threadpool_info_after": after,
    }
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def env_for_threads(n: int | None) -> dict[str, str]:
    env = os.environ.copy()
    if n is None:
        for key in THREAD_KEYS:
            env.pop(key, None)
    else:
        for key in THREAD_KEYS:
            env[key] = str(n)
    return env


def run_child(kind: str, threads: int | None, timeout: int, path: Path) -> dict:
    cmd = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker",
        kind,
        "--output",
        str(path),
    ]
    t0 = time.perf_counter()
    try:
        cp = subprocess.run(
            cmd,
            env=env_for_threads(threads),
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        wall = float(time.perf_counter() - t0)
        if cp.returncode != 0:
            return {
                "status": "failed",
                "returncode": int(cp.returncode),
                "wall_seconds": wall,
                "stderr_tail": cp.stderr[-4000:],
                "stdout_tail": cp.stdout[-2000:],
                "threads_requested": threads,
            }
        report = json.loads(path.read_text(encoding="utf-8"))
        report.update(
            {
                "status": "completed",
                "wall_seconds": wall,
                "threads_requested": threads,
            }
        )
        return report
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "timeout",
            "wall_seconds": float(time.perf_counter() - t0),
            "timeout_seconds": timeout,
            "threads_requested": threads,
            "stdout_tail": (exc.stdout or "")[-2000:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "",
        }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker", choices=("one-fold", "full"))
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    if args.worker == "one-fold":
        worker_one_fold(output)
        return
    if args.worker == "full":
        worker_full(output)
        return

    scratch = output.parent / "hgb_thread_audit_scratch"
    scratch.mkdir(parents=True, exist_ok=True)

    one_fold = {}
    for label, threads in (("library_default", None), ("threads_1", 1), ("threads_4", 4)):
        one_fold[label] = run_child(
            "one-fold",
            threads,
            timeout=90,
            path=scratch / f"{label}.json",
        )

    candidates = [
        (label, r)
        for label, r in one_fold.items()
        if r.get("status") == "completed" and label != "library_default"
    ]
    if not candidates:
        full = {
            "status": "not_run",
            "reason": "No explicit-thread one-fold configuration completed within the benchmark limit.",
        }
        selected = None
    else:
        selected, best = min(candidates, key=lambda item: item[1]["seconds"])
        threads = int(best["threads_requested"])
        full = run_child(
            "full",
            threads,
            timeout=600,
            path=scratch / f"full_{selected}.json",
        )

    report = {
        "analysis": "v2.1 synthetic HGB thread/runtime audit",
        "status": "completed",
        "real_clinical_data_read": False,
        "real_outcome_performance_computed": False,
        "purpose": (
            "Test whether the Y5R7M2Q8 runtime is reproducible under the workstation "
            "threading environment before using runtime to choose the preregistration "
            "uncertainty procedure."
        ),
        "reference_job": "Y5R7M2Q8",
        "reference_seconds_per_full_replicate": 5470.322735227644,
        "one_fold_results": one_fold,
        "selected_explicit_thread_configuration": selected,
        "full_replicate_result": full,
        "interpretation_rule": (
            "If an explicit-thread full replicate is dramatically faster than the "
            "Y5 reference, treat Y5 as an environment/performance artifact and re-open "
            "the refit-bootstrap feasibility decision before OSF registration."
        ),
    }
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
