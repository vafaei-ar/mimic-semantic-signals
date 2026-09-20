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


def bootstrap_metric_diff(fold_df: pd.DataFrame, a: str, b: str, seed: int, n_boot: int = 5000):
    vals = (
        fold_df.pivot_table(index=["repeat", "fold"], columns="model", values="auroc")
        .dropna(subset=[a, b])
    )
    diffs = (vals[a] - vals[b]).to_numpy(dtype=float)
    if len(diffs) < 2:
        return {"mean": float(np.mean(diffs)) if len(diffs) else np.nan, "ci95": [np.nan, np.nan]}
    rng = np.random.default_rng(seed)
    boot = np.empty(n_boot)
    for i in range(n_boot):
        boot[i] = rng.choice(diffs, size=len(diffs), replace=True).mean()
    return {
        "mean": float(diffs.mean()),
        "ci95": [float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))],
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
    args = ap.parse_args()

    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import brier_score_loss, roc_auc_score
    from sklearn.model_selection import RepeatedStratifiedKFold
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    features = pd.read_csv(Path(args.features).expanduser().resolve())
    semantics = load_semantics(Path(args.semantics).expanduser().resolve())
    df = features.merge(semantics, on="case_id", how="inner")
    if df.empty:
        raise RuntimeError("No overlap between structured features and semantic predictions.")

    y = df["label"].astype(int).to_numpy()
    semantic_cols = [c for c in df.columns if c.startswith("sem_")]
    categorical_cols = [c for c in ["category", "dbsource"] if c in df.columns]
    excluded = {"case_id", "label", "match_set", *categorical_cols, *semantic_cols}
    physiology_cols = [
        c for c in df.columns
        if c not in excluded and pd.api.types.is_numeric_dtype(df[c])
    ]

    models = {
        "physiology_only": physiology_cols + categorical_cols,
        "semantics_only": semantic_cols + categorical_cols,
        "physiology_plus_semantics": physiology_cols + semantic_cols + categorical_cols,
    }

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
                class_weight="balanced",
                C=1.0,
            )),
        ])

    cv = RepeatedStratifiedKFold(
        n_splits=args.folds,
        n_repeats=args.repeats,
        random_state=args.seed,
    )

    rows = []
    split_index = 0
    for train_idx, test_idx in cv.split(df, y):
        repeat = split_index // args.folds
        fold = split_index % args.folds
        split_index += 1
        for model_name, cols in models.items():
            pipe = make_pipeline(cols)
            pipe.fit(df.iloc[train_idx][cols], y[train_idx])
            p = pipe.predict_proba(df.iloc[test_idx][cols])[:, 1]
            rows.append({
                "repeat": repeat,
                "fold": fold,
                "model": model_name,
                "n_test": len(test_idx),
                "auroc": float(roc_auc_score(y[test_idx], p)),
                "brier": float(brier_score_loss(y[test_idx], p)),
            })

    fold_df = pd.DataFrame(rows)
    out = Path(args.output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    fold_df.to_csv(out / "cv_fold_metrics.csv", index=False)

    summary = (
        fold_df.groupby("model")
        .agg(
            auroc_mean=("auroc", "mean"),
            auroc_sd=("auroc", "std"),
            brier_mean=("brier", "mean"),
            brier_sd=("brier", "std"),
            folds=("auroc", "size"),
        )
        .reset_index()
    )
    summary.to_csv(out / "model_summary.csv", index=False)

    comparisons = {
        "combined_minus_physiology_auroc": bootstrap_metric_diff(
            fold_df,
            "physiology_plus_semantics",
            "physiology_only",
            args.seed + 1,
        ),
        "combined_minus_semantics_auroc": bootstrap_metric_diff(
            fold_df,
            "physiology_plus_semantics",
            "semantics_only",
            args.seed + 2,
        ),
        "semantics_minus_physiology_auroc": bootstrap_metric_diff(
            fold_df,
            "semantics_only",
            "physiology_only",
            args.seed + 3,
        ),
    }

    report = {
        "n": int(len(df)),
        "cases": int(y.sum()),
        "controls": int((1 - y).sum()),
        "physiology_features": physiology_cols,
        "semantic_features": semantic_cols,
        "categorical_adjustment": categorical_cols,
        "cv": {
            "folds": args.folds,
            "repeats": args.repeats,
            "total_fold_evaluations_per_model": int(args.folds * args.repeats),
        },
        "models": summary.to_dict(orient="records"),
        "paired_fold_auroc_differences": comparisons,
        "contains_note_text": False,
        "contains_source_patient_identifiers": False,
        "interpretation": (
            "The primary incremental test is combined_minus_physiology_auroc. "
            "A positive difference with a bootstrap interval above zero is evidence that "
            "semantic note features add discrimination beyond the structured physiology "
            "included in this pilot."
        ),
    }
    (out / "report.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
