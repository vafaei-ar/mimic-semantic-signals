from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from runrelay_progress import update_progress


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


def load_semantics(path: Path, prefix: str) -> pd.DataFrame:
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
                    row[f"{prefix}_{name}"] = float(np.mean(values))
                elif isinstance(a, dict) and isinstance(a.get("noul"), (int, float)):
                    row[f"{prefix}_{name}"] = float(a["noul"])
                else:
                    row[f"{prefix}_{name}"] = np.nan
            rows.append(row)
    out = pd.DataFrame(rows)
    if out.empty or out["case_id"].duplicated().any():
        raise RuntimeError(f"Semantic file for {prefix} is empty or duplicated.")
    return out


def summarize_repeat_diff(repeat_df: pd.DataFrame, a: str, b: str) -> dict:
    wide = repeat_df.pivot(index="repeat", columns="model", values="auroc").dropna(subset=[a, b])
    d = (wide[a] - wide[b]).to_numpy(dtype=float)
    return {
        "mean": float(np.mean(d)),
        "sd": float(np.std(d, ddof=1)) if len(d) > 1 else 0.0,
        "p2_5": float(np.quantile(d, 0.025)),
        "p97_5": float(np.quantile(d, 0.975)),
        "repeats": int(len(d)),
        "pct_positive": float(100.0 * np.mean(d > 0)),
    }


def bootstrap_auc_diff(
    averaged: pd.DataFrame,
    a: str,
    b: str,
    *,
    n_boot: int,
    seed: int,
) -> dict:
    from sklearn.metrics import roc_auc_score

    wide = (
        averaged.pivot_table(
            index=["case_id", "label", "match_set"],
            columns="model",
            values="probability",
        )
        .dropna(subset=[a, b])
        .reset_index()
    )
    by_set = {k: g for k, g in wide.groupby("match_set", sort=False)}
    match_sets = np.array(list(by_set.keys()))
    observed = float(
        roc_auc_score(wide["label"], wide[a])
        - roc_auc_score(wide["label"], wide[b])
    )
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        sampled = rng.choice(match_sets, size=len(match_sets), replace=True)
        boot = pd.concat([by_set[k] for k in sampled], ignore_index=True)
        vals.append(
            float(
                roc_auc_score(boot["label"], boot[a])
                - roc_auc_score(boot["label"], boot[b])
            )
        )
    arr = np.asarray(vals, dtype=float)
    return {
        "difference": observed,
        "ci95": [float(np.quantile(arr, 0.025)), float(np.quantile(arr, 0.975))],
        "bootstrap_replicates": int(len(arr)),
        "cluster": "match_set",
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Post-timeout nonlinear sensitivity using a bounded random-forest "
            "structured physiology comparator."
        )
    )
    ap.add_argument("--features", required=True)
    ap.add_argument("--openjev", required=True)
    ap.add_argument("--laya", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--repeats", type=int, default=10)
    ap.add_argument("--bootstrap-replicates", type=int, default=2000)
    ap.add_argument("--n-estimators", type=int, default=500)
    ap.add_argument("--seed", type=int, default=20260921)
    args = ap.parse_args()

    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
    from sklearn.model_selection import StratifiedGroupKFold
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder

    features = pd.read_csv(Path(args.features).expanduser().resolve())
    oj = load_semantics(Path(args.openjev).expanduser().resolve(), "openjev")
    ly = load_semantics(Path(args.laya).expanduser().resolve(), "laya")
    df = features.merge(oj, on="case_id", how="inner").merge(ly, on="case_id", how="inner")
    if len(df) != len(features):
        raise RuntimeError(f"Expected {len(features)} complete rows but merged {len(df)}.")

    y = df["label"].astype(int).to_numpy()
    groups = df["match_set"].astype(int).to_numpy()
    categorical = [c for c in ["category", "dbsource"] if c in df.columns]
    baseline_numeric = [c for c in ["hours_since_icu"] if c in df.columns]
    oj_cols = [f"openjev_{x}" for x in SEMANTIC_NAMES]
    ly_cols = [f"laya_{x}" for x in SEMANTIC_NAMES]
    excluded = {
        "case_id", "label", "match_set", "patient_group",
        *categorical, *baseline_numeric, *oj_cols, *ly_cols,
    }
    physiology = [
        c for c in df.columns
        if c not in excluded and pd.api.types.is_numeric_dtype(df[c])
    ]
    baseline = baseline_numeric + categorical
    structured = baseline + physiology

    model_cols = {
        "rf_physiology": structured,
        "rf_physiology_plus_openjev": structured + oj_cols,
        "rf_physiology_plus_laya": structured + ly_cols,
    }

    def make_pipeline(cols: list[str], random_state: int) -> Pipeline:
        cat = [c for c in cols if c in categorical]
        num = [c for c in cols if c not in cat]
        transformers = []
        if num:
            transformers.append((
                "num",
                SimpleImputer(strategy="median", add_indicator=True),
                num,
            ))
        if cat:
            transformers.append((
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                cat,
            ))
        pre = ColumnTransformer(transformers, remainder="drop", sparse_threshold=0.0)
        model = RandomForestClassifier(
            n_estimators=args.n_estimators,
            max_depth=None,
            min_samples_leaf=50,
            max_features=1.0,
            bootstrap=True,
            n_jobs=4,
            random_state=random_state,
        )
        return Pipeline([("pre", pre), ("model", model)])

    repeat_rows = []
    oof_rows = []
    progress_total = int(args.repeats * args.folds)
    progress_current = 0
    update_progress(
        current=0,
        total=progress_total,
        phase="cross_validation",
        message="Starting grouped random-forest nonlinear sensitivity",
        unit="fold",
    )

    for repeat in range(args.repeats):
        cv = StratifiedGroupKFold(
            n_splits=args.folds,
            shuffle=True,
            random_state=args.seed + repeat,
        )
        preds = {name: np.full(len(df), np.nan, dtype=float) for name in model_cols}
        for fold, (train_idx, test_idx) in enumerate(cv.split(df, y, groups=groups)):
            fold_seed = args.seed + repeat * 100 + fold
            for name, cols in model_cols.items():
                pipe = make_pipeline(cols, fold_seed)
                pipe.fit(df.iloc[train_idx][cols], y[train_idx])
                preds[name][test_idx] = pipe.predict_proba(df.iloc[test_idx][cols])[:, 1]

            progress_current += 1
            update_progress(
                current=progress_current,
                total=progress_total,
                phase="cross_validation",
                message=f"Completed repeat {repeat + 1}/{args.repeats}, fold {fold + 1}/{args.folds}",
                unit="fold",
            )

        for name, p in preds.items():
            if np.isnan(p).any():
                raise RuntimeError(f"Missing OOF predictions for {name}, repeat {repeat}.")
            repeat_rows.append({
                "repeat": repeat,
                "model": name,
                "auroc": float(roc_auc_score(y, p)),
                "auprc": float(average_precision_score(y, p)),
                "brier": float(brier_score_loss(y, p)),
            })
            for i, value in enumerate(p):
                oof_rows.append({
                    "repeat": repeat,
                    "model": name,
                    "case_id": df.iloc[i]["case_id"],
                    "label": int(y[i]),
                    "match_set": int(df.iloc[i]["match_set"]),
                    "probability": float(value),
                })

    repeat_df = pd.DataFrame(repeat_rows)
    oof_df = pd.DataFrame(oof_rows)
    averaged = (
        oof_df.groupby(["case_id", "label", "match_set", "model"], as_index=False)["probability"]
        .mean()
    )
    summary = (
        repeat_df.groupby("model")
        .agg(
            auroc_mean=("auroc", "mean"),
            auroc_sd=("auroc", "std"),
            auprc_mean=("auprc", "mean"),
            auprc_sd=("auprc", "std"),
            brier_mean=("brier", "mean"),
            brier_sd=("brier", "std"),
        )
        .reset_index()
    )

    comparisons = [
        ("rf_physiology_plus_openjev", "rf_physiology"),
        ("rf_physiology_plus_laya", "rf_physiology"),
    ]
    paired = {}
    boot = {}
    for j, (a, b) in enumerate(comparisons):
        key = f"{a}_minus_{b}"
        paired[key] = summarize_repeat_diff(repeat_df, a, b)
        boot[key] = bootstrap_auc_diff(
            averaged,
            a,
            b,
            n_boot=args.bootstrap_replicates,
            seed=args.seed + 3000 + j,
        )

    report = {
        "analysis": (
            "Random-forest nonlinear structured sensitivity on the frozen v5 "
            "complete-matched cohort."
        ),
        "provenance_note": (
            "The originally prespecified HistGradientBoosting sensitivity produced no "
            "aggregate result because it reached only 10/50 folds before the 180-minute "
            "runtime limit. This separate sensitivity uses the same cohort, grouped folds, "
            "repeats, preprocessing, semantic features, and matched-set bootstrap but a "
            "computationally bounded random-forest comparator. It should be described as "
            "a post-timeout sensitivity analysis, not as the original prespecified model."
        ),
        "n": int(len(df)),
        "cases": int(y.sum()),
        "controls": int((1 - y).sum()),
        "folds": args.folds,
        "repeats": args.repeats,
        "structured_features": structured,
        "model_specification": {
            "estimator": "RandomForestClassifier",
            "n_estimators": args.n_estimators,
            "max_depth": None,
            "min_samples_leaf": 50,
            "max_features": 1.0,
            "bootstrap": True,
            "n_jobs": 4,
            "selection": (
                "Post-timeout computational substitution chosen before observing any "
                "aggregate nonlinear robustness result."
            ),
        },
        "models": summary.to_dict(orient="records"),
        "paired_repeat_auroc_differences": paired,
        "matched_set_bootstrap_auroc_differences": boot,
        "contains_note_text": False,
        "contains_source_patient_identifiers": False,
        "patient_level_predictions_shared": False,
        "interpretation_guardrail": (
            "This sensitivity asks whether semantic increment persists beyond a nonlinear "
            "tree-ensemble structured comparator. Because the originally prespecified HGB "
            "analysis timed out without an aggregate result, this analysis must be labeled "
            "as a post-timeout sensitivity rather than a prespecified replacement."
        ),
    }

    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
