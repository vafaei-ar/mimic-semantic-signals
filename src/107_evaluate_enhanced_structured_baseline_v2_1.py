from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from runrelay_progress import update_progress


OUTCOMES = ("invasive_ventilation", "renal_replacement_therapy", "icu_death")
REPEAT_SEEDS = (20260924, 20260925, 20260926, 20260927, 20260928)
THRESHOLDS = (0.0025, 0.005, 0.0075, 0.01, 0.015, 0.02, 0.03, 0.05)
BOOTSTRAP_SEED = 20260924
FOLDS = 5

ID_COLS = {"case_id", "subject_id", "icustay_id", "label", "has_note"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def logit(p):
    p = np.clip(np.asarray(p, dtype=float), 1e-8, 1 - 1e-8)
    return np.log(p / (1 - p))


def _weighted_citl(y, p, w):
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    w = np.asarray(w, dtype=float)
    z = logit(p)
    alpha = 0.0

    for _ in range(100):
        eta = np.clip(z + alpha, -40.0, 40.0)
        mu = 1.0 / (1.0 + np.exp(-eta))
        grad = float(np.sum(w * (y - mu)))
        info = float(np.sum(w * mu * (1.0 - mu)))
        if not np.isfinite(info) or info <= 1e-12:
            break
        step = grad / info
        alpha_new = alpha + step
        if abs(step) < 1e-10:
            alpha = alpha_new
            break
        alpha = alpha_new

    return float(alpha)


def _weighted_joint_recalibration(y, p, w):
    z = logit(p)
    y = np.asarray(y, dtype=float)
    w = np.asarray(w, dtype=float)
    beta = np.array([0.0, 1.0], dtype=float)

    for _ in range(50):
        eta = np.clip(beta[0] + beta[1] * z, -40.0, 40.0)
        mu = 1.0 / (1.0 + np.exp(-eta))
        resid = w * (y - mu)
        grad = np.array([resid.sum(), np.dot(resid, z)], dtype=float)
        v = w * mu * (1.0 - mu)
        h00 = v.sum()
        h01 = np.dot(v, z)
        h11 = np.dot(v, z * z)
        h = np.array([[h00, h01], [h01, h11]], dtype=float)
        if not np.all(np.isfinite(h)) or np.linalg.det(h) <= 1e-12:
            break
        step = np.linalg.solve(h, grad)
        beta_new = beta + step
        if np.max(np.abs(step)) < 1e-9:
            beta = beta_new
            break
        beta = beta_new

    return float(beta[0]), float(beta[1])


def calibration_metrics(y, p):
    from sklearn.metrics import brier_score_loss, log_loss

    y = np.asarray(y, dtype=int)
    p = np.asarray(p, dtype=float)
    w = np.ones(len(y), dtype=float)

    citl = _weighted_citl(y, p, w)
    joint_intercept, slope = _weighted_joint_recalibration(y, p, w)

    tmp = pd.DataFrame({"y": y, "p": p})
    try:
        tmp["bin"] = pd.qcut(tmp["p"], q=10, duplicates="drop")
    except Exception:
        tmp["bin"] = pd.cut(tmp["p"], bins=10, duplicates="drop")

    tab = (
        tmp.groupby("bin", observed=True)
        .agg(n=("y", "size"), mean_pred=("p", "mean"), observed=("y", "mean"))
        .reset_index(drop=True)
    )
    ece = float(
        np.sum((tab["n"] / len(tmp)) * np.abs(tab["observed"] - tab["mean_pred"]))
    )

    return {
        "brier": float(brier_score_loss(y, p)),
        "log_loss": float(
            log_loss(y, np.clip(p, 1e-8, 1 - 1e-8), labels=[0, 1])
        ),
        "calibration_in_the_large": citl,
        "joint_recalibration_intercept": joint_intercept,
        "calibration_slope": slope,
        "ece_10_quantile_bins": ece,
        "calibration_bins": [
            {
                "n": int(r.n),
                "mean_pred": float(r.mean_pred),
                "observed": float(r.observed),
            }
            for r in tab.itertuples(index=False)
        ],
    }


def decision_curve(y, p):
    y = np.asarray(y, dtype=int)
    p = np.asarray(p, dtype=float)
    n = len(y)
    prevalence = float(y.mean())
    out = {}

    for pt in THRESHOLDS:
        pred = p >= pt
        tp = int(np.sum(pred & (y == 1)))
        fp = int(np.sum(pred & (y == 0)))
        nb = float(tp / n - (fp / n) * (pt / (1 - pt)))
        all_nb = float(prevalence - (1 - prevalence) * (pt / (1 - pt)))
        out[f"{pt:.4f}"] = {
            "threshold_probability": float(pt),
            "model_net_benefit": nb,
            "treat_all_net_benefit": all_nb,
            "treat_none_net_benefit": 0.0,
            "classified_positive": int(pred.sum()),
            "classified_positive_fraction": float(pred.mean()),
            "true_positives": tp,
            "false_positives": fp,
        }

    return out


def basic_metrics(y, p):
    from sklearn.metrics import average_precision_score, roc_auc_score

    out = {
        "auroc": float(roc_auc_score(y, p)),
        "auprc": float(average_precision_score(y, p)),
    }
    out.update(calibration_metrics(y, p))
    out["decision_curve"] = decision_curve(y, p)
    return out


def scalar_metrics(metrics):
    return {
        k: float(metrics[k])
        for k in (
            "auroc",
            "auprc",
            "brier",
            "log_loss",
            "calibration_in_the_large",
            "joint_recalibration_intercept",
            "calibration_slope",
            "ece_10_quantile_bins",
        )
    }


def summarize_repeat_metrics(rows):
    keys = list(rows[0].keys())
    out = {}

    for key in keys:
        a = np.asarray([r[key] for r in rows], dtype=float)
        out[key] = {
            "mean": float(a.mean()),
            "sd": float(a.std(ddof=1)) if len(a) > 1 else 0.0,
            "min": float(a.min()),
            "max": float(a.max()),
        }

    return out


def _prepare_weighted_rank_metrics(y, p):
    y = np.asarray(y, dtype=int)
    p = np.asarray(p, dtype=float)

    order_asc = np.argsort(p, kind="mergesort")
    p_asc = p[order_asc]
    y_asc = y[order_asc]
    starts_asc = np.r_[0, np.flatnonzero(np.diff(p_asc) != 0) + 1]

    order_desc = order_asc[::-1]
    p_desc = p[order_desc]
    y_desc = y[order_desc]
    starts_desc = np.r_[0, np.flatnonzero(np.diff(p_desc) != 0) + 1]

    return {
        "order_asc": order_asc,
        "y_asc": y_asc,
        "starts_asc": starts_asc,
        "order_desc": order_desc,
        "y_desc": y_desc,
        "starts_desc": starts_desc,
    }


def _weighted_auc_ap(prepared, w):
    w = np.asarray(w, dtype=float)

    wa = w[prepared["order_asc"]]
    ya = prepared["y_asc"]
    gp = np.add.reduceat(wa * ya, prepared["starts_asc"])
    gn = np.add.reduceat(wa * (1 - ya), prepared["starts_asc"])
    total_pos = gp.sum()
    total_neg = gn.sum()

    if total_pos <= 0 or total_neg <= 0:
        return None, None

    cum_neg_before = np.cumsum(gn) - gn
    auc = float(
        np.sum(gp * (cum_neg_before + 0.5 * gn)) / (total_pos * total_neg)
    )

    wd = w[prepared["order_desc"]]
    yd = prepared["y_desc"]
    gp_d = np.add.reduceat(wd * yd, prepared["starts_desc"])
    gn_d = np.add.reduceat(wd * (1 - yd), prepared["starts_desc"])
    cum_tp = np.cumsum(gp_d)
    cum_fp = np.cumsum(gn_d)
    precision = np.divide(
        cum_tp,
        cum_tp + cum_fp,
        out=np.ones_like(cum_tp, dtype=float),
        where=(cum_tp + cum_fp) > 0,
    )
    recall_inc = gp_d / total_pos
    ap = float(np.sum(recall_inc * precision))
    return auc, ap


def _quantile_ci(values):
    a = np.asarray(values, dtype=float)
    return [float(np.quantile(a, 0.025)), float(np.quantile(a, 0.975))]


def bootstrap_two_models(df, n_boot, progress_base, total_progress, outcome):
    y = df["label"].to_numpy(dtype=int)
    p_linear = df["linear_prediction"].to_numpy(dtype=float)
    p_nonlinear = df["nonlinear_prediction"].to_numpy(dtype=float)

    patient_codes, patients = pd.factorize(df["subject_id"], sort=False)
    n_patients = len(patients)
    rng = np.random.default_rng(BOOTSTRAP_SEED)

    prepared = {
        "linear": _prepare_weighted_rank_metrics(y, p_linear),
        "nonlinear": _prepare_weighted_rank_metrics(y, p_nonlinear),
    }
    predictions = {"linear": p_linear, "nonlinear": p_nonlinear}

    metric_names = (
        "auroc",
        "auprc",
        "brier",
        "log_loss",
        "calibration_in_the_large",
        "joint_recalibration_intercept",
        "calibration_slope",
    )
    per_model = {
        name: {k: [] for k in metric_names}
        for name in predictions
    }
    nb = {
        name: {f"{pt:.4f}": [] for pt in THRESHOLDS}
        for name in predictions
    }
    diffs = {k: [] for k in ("auroc", "auprc", "brier", "log_loss")}

    squared_error = {
        name: (p - y.astype(float)) ** 2
        for name, p in predictions.items()
    }
    log_loss_row = {
        name: -(
            y * np.log(np.clip(p, 1e-8, 1 - 1e-8))
            + (1 - y) * np.log(np.clip(1 - p, 1e-8, 1 - 1e-8))
        )
        for name, p in predictions.items()
    }
    threshold_masks = {
        name: {f"{pt:.4f}": (p >= pt) for pt in THRESHOLDS}
        for name, p in predictions.items()
    }

    used = 0

    for b in range(n_boot):
        sampled = rng.integers(0, n_patients, size=n_patients)
        patient_mult = np.bincount(sampled, minlength=n_patients).astype(float)
        w = patient_mult[patient_codes]
        n_eff = float(w.sum())
        pos = float(np.dot(w, y))
        neg = n_eff - pos

        if pos <= 0 or neg <= 0:
            continue

        current_metrics = {}

        for name, p in predictions.items():
            auc, ap = _weighted_auc_ap(prepared[name], w)
            if auc is None or ap is None:
                break

            brier = float(np.dot(w, squared_error[name]) / n_eff)
            ll = float(np.dot(w, log_loss_row[name]) / n_eff)
            citl = _weighted_citl(y, p, w)
            joint_intercept, slope = _weighted_joint_recalibration(y, p, w)

            values = {
                "auroc": auc,
                "auprc": ap,
                "brier": brier,
                "log_loss": ll,
                "calibration_in_the_large": citl,
                "joint_recalibration_intercept": joint_intercept,
                "calibration_slope": slope,
            }
            for key, value in values.items():
                per_model[name][key].append(float(value))

            current_metrics[name] = {
                k: values[k]
                for k in ("auroc", "auprc", "brier", "log_loss")
            }

            for pt in THRESHOLDS:
                key = f"{pt:.4f}"
                mask = threshold_masks[name][key]
                tp = float(np.dot(w, mask & (y == 1)))
                fp = float(np.dot(w, mask & (y == 0)))
                nb[name][key].append(
                    float(tp / n_eff - (fp / n_eff) * (pt / (1 - pt)))
                )
        else:
            for metric in diffs:
                diffs[metric].append(
                    float(
                        current_metrics["nonlinear"][metric]
                        - current_metrics["linear"][metric]
                    )
                )
            used += 1

        if (b + 1) % 25 == 0 or (b + 1) == n_boot:
            update_progress(
                current=progress_base + b + 1,
                total=total_progress,
                phase="enhanced_structured_v2_1_bootstrap",
                message=f"{outcome}: paired patient bootstrap {b+1}/{n_boot}",
                unit="bootstrap",
            )

    return {
        "replicates_requested": int(n_boot),
        "replicates_used": int(used),
        "cluster": "source_patient",
        "implementation": (
            "patient multiplicity weights applied to repeat-averaged cross-fitted predictions; "
            "models are not refit inside bootstrap replicates"
        ),
        "models": {
            name: {
                "metrics_ci95": {
                    k: _quantile_ci(v)
                    for k, v in values.items()
                },
                "decision_curve_model_net_benefit_ci95": {
                    k: _quantile_ci(v)
                    for k, v in nb[name].items()
                },
            }
            for name, values in per_model.items()
        },
        "paired_nonlinear_minus_linear_ci95": {
            k: _quantile_ci(v)
            for k, v in diffs.items()
        },
    }


def _self_check_weighted_metrics():
    from sklearn.metrics import average_precision_score, roc_auc_score

    y = np.array([0, 1, 1, 0, 0, 1, 0, 1], dtype=int)
    p = np.array([0.05, 0.80, 0.20, 0.65, 0.40, 0.55, 0.10, 0.90], dtype=float)
    patient_codes = np.array([0, 0, 1, 2, 2, 3, 4, 4], dtype=int)
    patient_mult = np.array([2, 0, 1, 3, 1], dtype=int)
    w = patient_mult[patient_codes].astype(float)
    idx = np.repeat(np.arange(len(y)), w.astype(int))

    prepared = _prepare_weighted_rank_metrics(y, p)
    auc_fast, ap_fast = _weighted_auc_ap(prepared, w)
    auc_exact = float(roc_auc_score(y[idx], p[idx]))
    ap_exact = float(average_precision_score(y[idx], p[idx]))

    if abs(auc_fast - auc_exact) > 1e-12 or abs(ap_fast - ap_exact) > 1e-12:
        raise RuntimeError("Weighted rank metric self-check failed")


def build_models(seed):
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    linear = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median", add_indicator=True)),
            ("scale", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    solver="liblinear",
                    penalty="l2",
                    C=1.0,
                    class_weight=None,
                    max_iter=5000,
                ),
            ),
        ]
    )

    nonlinear = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median", add_indicator=True)),
            (
                "model",
                HistGradientBoostingClassifier(
                    loss="log_loss",
                    learning_rate=0.05,
                    max_iter=300,
                    max_leaf_nodes=15,
                    min_samples_leaf=50,
                    l2_regularization=1.0,
                    early_stopping=False,
                    random_state=int(seed),
                ),
            ),
        ]
    )

    return linear, nonlinear


def prepare_features(df):
    feature_cols = [c for c in df.columns if c not in ID_COLS]

    if len(feature_cols) != 34:
        raise RuntimeError(
            f"Expected 34 raw features, found {len(feature_cols)}: {feature_cols}"
        )
    if "sex" not in feature_cols:
        raise RuntimeError("Frozen sex feature missing")

    x = df[feature_cols].copy()
    sex = x.pop("sex").astype(str).str.upper()
    unexpected = sorted(set(sex.dropna().unique()) - {"M", "F"})

    if unexpected:
        raise RuntimeError(f"Unexpected sex values: {unexpected}")

    x.insert(1, "sex_male", sex.map({"M": 1.0, "F": 0.0}).astype(float))

    for c in x.columns:
        x[c] = pd.to_numeric(x[c], errors="coerce")

    if len(x.columns) != 34:
        raise RuntimeError(
            f"Encoded feature count changed unexpectedly: {len(x.columns)}"
        )

    return x, list(x.columns)


def load_frozen_splits(
    df: pd.DataFrame,
    outcome: str,
    base: Path,
    split_manifest: dict,
):
    expected = split_manifest["outcomes"].get(outcome)
    if not isinstance(expected, dict):
        raise RuntimeError(f"{outcome}: missing from split manifest")

    observed_counts = {
        "rows": int(len(df)),
        "cases": int(df["label"].astype(int).sum()),
        "controls": int(len(df) - df["label"].astype(int).sum()),
        "unique_patients": int(df["subject_id"].nunique()),
    }
    for key, value in observed_counts.items():
        if int(expected[key]) != int(value):
            raise RuntimeError(
                f"{outcome}: {key}={value} differs from frozen split manifest {expected[key]}"
            )

    split_path = base / outcome / "enhanced_structured_cv_splits_v2_1_local.csv"
    observed_hash = sha256_file(split_path)
    if observed_hash != expected["split_sha256"]:
        raise RuntimeError(
            f"{outcome}: split hash mismatch {observed_hash} != {expected['split_sha256']}"
        )

    split_df = pd.read_csv(split_path, low_memory=False)
    required = {"case_id", "subject_id"} | {
        f"repeat_{i}_fold" for i in range(1, len(REPEAT_SEEDS) + 1)
    }
    missing = required - set(split_df.columns)
    if missing:
        raise RuntimeError(
            f"{outcome}: split file missing columns {sorted(missing)}"
        )
    if split_df["case_id"].duplicated().any():
        raise RuntimeError(f"{outcome}: duplicate case_id in frozen split file")

    aligned = split_df.set_index("case_id").reindex(df["case_id"].astype(str))
    if aligned.isna().all(axis=1).any():
        raise RuntimeError(f"{outcome}: feature rows missing from frozen split file")

    split_subject = pd.to_numeric(aligned["subject_id"], errors="raise").to_numpy()
    feature_subject = pd.to_numeric(df["subject_id"], errors="raise").to_numpy()

    if not np.array_equal(split_subject, feature_subject):
        raise RuntimeError(f"{outcome}: subject_id mismatch against frozen split file")

    return aligned.reset_index(drop=True), observed_hash


def main():
    ap = argparse.ArgumentParser(
        description="Evaluate frozen corrected-adult enhanced structured baseline v2.1."
    )
    ap.add_argument("--base", required=True)
    ap.add_argument("--split-manifest", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--bootstrap-replicates", type=int, default=1000)
    args = ap.parse_args()

    _self_check_weighted_metrics()

    base = Path(args.base).expanduser().resolve()
    split_manifest_path = Path(args.split_manifest).expanduser().resolve()
    split_manifest = json.loads(split_manifest_path.read_text(encoding="utf-8"))
    out_path = Path(args.output).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    repeats = len(REPEAT_SEEDS)
    fold_work = repeats * FOLDS
    work_per_outcome = fold_work + args.bootstrap_replicates
    total_progress = len(OUTCOMES) * work_per_outcome

    report = {
        "analysis": "Enhanced structured baseline predictive evaluation v2.1",
        "protocol": "docs/enhanced_structured_baseline_evaluation_protocol_v2.md",
        "evaluation_addendum": "docs/enhanced_structured_baseline_evaluation_addendum_v2_1.md",
        "feature_mapping": "docs/enhanced_structured_baseline_mapping_freeze_v2.md",
        "feature_mapping_addendum": "docs/enhanced_structured_baseline_mapping_addendum_v2_1.md",
        "split_manifest_sha256": sha256_file(split_manifest_path),
        "local_only": True,
        "contains_patient_identifiers": False,
        "contains_row_level_predictions": False,
        "semantic_or_text_features_used": False,
        "repeat_seeds": [int(x) for x in REPEAT_SEEDS],
        "folds_per_repeat": FOLDS,
        "group": "source_patient",
        "decision_thresholds": [float(x) for x in THRESHOLDS],
        "bootstrap_replicates": int(args.bootstrap_replicates),
        "model_specs": {
            "linear": {
                "imputation": "training-fold median + missingness indicators",
                "standardization": True,
                "classifier": "LogisticRegression",
                "solver": "liblinear",
                "penalty": "l2",
                "C": 1.0,
                "class_weight": None,
            },
            "nonlinear": {
                "imputation": "training-fold median + missingness indicators",
                "classifier": "HistGradientBoostingClassifier",
                "learning_rate": 0.05,
                "max_iter": 300,
                "max_leaf_nodes": 15,
                "min_samples_leaf": 50,
                "l2_regularization": 1.0,
                "early_stopping": False,
                "class_weight": None,
            },
        },
        "outcomes": {},
    }

    for oi, outcome in enumerate(OUTCOMES):
        path = base / outcome / "enhanced_structured_features_v2_1_local.csv"
        df = pd.read_csv(path, low_memory=False)

        required = {"case_id", "subject_id", "label"}
        if not required.issubset(df.columns):
            raise RuntimeError(
                f"{outcome}: missing required columns {sorted(required - set(df.columns))}"
            )

        df["case_id"] = df["case_id"].astype(str)
        y = df["label"].astype(int).to_numpy()
        groups = df["subject_id"].to_numpy()
        x, encoded_features = prepare_features(df)

        frozen_splits, split_hash = load_frozen_splits(
            df, outcome, base, split_manifest
        )

        linear_preds = np.full((len(df), repeats), np.nan, dtype=float)
        nonlinear_preds = np.full((len(df), repeats), np.nan, dtype=float)
        fold_summaries = []
        repeat_metric_rows = {"linear": [], "nonlinear": []}
        repeat_metrics_full = {"linear": [], "nonlinear": []}

        outcome_base_progress = oi * work_per_outcome

        for ri, seed in enumerate(REPEAT_SEEDS, start=1):
            fold_assignment = pd.to_numeric(
                frozen_splits[f"repeat_{ri}_fold"], errors="raise"
            ).astype(int).to_numpy()

            if not np.isin(fold_assignment, np.arange(1, FOLDS + 1)).all():
                raise RuntimeError(
                    f"{outcome}: invalid fold value in frozen repeat {ri}"
                )

            check = pd.DataFrame(
                {"subject_id": groups, "fold": fold_assignment}
            )
            if (check.groupby("subject_id")["fold"].nunique() > 1).any():
                raise RuntimeError(
                    f"{outcome}: patient crosses frozen folds in repeat {ri}"
                )

            for fold in range(1, FOLDS + 1):
                te = np.flatnonzero(fold_assignment == fold)
                tr = np.flatnonzero(fold_assignment != fold)

                linear_model, nonlinear_model = build_models(int(seed) + fold)

                linear_model.fit(x.iloc[tr], y[tr])
                nonlinear_model.fit(x.iloc[tr], y[tr])

                linear_preds[te, ri - 1] = linear_model.predict_proba(
                    x.iloc[te]
                )[:, 1]
                nonlinear_preds[te, ri - 1] = nonlinear_model.predict_proba(
                    x.iloc[te]
                )[:, 1]

                fold_summaries.append(
                    {
                        "repeat": int(ri),
                        "seed": int(seed),
                        "fold": int(fold),
                        "train_n": int(len(tr)),
                        "test_n": int(len(te)),
                        "train_cases": int(y[tr].sum()),
                        "test_cases": int(y[te].sum()),
                        "test_unique_patients": int(
                            pd.Series(groups[te]).nunique()
                        ),
                    }
                )

                update_progress(
                    current=outcome_base_progress + (ri - 1) * FOLDS + fold,
                    total=total_progress,
                    phase="enhanced_structured_v2_1_crossfit",
                    message=(
                        f"{outcome}: repeat {ri}/{repeats}, fold {fold}/{FOLDS}"
                    ),
                    unit="fold",
                )

            if (
                np.isnan(linear_preds[:, ri - 1]).any()
                or np.isnan(nonlinear_preds[:, ri - 1]).any()
            ):
                raise RuntimeError(
                    f"{outcome}: incomplete out-of-fold predictions in repeat {ri}"
                )

            lm = basic_metrics(y, linear_preds[:, ri - 1])
            nm = basic_metrics(y, nonlinear_preds[:, ri - 1])

            repeat_metrics_full["linear"].append(
                {"repeat": int(ri), "seed": int(seed), **lm}
            )
            repeat_metrics_full["nonlinear"].append(
                {"repeat": int(ri), "seed": int(seed), **nm}
            )
            repeat_metric_rows["linear"].append(scalar_metrics(lm))
            repeat_metric_rows["nonlinear"].append(scalar_metrics(nm))

        linear_mean = linear_preds.mean(axis=1)
        nonlinear_mean = nonlinear_preds.mean(axis=1)

        linear_metrics = basic_metrics(y, linear_mean)
        nonlinear_metrics = basic_metrics(y, nonlinear_mean)

        local_pred = df[
            ["case_id", "subject_id", "icustay_id", "label"]
        ].copy()
        for ri in range(repeats):
            local_pred[f"linear_repeat_{ri+1}"] = linear_preds[:, ri]
            local_pred[f"nonlinear_repeat_{ri+1}"] = nonlinear_preds[:, ri]
        local_pred["linear_prediction_mean"] = linear_mean
        local_pred["nonlinear_prediction_mean"] = nonlinear_mean

        pred_path = (
            base
            / outcome
            / "enhanced_structured_predictions_v2_1_local.csv"
        )
        local_pred.to_csv(pred_path, index=False)

        boot_df = df[["subject_id", "label"]].copy()
        boot_df["linear_prediction"] = linear_mean
        boot_df["nonlinear_prediction"] = nonlinear_mean

        boot = bootstrap_two_models(
            boot_df,
            args.bootstrap_replicates,
            progress_base=outcome_base_progress + fold_work,
            total_progress=total_progress,
            outcome=outcome,
        )

        report["outcomes"][outcome] = {
            "n": int(len(df)),
            "cases": int(y.sum()),
            "controls": int(len(y) - y.sum()),
            "prevalence": float(y.mean()),
            "encoded_feature_names": encoded_features,
            "frozen_split_sha256": split_hash,
            "folds": fold_summaries,
            "models": {
                "linear": {
                    "averaged_oof_metrics": linear_metrics,
                    "repeat_metrics": repeat_metrics_full["linear"],
                    "repeat_variability": summarize_repeat_metrics(
                        repeat_metric_rows["linear"]
                    ),
                },
                "nonlinear": {
                    "averaged_oof_metrics": nonlinear_metrics,
                    "repeat_metrics": repeat_metrics_full["nonlinear"],
                    "repeat_variability": summarize_repeat_metrics(
                        repeat_metric_rows["nonlinear"]
                    ),
                },
            },
            "bootstrap": boot,
            "local_prediction_file": str(pred_path),
        }

    report["guardrails"] = [
        "All predictions are patient-grouped out-of-fold predictions.",
        "The evaluator loads pre-frozen split files and verifies their SHA-256 hashes.",
        "No semantic, lexical, note-context, treatment-context, or dbsource predictor is used.",
        "Calibration-in-the-large is reported separately from the joint recalibration intercept.",
        "Bootstrap intervals condition on repeat-averaged cross-fitted predictions and do not refit models.",
        "Row-level predictions and split assignments remain local.",
    ]
    report["status"] = "completed"

    out_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
