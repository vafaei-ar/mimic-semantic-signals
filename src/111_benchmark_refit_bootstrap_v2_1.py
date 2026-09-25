from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from preregistration_stats import (
    one_sided_centered_bootstrap_pvalue,
    patient_cluster_refit_indices,
)
from runrelay_progress import update_progress


OUTCOMES = ("invasive_ventilation", "renal_replacement_therapy", "icu_death")


def logistic(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


def make_synthetic(n: int, prevalence: float, note_coverage: float, seed: int, p: int = 60):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=(n, p)).astype("float32")
    linear = 0.35 * x[:, 0] - 0.25 * x[:, 1] + 0.15 * x[:, 2]
    lo, hi = -12.0, 2.0
    for _ in range(80):
        mid = (lo + hi) / 2
        pr = logistic(linear + mid)
        if pr.mean() > prevalence:
            hi = mid
        else:
            lo = mid
    y = rng.binomial(1, logistic(linear + (lo + hi) / 2)).astype(int)

    semantics = rng.normal(size=(n, 8)).astype("float32")
    no_note = rng.random(n) > note_coverage
    semantics[no_note, :] = np.nan

    # One row per synthetic patient isolates model-refit runtime without
    # inventing a patient-to-stay distribution. The number of model rows is
    # the frozen confirmatory cohort size.
    subjects = np.arange(n, dtype=int)

    # Balanced deterministic fold assignment is sufficient for a runtime-only
    # synthetic benchmark and avoids rare-event fold degeneracy.
    folds = np.tile(np.arange(1, 6, dtype=int), int(np.ceil(n / 5)))[:n]
    rng.shuffle(folds)
    return x, semantics, y, subjects, folds


def write_checkpoint(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def fit_delta(
    x,
    semantics,
    y,
    subjects,
    folds,
    seed,
    *,
    bootstrap: bool,
    fold_callback=None,
):
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import roc_auc_score

    rng = np.random.default_rng(seed)

    if bootstrap:
        split_indices = patient_cluster_refit_indices(subjects, folds, rng)
    else:
        split_indices = {
            fold: (
                np.flatnonzero(folds != fold),
                np.flatnonzero(folds == fold),
            )
            for fold in sorted(np.unique(folds))
        }

    eval_y = []
    eval_base = []
    eval_aug = []

    for fold, (tr, te) in split_indices.items():
        if len(te) == 0 or y[tr].sum() == 0 or y[tr].sum() == len(tr):
            continue

        t0 = time.perf_counter()
        base = HistGradientBoostingClassifier(
            learning_rate=0.05,
            max_iter=300,
            max_leaf_nodes=15,
            min_samples_leaf=50,
            l2_regularization=1.0,
            early_stopping=False,
            random_state=20260924,
        )
        aug = HistGradientBoostingClassifier(
            learning_rate=0.05,
            max_iter=300,
            max_leaf_nodes=15,
            min_samples_leaf=50,
            l2_regularization=1.0,
            early_stopping=False,
            random_state=20260924,
        )
        base.fit(x[tr], y[tr])
        aug.fit(np.column_stack([x[tr], semantics[tr]]), y[tr])

        pb = base.predict_proba(x[te])[:, 1]
        pa = aug.predict_proba(np.column_stack([x[te], semantics[te]]))[:, 1]

        # In a patient-cluster bootstrap, duplicated held-out patients remain
        # duplicated in the evaluation distribution according to their
        # bootstrap multiplicity.
        eval_y.append(y[te])
        eval_base.append(pb)
        eval_aug.append(pa)

        elapsed = float(time.perf_counter() - t0)
        if fold_callback is not None:
            fold_callback(
                int(fold),
                elapsed,
                int(len(tr)),
                int(len(te)),
            )

    if not eval_y:
        raise RuntimeError("Synthetic benchmark produced no held-out predictions")

    yy = np.concatenate(eval_y)
    pb = np.concatenate(eval_base)
    pa = np.concatenate(eval_aug)
    if yy.sum() == 0 or yy.sum() == len(yy):
        raise RuntimeError("Synthetic benchmark produced degenerate held-out labels")

    return float(roc_auc_score(yy, pa) - roc_auc_score(yy, pb))


def synthetic_null_calibration(
    *,
    trials: int,
    bootstrap_replicates: int,
    seed: int,
) -> dict:
    """Cheap statistical check of the registered one-sided centered-bootstrap rule.

    Under a Gaussian synthetic null, draw an observed statistic T~N(0,1).
    Conditional bootstrap statistics are T_b = T + E_b, E_b~N(0,1).
    The centered-bootstrap p-value should therefore be approximately uniform
    under the null. This checks the p-value rule without thousands of HGB fits.
    """
    if trials <= 0 or bootstrap_replicates <= 0:
        raise ValueError("trials and bootstrap_replicates must be positive")

    rng = np.random.default_rng(seed)
    pvals = np.empty(trials, dtype=float)
    for i in range(trials):
        observed = float(rng.normal())
        bootstrap = observed + rng.normal(size=bootstrap_replicates)
        pvals[i] = one_sided_centered_bootstrap_pvalue(observed, bootstrap)

    return {
        "trials": int(trials),
        "bootstrap_replicates_per_trial": int(bootstrap_replicates),
        "mean_pvalue": float(pvals.mean()),
        "median_pvalue": float(np.median(pvals)),
        "rejection_rate_alpha_0_05": float(np.mean(pvals <= 0.05)),
        "rejection_rate_holm_first_0_05_over_3": float(
            np.mean(pvals <= (0.05 / 3.0))
        ),
        "minimum_observed_pvalue": float(pvals.min()),
        "maximum_observed_pvalue": float(pvals.max()),
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Synthetic-only exact-runtime benchmark for one patient-cluster "
            "refit-bootstrap replicate plus cheap null calibration of the "
            "one-sided centered-bootstrap p-value."
        )
    )
    ap.add_argument("--analysis-populations", required=True)
    ap.add_argument("--outcome", choices=OUTCOMES, required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--runtime-replicates", type=int, default=1)
    ap.add_argument("--null-trials", type=int, default=2000)
    ap.add_argument("--null-bootstrap-replicates", type=int, default=500)
    args = ap.parse_args()

    population_path = Path(args.analysis_populations).expanduser().resolve()
    population_contract = json.loads(population_path.read_text(encoding="utf-8"))
    output = Path(args.output).expanduser().resolve()

    outcome = args.outcome
    info = population_contract["confirmatory_outcomes"][outcome]
    n = int(info["rows"])
    prevalence = float(info["prevalence"])
    note_coverage = float(info["note_coverage"])

    report = {
        "analysis": "v2.1 synthetic exact-runtime patient-cluster refit-bootstrap benchmark",
        "status": "started",
        "outcome": outcome,
        "real_outcome_labels_used": False,
        "real_predictors_used": False,
        "analysis_population_contract": str(population_path),
        "synthetic_rows": n,
        "synthetic_prevalence_target": prevalence,
        "synthetic_note_coverage": note_coverage,
        "primary_hgb_specification": {
            "learning_rate": 0.05,
            "max_iter": 300,
            "max_leaf_nodes": 15,
            "min_samples_leaf": 50,
            "l2_regularization": 1.0,
            "early_stopping": False,
            "random_state": 20260924,
        },
        "bootstrap_patient_representation": (
            "explicit duplicated patient rows within fixed five-fold assignment"
        ),
        "fixed_fold_limitation": (
            "Covers patient-sampling and model-refit variance conditional on the "
            "primary fold assignment; repeats 2-5 are separate split-stability checks."
        ),
        "pvalue_rule": (
            "one-sided null-centered bootstrap p=(1 + "
            "count((delta_b-delta_obs)>=delta_obs))/(B+1) for H0 delta<=0"
        ),
        "runtime_replicates_requested": int(args.runtime_replicates),
        "runtime_replicates_completed": 0,
        "runtime_replicates": [],
        "null_calibration": None,
        "w9_supersession_reason": (
            "W9R6M4N2 combined exact full-size runtime benchmarking with eight "
            "model-refit null replicates per outcome and timed out before an artifact. "
            "This benchmark isolates the exact runtime measurement from cheap statistical "
            "null calibration."
        ),
    }
    write_checkpoint(output, report)

    x, s, y, subjects, folds = make_synthetic(
        n=n,
        prevalence=prevalence,
        note_coverage=note_coverage,
        seed=20260924 + OUTCOMES.index(outcome) + 1,
    )

    for b in range(args.runtime_replicates):
        fold_timings = []

        def on_fold(fold, seconds, train_rows, test_rows):
            fold_timings.append(
                {
                    "fold": fold,
                    "seconds": seconds,
                    "train_rows_with_bootstrap_multiplicity": train_rows,
                    "test_rows_with_bootstrap_multiplicity": test_rows,
                }
            )
            report["active_runtime_replicate"] = {
                "replicate": b + 1,
                "completed_folds": len(fold_timings),
                "fold_timings": fold_timings,
            }
            write_checkpoint(output, report)
            update_progress(
                current=len(fold_timings),
                total=5,
                phase="synthetic_refit_runtime",
                message=f"{outcome}: runtime replicate {b + 1}, fold {fold} complete",
                unit="fold",
            )

        t0 = time.perf_counter()
        delta = fit_delta(
            x,
            s,
            y,
            subjects,
            folds,
            seed=8000 + OUTCOMES.index(outcome) * 100 + b,
            bootstrap=True,
            fold_callback=on_fold,
        )
        elapsed = float(time.perf_counter() - t0)
        report["runtime_replicates"].append(
            {
                "replicate": b + 1,
                "seconds": elapsed,
                "synthetic_delta_auroc": delta,
                "fold_timings": fold_timings,
            }
        )
        report["runtime_replicates_completed"] = b + 1
        report.pop("active_runtime_replicate", None)
        median_sec = float(
            np.median([r["seconds"] for r in report["runtime_replicates"]])
        )
        report["median_seconds_per_exact_refit_bootstrap_replicate"] = median_sec
        report["projected_500_replicate_hours_serial"] = float(
            median_sec * 500 / 3600.0
        )
        write_checkpoint(output, report)

    report["null_calibration"] = synthetic_null_calibration(
        trials=args.null_trials,
        bootstrap_replicates=args.null_bootstrap_replicates,
        seed=20260925 + OUTCOMES.index(outcome),
    )
    report["status"] = "completed"
    write_checkpoint(output, report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
