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
PLUS_LACTATE_FEATURES = PRIMARY_FEATURES + ["lactate_last"]


def ensure_columns(df: pd.DataFrame, cols: list[str], name: str) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise RuntimeError(f"{name} is missing required columns: {missing}")


def bootstrap_metric(df, metric_name: str, n_boot: int, seed: int) -> dict:
    from sklearn.metrics import average_precision_score, roc_auc_score

    fn = {"auroc": roc_auc_score, "auprc": average_precision_score}[metric_name]
    observed = float(fn(df["label"], df["probability"]))
    by_set = {k: g for k, g in df.groupby("match_set", sort=False)}
    sets = np.array(list(by_set.keys()))
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        sampled = rng.choice(sets, size=len(sets), replace=True)
        b = pd.concat([by_set[k] for k in sampled], ignore_index=True)
        vals.append(float(fn(b["label"], b["probability"])))
    arr = np.asarray(vals, dtype=float)
    return {
        "estimate": observed,
        "ci95": [float(np.quantile(arr, 0.025)), float(np.quantile(arr, 0.975))],
        "bootstrap_replicates": int(len(arr)),
        "cluster": "match_set",
    }


def score(df, model, features, n_boot: int, seed: int) -> dict:
    from sklearn.metrics import brier_score_loss

    p = model.predict_proba(df[features])[:, 1]
    s = df[["label", "match_set"]].copy()
    s["probability"] = p
    return {
        "n": int(len(df)),
        "cases": int(df["label"].sum()),
        "controls": int((1 - df["label"]).sum()),
        "auroc": bootstrap_metric(s, "auroc", n_boot, seed),
        "auprc": bootstrap_metric(s, "auprc", n_boot, seed + 1),
        "brier": float(brier_score_loss(s["label"], p)),
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Transport sensitivity using MIMIC-fitted median imputation without missingness indicators."
    )
    ap.add_argument("--mimic-features", required=True)
    ap.add_argument("--eicu-features", required=True)
    ap.add_argument("--nwicu-features", required=True)
    ap.add_argument("--reference-report", required=True)
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

    data = {
        "mimic": pd.read_csv(Path(args.mimic_features).expanduser().resolve()),
        "eicu": pd.read_csv(Path(args.eicu_features).expanduser().resolve()),
        "nwicu": pd.read_csv(Path(args.nwicu_features).expanduser().resolve()),
    }
    ref = json.loads(Path(args.reference_report).expanduser().resolve().read_text(encoding="utf-8"))
    feature_sets = {
        "portable_core": PRIMARY_FEATURES,
        "portable_plus_lactate": PLUS_LACTATE_FEATURES,
    }
    for name, df in data.items():
        ensure_columns(df, ["label", "match_set"] + PLUS_LACTATE_FEATURES, name)

    def make_model():
        return Pipeline([
            ("impute", SimpleImputer(strategy="median", add_indicator=False, keep_empty_features=True)),
            ("scale", StandardScaler()),
            ("model", LogisticRegression(max_iter=3000, solver="liblinear", C=1.0)),
        ])

    mimic = data["mimic"]
    y = mimic["label"].astype(int).to_numpy()
    groups = mimic["match_set"].astype(int).to_numpy()

    report = {
        "analysis": "Structured transport sensitivity without missingness indicators.",
        "preprocessing": (
            "Median imputation values are learned in MIMIC training data; no missingness "
            "indicator variables are created. The fitted MIMIC pipeline is applied unchanged externally."
        ),
        "external_refitting": False,
        "reference": "Original transport model used the same features with MIMIC-fitted missingness indicators.",
        "results": {},
        "contains_note_text": False,
        "contains_source_patient_identifiers": False,
        "patient_level_predictions_shared": False,
    }

    for j, (set_name, features) in enumerate(feature_sets.items()):
        repeat_rows = []
        oof = []
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
                p_all[test_idx] = model.predict_proba(mimic.iloc[test_idx][features])[:, 1]
            if np.isnan(p_all).any():
                raise RuntimeError(f"Missing MIMIC OOF predictions for {set_name}.")
            repeat_rows.append({
                "repeat": repeat,
                "auroc": float(roc_auc_score(y, p_all)),
                "auprc": float(average_precision_score(y, p_all)),
                "brier": float(brier_score_loss(y, p_all)),
            })
            oof.append(p_all)

        repeat_df = pd.DataFrame(repeat_rows)
        mean_oof = np.mean(np.vstack(oof), axis=0)
        mimic_scored = mimic[["label", "match_set"]].copy()
        mimic_scored["probability"] = mean_oof

        final_model = make_model()
        final_model.fit(mimic[features], y)

        values_only = {
            "mimic_internal": {
                "auroc_mean": float(repeat_df["auroc"].mean()),
                "auroc_sd": float(repeat_df["auroc"].std(ddof=1)),
                "auprc_mean": float(repeat_df["auprc"].mean()),
                "auprc_sd": float(repeat_df["auprc"].std(ddof=1)),
                "brier_mean": float(repeat_df["brier"].mean()),
                "brier_sd": float(repeat_df["brier"].std(ddof=1)),
                "mean_oof_auroc": bootstrap_metric(
                    mimic_scored, "auroc", args.bootstrap_replicates, args.seed + 100 + j
                ),
            },
            "external": {
                "eicu": score(
                    data["eicu"], final_model, features,
                    args.bootstrap_replicates, args.seed + 1000 + j * 10,
                ),
                "nwicu": score(
                    data["nwicu"], final_model, features,
                    args.bootstrap_replicates, args.seed + 2000 + j * 10,
                ),
            },
        }

        reference = ref.get("results", {}).get(set_name, {})
        comparison = {}
        for dataset in ["eicu", "nwicu"]:
            old = reference.get("external", {}).get(dataset, {})
            new = values_only["external"][dataset]
            if old:
                comparison[dataset] = {
                    "auroc_values_only_minus_with_indicators": (
                        float(new["auroc"]["estimate"]) - float(old["auroc"]["estimate"])
                    ),
                    "auprc_values_only_minus_with_indicators": (
                        float(new["auprc"]["estimate"]) - float(old["auprc"]["estimate"])
                    ),
                    "brier_values_only_minus_with_indicators": (
                        float(new["brier"]) - float(old["brier"])
                    ),
                }

        report["results"][set_name] = {
            "values_only": values_only,
            "comparison_to_missingness_indicator_reference": comparison,
        }

    report["interpretation_guardrail"] = (
        "Large performance changes after removing missingness indicators would suggest that "
        "observation-process differences contribute materially to transport performance, especially "
        "in NWICU where case/control measurement completeness differs."
    )

    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
