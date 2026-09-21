from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


PRIMARY_FEATURES = [
    "anchor_hour",
    "heart_rate_last",
    "heart_rate_delta",
    "resp_rate_last",
    "resp_rate_delta",
    "spo2_last",
    "spo2_delta",
    "sbp_last",
    "sbp_delta",
    "dbp_last",
    "dbp_delta",
    "creatinine_last",
    "wbc_last",
]

LAST_ONLY_FEATURES = [
    "anchor_hour",
    "heart_rate_last",
    "resp_rate_last",
    "spo2_last",
    "sbp_last",
    "dbp_last",
    "creatinine_last",
    "wbc_last",
]

PLUS_LACTATE_FEATURES = PRIMARY_FEATURES + ["lactate_last"]


def ensure_columns(df: pd.DataFrame, cols: list[str], name: str) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise RuntimeError(f"{name} is missing required columns: {missing}")


def matched_bootstrap_metric(
    df: pd.DataFrame,
    probability_col: str,
    *,
    metric_name: str,
    n_boot: int,
    seed: int,
) -> dict:
    from sklearn.metrics import average_precision_score, roc_auc_score

    metric_fn = {
        "auroc": roc_auc_score,
        "auprc": average_precision_score,
    }[metric_name]

    y = df["label"].astype(int).to_numpy()
    p = df[probability_col].astype(float).to_numpy()
    observed = float(metric_fn(y, p))

    by_set = {k: g.copy() for k, g in df.groupby("match_set", sort=False)}
    match_sets = np.array(list(by_set.keys()))
    rng = np.random.default_rng(seed)
    values = []

    for _ in range(n_boot):
        sampled = rng.choice(match_sets, size=len(match_sets), replace=True)
        boot = pd.concat([by_set[k] for k in sampled], ignore_index=True)
        if boot["label"].nunique() < 2:
            continue
        values.append(
            float(
                metric_fn(
                    boot["label"].astype(int).to_numpy(),
                    boot[probability_col].astype(float).to_numpy(),
                )
            )
        )

    arr = np.asarray(values, dtype=float)
    return {
        "estimate": observed,
        "ci95": [
            float(np.quantile(arr, 0.025)),
            float(np.quantile(arr, 0.975)),
        ]
        if len(arr)
        else [None, None],
        "bootstrap_replicates": int(len(arr)),
        "cluster": "match_set",
    }


def score_external(
    df: pd.DataFrame,
    model,
    features: list[str],
    *,
    dataset: str,
    n_boot: int,
    seed: int,
) -> dict:
    from sklearn.metrics import brier_score_loss

    p = model.predict_proba(df[features])[:, 1]
    scored = df[["label", "match_set"]].copy()
    scored["probability"] = p

    return {
        "dataset": dataset,
        "n": int(len(df)),
        "cases": int(df["label"].sum()),
        "controls": int((1 - df["label"]).sum()),
        "auroc": matched_bootstrap_metric(
            scored,
            "probability",
            metric_name="auroc",
            n_boot=n_boot,
            seed=seed,
        ),
        "auprc": matched_bootstrap_metric(
            scored,
            "probability",
            metric_name="auprc",
            n_boot=n_boot,
            seed=seed + 1,
        ),
        "brier": float(
            brier_score_loss(
                scored["label"].astype(int).to_numpy(),
                scored["probability"].to_numpy(),
            )
        ),
        "calibration_warning": (
            "Brier score is conditional on the matched 1:3 case-control sampling "
            "and is not population calibration."
        ),
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Train a frozen MIMIC exact-6h physiology model and apply it without "
            "refitting to eICU and NWICU."
        )
    )
    ap.add_argument("--mimic-features", required=True)
    ap.add_argument("--eicu-features", required=True)
    ap.add_argument("--nwicu-features", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--repeats", type=int, default=10)
    ap.add_argument("--bootstrap-replicates", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20260921)
    args = ap.parse_args()

    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
    from sklearn.model_selection import StratifiedGroupKFold
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    paths = {
        "mimic": Path(args.mimic_features).expanduser().resolve(),
        "eicu": Path(args.eicu_features).expanduser().resolve(),
        "nwicu": Path(args.nwicu_features).expanduser().resolve(),
    }
    data = {k: pd.read_csv(v) for k, v in paths.items()}

    feature_sets = {
        "portable_core": PRIMARY_FEATURES,
        "portable_last_only": LAST_ONLY_FEATURES,
        "portable_plus_lactate": PLUS_LACTATE_FEATURES,
    }

    for name, df in data.items():
        ensure_columns(df, ["label", "match_set"] + PLUS_LACTATE_FEATURES, name)

    def make_model() -> Pipeline:
        return Pipeline(
            [
                (
                    "impute",
                    SimpleImputer(
                        strategy="median",
                        add_indicator=True,
                        keep_empty_features=True,
                    ),
                ),
                ("scale", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        max_iter=3000,
                        solver="liblinear",
                        C=1.0,
                    ),
                ),
            ]
        )

    mimic = data["mimic"].copy()
    y = mimic["label"].astype(int).to_numpy()
    groups = mimic["match_set"].astype(int).to_numpy()

    report = {
        "contains_note_text": False,
        "contains_source_patient_identifiers": False,
        "patient_level_predictions_shared": False,
        "analysis": (
            "Frozen structured physiology transport: train in MIMIC exact-6h "
            "risk sets and apply without refitting to eICU and NWICU."
        ),
        "primary_feature_set": "portable_core",
        "feature_sets": feature_sets,
        "feature_selection_rule": (
            "Features were frozen from cross-dataset availability before examining "
            "external model performance. Direct MAP was excluded because NWICU has "
            "no direct MAP chart item. Lab trends were excluded from the portable "
            "core because of sparse repeated external measurements. Lactate is "
            "sensitivity-only because of high external missingness."
        ),
        "imputation": (
            "MIMIC-training median imputation with missingness indicators; the fitted "
            "MIMIC preprocessing pipeline is applied unchanged to external datasets."
        ),
        "external_refitting": False,
        "results": {},
    }

    for model_index, (set_name, features) in enumerate(feature_sets.items()):
        repeat_metrics = []
        oof_by_repeat = []

        for repeat in range(args.repeats):
            cv = StratifiedGroupKFold(
                n_splits=args.folds,
                shuffle=True,
                random_state=args.seed + repeat,
            )
            p_all = np.full(len(mimic), np.nan, dtype=float)

            for train_idx, test_idx in cv.split(mimic, y, groups=groups):
                model = make_model()
                model.fit(mimic.iloc[train_idx][features], y[train_idx])
                p_all[test_idx] = model.predict_proba(
                    mimic.iloc[test_idx][features]
                )[:, 1]

            if np.isnan(p_all).any():
                raise RuntimeError(
                    f"Missing MIMIC OOF predictions for {set_name}, repeat {repeat}"
                )

            repeat_metrics.append(
                {
                    "repeat": repeat,
                    "auroc": float(roc_auc_score(y, p_all)),
                    "auprc": float(average_precision_score(y, p_all)),
                    "brier": float(brier_score_loss(y, p_all)),
                }
            )
            oof_by_repeat.append(p_all)

        repeat_df = pd.DataFrame(repeat_metrics)
        mean_oof = np.mean(np.vstack(oof_by_repeat), axis=0)
        mimic_scored = mimic[["label", "match_set"]].copy()
        mimic_scored["probability"] = mean_oof

        final_model = make_model()
        final_model.fit(mimic[features], y)

        result = {
            "mimic_internal": {
                "n": int(len(mimic)),
                "cases": int(mimic["label"].sum()),
                "controls": int((1 - mimic["label"]).sum()),
                "cv": {
                    "folds": args.folds,
                    "repeats": args.repeats,
                    "auroc_mean": float(repeat_df["auroc"].mean()),
                    "auroc_sd": float(repeat_df["auroc"].std(ddof=1)),
                    "auprc_mean": float(repeat_df["auprc"].mean()),
                    "auprc_sd": float(repeat_df["auprc"].std(ddof=1)),
                    "brier_mean": float(repeat_df["brier"].mean()),
                    "brier_sd": float(repeat_df["brier"].std(ddof=1)),
                },
                "matched_set_bootstrap_on_mean_oof": {
                    "auroc": matched_bootstrap_metric(
                        mimic_scored,
                        "probability",
                        metric_name="auroc",
                        n_boot=args.bootstrap_replicates,
                        seed=args.seed + 100 + model_index,
                    ),
                    "auprc": matched_bootstrap_metric(
                        mimic_scored,
                        "probability",
                        metric_name="auprc",
                        n_boot=args.bootstrap_replicates,
                        seed=args.seed + 200 + model_index,
                    ),
                },
            },
            "external": {
                "eicu": score_external(
                    data["eicu"],
                    final_model,
                    features,
                    dataset="eicu",
                    n_boot=args.bootstrap_replicates,
                    seed=args.seed + 1000 + model_index * 10,
                ),
                "nwicu": score_external(
                    data["nwicu"],
                    final_model,
                    features,
                    dataset="nwicu",
                    n_boot=args.bootstrap_replicates,
                    seed=args.seed + 2000 + model_index * 10,
                ),
            },
        }

        report["results"][set_name] = result

    report["interpretation_guardrail"] = (
        "This analysis tests transportability of a structured deterioration model. "
        "It does not externally validate the narrative semantic signal, because eICU "
        "and NWICU do not provide comparable free-text narrative inputs for this study."
    )

    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
