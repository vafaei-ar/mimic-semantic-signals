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

    # One row per synthetic patient for the runtime benchmark is conservative
    # for fold isolation and avoids inventing a patient-stay distribution.
    subjects = np.arange(n, dtype=int)
    folds = rng.integers(1, 6, size=n)
    return x, semantics, y, subjects, folds


def fit_delta(x, semantics, y, subjects, folds, seed, bootstrap: bool):
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
        base = HistGradientBoostingClassifier(
            learning_rate=0.05,
            max_iter=300,
            max_leaf_nodes=15,
            min_samples_leaf=50,
            l2_regularization=1.0,
            early_stopping=False,
            random_state=seed + int(fold),
        )
        aug = HistGradientBoostingClassifier(
            learning_rate=0.05,
            max_iter=300,
            max_leaf_nodes=15,
            min_samples_leaf=50,
            l2_regularization=1.0,
            early_stopping=False,
            random_state=seed + int(fold),
        )
        base.fit(x[tr], y[tr])
        aug.fit(np.column_stack([x[tr], semantics[tr]]), y[tr])

        pb = base.predict_proba(x[te])[:, 1]
        pa = aug.predict_proba(np.column_stack([x[te], semantics[te]]))[:, 1]

        # In a patient-cluster bootstrap, duplicated held-out patients must
        # contribute with their bootstrap multiplicity to the evaluation
        # distribution.  te therefore remains duplicated here rather than
        # being collapsed back to unique original rows.
        eval_y.append(y[te])
        eval_base.append(pb)
        eval_aug.append(pa)

    if not eval_y:
        raise RuntimeError("Synthetic benchmark produced no held-out predictions")

    yy = np.concatenate(eval_y)
    pb = np.concatenate(eval_base)
    pa = np.concatenate(eval_aug)
    if yy.sum() == 0 or yy.sum() == len(yy):
        raise RuntimeError("Synthetic benchmark produced degenerate held-out labels")

    return float(roc_auc_score(yy, pa) - roc_auc_score(yy, pb))


def main() -> None:
    ap = argparse.ArgumentParser(description="Synthetic-only runtime/null benchmark for patient-cluster refit bootstrap.")
    ap.add_argument("--analysis-populations", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--runtime-replicates", type=int, default=1)
    ap.add_argument("--null-replicates", type=int, default=20)
    args = ap.parse_args()

    population_path = Path(args.analysis_populations).expanduser().resolve()
    population_contract = json.loads(population_path.read_text(encoding="utf-8"))
    report = {
        "analysis": "v2.1 synthetic patient-cluster refit-bootstrap benchmark",
        "real_outcome_labels_used": False,
        "real_predictors_used": False,
        "analysis_population_contract": str(population_path),
        "death_population": "MetaVision-only confirmatory ICU-death population",
        "bootstrap_patient_representation": "explicit duplicated patient rows within fixed frozen fold",
        "fixed_fold_limitation": (
            "Covers patient-sampling and model-refit variance conditional on the primary fold assignment; "
            "does not include variance from choosing a different fold partition. Repeats 2-5 are stability checks."
        ),
        "pvalue_rule": (
            "one-sided null-centered bootstrap p=(1 + count((delta_b-delta_obs)>=delta_obs))/(B+1) "
            "for H0 delta<=0"
        ),
        "outcomes": {},
    }

    for oi, outcome in enumerate(OUTCOMES, start=1):
        info = population_contract["confirmatory_outcomes"][outcome]
        n = int(info["rows"])
        prevalence = float(info["prevalence"])
        note_coverage = float(info["note_coverage"])

        update_progress(
            current=oi,
            total=len(OUTCOMES),
            phase="synthetic_refit_bootstrap_benchmark",
            message=f"{outcome}: benchmarking explicit-duplication refit bootstrap on synthetic data",
            unit="outcome",
        )

        x, s, y, subjects, folds = make_synthetic(
            n=n,
            prevalence=prevalence,
            note_coverage=note_coverage,
            seed=20260924 + oi,
        )
        observed = fit_delta(x, s, y, subjects, folds, 7000 + oi, bootstrap=False)

        times = []
        deltas = []
        for b in range(args.runtime_replicates):
            t0 = time.perf_counter()
            d = fit_delta(x, s, y, subjects, folds, 8000 + oi * 100 + b, bootstrap=True)
            times.append(time.perf_counter() - t0)
            deltas.append(d)

        # Null-behavior check on a smaller independent synthetic dataset. The 8
        # added semantic features are pure noise by construction.
        small_n = min(5000, n)
        xn, sn, yn, subn, foldn = make_synthetic(
            n=small_n,
            prevalence=max(prevalence, 0.02),
            note_coverage=note_coverage,
            seed=9000 + oi,
            p=40,
        )
        null_obs = fit_delta(xn, sn, yn, subn, foldn, 10000 + oi, bootstrap=False)
        null_boot = [
            fit_delta(xn, sn, yn, subn, foldn, 11000 + oi * 1000 + b, bootstrap=True)
            for b in range(args.null_replicates)
        ]
        null_p = one_sided_centered_bootstrap_pvalue(null_obs, null_boot)

        median_sec = float(np.median(times))
        report["outcomes"][outcome] = {
            "synthetic_rows": n,
            "synthetic_prevalence_target": prevalence,
            "synthetic_note_coverage": note_coverage,
            "runtime_replicates": int(args.runtime_replicates),
            "runtime_seconds": [float(x) for x in times],
            "median_seconds_per_refit_bootstrap_replicate": median_sec,
            "projected_500_replicate_hours_serial": float(median_sec * 500 / 3600.0),
            "observed_synthetic_noise_delta_auroc": observed,
            "runtime_bootstrap_deltas": deltas,
            "null_check": {
                "rows": small_n,
                "replicates": int(args.null_replicates),
                "observed_delta_auroc": null_obs,
                "bootstrap_delta_auroc": [float(x) for x in null_boot],
                "one_sided_null_centered_pvalue": null_p,
            },
        }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
