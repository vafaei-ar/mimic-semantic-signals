from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


SEMANTIC_NAMES = [
    "overall_clinician_concern",
    "worsening_trajectory",
    "respiratory_concern",
    "hemodynamic_concern",
    "poor_treatment_response",
    "escalation_considered",
    "diagnostic_uncertainty",
    "reassuring_stability",
]


def load_semantics(path: Path) -> pd.DataFrame:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("status") != "ok":
                continue
            row = {"case_id": rec.get("case_id")}
            answers = rec.get("response", {}).get("answers", {})
            for name in SEMANTIC_NAMES:
                a = answers.get(name, {})
                values = a.get("chunk_values") if isinstance(a, dict) else None
                if isinstance(values, list) and values:
                    row[f"sem_{name}"] = float(np.mean(values))
                elif isinstance(a, dict) and isinstance(a.get("noul"), (int, float)):
                    row[f"sem_{name}"] = float(a["noul"])
                else:
                    row[f"sem_{name}"] = np.nan
            rows.append(row)
    return pd.DataFrame(rows)


def summarize_repeat_diff(repeat_df: pd.DataFrame, a: str, b: str) -> dict:
    vals = (
        repeat_df.pivot_table(index="repeat", columns="model", values="auroc")
        .dropna(subset=[a, b])
    )
    diffs = (vals[a] - vals[b]).to_numpy(dtype=float)
    if len(diffs) == 0:
        return {
            "mean": np.nan,
            "sd": np.nan,
            "p2_5": np.nan,
            "p97_5": np.nan,
            "repeats": 0,
            "pct_positive": np.nan,
        }
    return {
        "mean": float(np.mean(diffs)),
        "sd": float(np.std(diffs, ddof=1)) if len(diffs) > 1 else 0.0,
        "p2_5": float(np.quantile(diffs, 0.025)),
        "p97_5": float(np.quantile(diffs, 0.975)),
        "repeats": int(len(diffs)),
        "pct_positive": float(100.0 * np.mean(diffs > 0)),
    }


def matched_set_bootstrap_auc_diff(
    averaged: pd.DataFrame,
    model_a: str,
    model_b: str,
    seed: int,
    n_boot: int = 2000,
) -> dict:
    """Cluster bootstrap AUROC difference by matched case-control set."""
    from sklearn.metrics import roc_auc_score

    wide = (
        averaged.pivot_table(
            index=["case_id", "label", "match_set"],
            columns="model",
            values="probability",
        )
        .dropna(subset=[model_a, model_b])
        .reset_index()
    )
    match_sets = wide["match_set"].drop_duplicates().to_numpy()
    if len(match_sets) < 2:
        return {
            "difference": np.nan,
            "ci95": [np.nan, np.nan],
            "bootstrap_replicates": 0,
        }

    observed = float(
        roc_auc_score(wide["label"], wide[model_a])
        - roc_auc_score(wide["label"], wide[model_b])
    )

    by_set = {k: g.copy() for k, g in wide.groupby("match_set", sort=False)}
    rng = np.random.default_rng(seed)
    diffs = []
    for _ in range(n_boot):
        sampled = rng.choice(match_sets, size=len(match_sets), replace=True)
        parts = [by_set[k] for k in sampled]
        boot = pd.concat(parts, ignore_index=True)
        if boot["label"].nunique() < 2:
            continue
        diffs.append(
            float(
                roc_auc_score(boot["label"], boot[model_a])
                - roc_auc_score(boot["label"], boot[model_b])
            )
        )

    arr = np.asarray(diffs, dtype=float)
    return {
        "difference": observed,
        "ci95": [
            float(np.quantile(arr, 0.025)),
            float(np.quantile(arr, 0.975)),
        ] if len(arr) else [np.nan, np.nan],
        "bootstrap_replicates": int(len(arr)),
        "cluster": "match_set",
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Compare physiology-only, semantics-only, and combined vasopressor models."
    )
    ap.add_argument("--features", required=True)
    ap.add_argument("--semantics", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--repeats", type=int, default=20)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--seed", type=int, default=20260920)
    ap.add_argument("--bootstrap-replicates", type=int, default=2000)
    args = ap.parse_args()

    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
    from sklearn.model_selection import StratifiedGroupKFold
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    features = pd.read_csv(Path(args.features).expanduser().resolve())
    semantics = load_semantics(Path(args.semantics).expanduser().resolve())
    df = features.merge(semantics, on="case_id", how="inner")
    if df.empty:
        raise RuntimeError("No overlap between structured features and semantic predictions.")

    y = df["label"].astype(int).to_numpy()
    groups = df["match_set"].astype(int).to_numpy()
    semantic_cols = [c for c in df.columns if c.startswith("sem_")]
    categorical_cols = [c for c in ["category", "dbsource"] if c in df.columns]
    baseline_numeric = [c for c in ["hours_since_icu"] if c in df.columns]
    excluded = {
        "case_id", "label", "match_set", "patient_group",
        *categorical_cols, *baseline_numeric, *semantic_cols,
    }
    physiology_cols = [
        c for c in df.columns
        if c not in excluded and pd.api.types.is_numeric_dtype(df[c])
    ]
    baseline_cols = baseline_numeric + categorical_cols

    models = {
        "physiology_only": baseline_cols + physiology_cols,
        "semantics_only": baseline_cols + semantic_cols,
        "physiology_plus_semantics": baseline_cols + physiology_cols + semantic_cols,
    }
    for semantic_col in semantic_cols:
        short = semantic_col.removeprefix("sem_")
        models[f"physiology_plus_{short}"] = (
            baseline_cols + physiology_cols + [semantic_col]
        )

    def make_pipeline(cols: list[str]):
        num = [c for c in cols if c not in categorical_cols]
        cat = [c for c in cols if c in categorical_cols]
        transformers = []
        if num:
            transformers.append(
                (
                    "num",
                    Pipeline([
                        ("impute", SimpleImputer(strategy="median", add_indicator=True)),
                        ("scale", StandardScaler()),
                    ]),
                    num,
                )
            )
        if cat:
            transformers.append(
                (
                    "cat",
                    OneHotEncoder(handle_unknown="ignore"),
                    cat,
                )
            )
        pre = ColumnTransformer(transformers, remainder="drop")
        return Pipeline([
            ("pre", pre),
            ("model", LogisticRegression(
                max_iter=3000,
                solver="liblinear",
                C=1.0,
            )),
        ])

    fold_rows = []
    repeat_rows = []
    oof_rows = []

    for repeat in range(args.repeats):
        cv = StratifiedGroupKFold(
            n_splits=args.folds,
            shuffle=True,
            random_state=args.seed + repeat,
        )
        repeat_predictions = {
            model_name: np.full(len(df), np.nan, dtype=float)
            for model_name in models
        }

        for fold, (train_idx, test_idx) in enumerate(cv.split(df, y, groups=groups)):
            for model_name, cols in models.items():
                pipe = make_pipeline(cols)
                pipe.fit(df.iloc[train_idx][cols], y[train_idx])
                p = pipe.predict_proba(df.iloc[test_idx][cols])[:, 1]
                repeat_predictions[model_name][test_idx] = p
                fold_rows.append({
                    "repeat": repeat,
                    "fold": fold,
                    "model": model_name,
                    "n_test": len(test_idx),
                    "auroc": float(roc_auc_score(y[test_idx], p)),
                    "auprc": float(average_precision_score(y[test_idx], p)),
                    "brier": float(brier_score_loss(y[test_idx], p)),
                })

        for model_name, p_all in repeat_predictions.items():
            if np.isnan(p_all).any():
                raise RuntimeError(
                    f"Missing out-of-fold predictions for repeat {repeat}, model {model_name}."
                )
            repeat_rows.append({
                "repeat": repeat,
                "model": model_name,
                "n": len(df),
                "auroc": float(roc_auc_score(y, p_all)),
                "auprc": float(average_precision_score(y, p_all)),
                "brier": float(brier_score_loss(y, p_all)),
            })
            for idx, p in enumerate(p_all):
                oof_rows.append({
                    "repeat": repeat,
                    "model": model_name,
                    "case_id": df.iloc[idx]["case_id"],
                    "label": int(y[idx]),
                    "match_set": int(df.iloc[idx]["match_set"]),
                    "patient_group": str(df.iloc[idx]["patient_group"])
                    if "patient_group" in df.columns else "",
                    "probability": float(p),
                })

    fold_df = pd.DataFrame(fold_rows)
    repeat_df = pd.DataFrame(repeat_rows)
    oof_df = pd.DataFrame(oof_rows)

    out = Path(args.output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    fold_df.to_csv(out / "cv_fold_metrics.csv", index=False)
    repeat_df.to_csv(out / "cv_repeat_metrics.csv", index=False)
    oof_df.to_csv(out / "oof_predictions.csv", index=False)

    summary = (
        repeat_df.groupby("model")
        .agg(
            auroc_mean=("auroc", "mean"),
            auroc_sd=("auroc", "std"),
            auroc_p2_5=("auroc", lambda x: x.quantile(0.025)),
            auroc_p97_5=("auroc", lambda x: x.quantile(0.975)),
            auprc_mean=("auprc", "mean"),
            auprc_sd=("auprc", "std"),
            brier_mean=("brier", "mean"),
            brier_sd=("brier", "std"),
            repeats=("auroc", "size"),
        )
        .reset_index()
    )
    summary.to_csv(out / "model_summary.csv", index=False)

    averaged_oof = (
        oof_df.groupby(
            ["case_id", "label", "match_set", "patient_group", "model"],
            as_index=False,
        )["probability"]
        .mean()
    )
    averaged_oof.to_csv(out / "oof_predictions_averaged.csv", index=False)

    matched_bootstrap = matched_set_bootstrap_auc_diff(
        averaged_oof,
        "physiology_plus_semantics",
        "physiology_only",
        seed=args.seed + 100,
        n_boot=args.bootstrap_replicates,
    )

    single_semantic_incremental = {}
    for semantic_col in semantic_cols:
        short = semantic_col.removeprefix("sem_")
        model_name = f"physiology_plus_{short}"
        single_semantic_incremental[short] = summarize_repeat_diff(
            repeat_df,
            model_name,
            "physiology_only",
        )

    comparisons = {
        "combined_minus_physiology_auroc": summarize_repeat_diff(
            repeat_df,
            "physiology_plus_semantics",
            "physiology_only",
        ),
        "combined_minus_semantics_auroc": summarize_repeat_diff(
            repeat_df,
            "physiology_plus_semantics",
            "semantics_only",
        ),
        "semantics_minus_physiology_auroc": summarize_repeat_diff(
            repeat_df,
            "semantics_only",
            "physiology_only",
        ),
    }

    report = {
        "n": int(len(df)),
        "cases": int(y.sum()),
        "controls": int((1 - y).sum()),
        "physiology_features": physiology_cols,
        "semantic_features": semantic_cols,
        "baseline_adjustment": baseline_cols,
        "categorical_adjustment": categorical_cols,
        "cv": {
            "folds": args.folds,
            "repeats": args.repeats,
            "total_fold_evaluations_per_model": int(args.folds * args.repeats),
            "oof_auroc_estimates_per_model": int(args.repeats),
        },
        "models": summary.to_dict(orient="records"),
        "paired_repeat_auroc_differences": comparisons,
        "matched_set_bootstrap_combined_minus_physiology_auroc": matched_bootstrap,
        "single_semantic_incremental_auroc": single_semantic_incremental,
        "contains_note_text": False,
        "contains_source_patient_identifiers": False,
        "interpretation": (
            "The primary incremental estimate is combined_minus_physiology_auroc, "
            "computed from full out-of-fold predictions for each repeated grouped split. "
            "The p2_5/p97_5 values describe variability across repeated CV partitions. "
            "The matched-set bootstrap interval on averaged out-of-fold predictions is the "
            "primary sampling-uncertainty summary for the AUROC gain. Persistent positive gain across "
            "repeats supports incremental semantic discrimination beyond the structured "
            "physiology included in this pilot."
        ),
    }
    (out / "report.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
