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


def summarize_repeat(df: pd.DataFrame) -> list[dict]:
    return (
        df.groupby("model")
        .agg(
            auroc_mean=("auroc", "mean"),
            auroc_sd=("auroc", "std"),
            auprc_mean=("auprc", "mean"),
            auprc_sd=("auprc", "std"),
            brier_mean=("brier", "mean"),
            brier_sd=("brier", "std"),
            repeats=("auroc", "size"),
        )
        .reset_index()
        .to_dict(orient="records")
    )


def bootstrap_model_metrics(
    averaged: pd.DataFrame,
    model: str,
    n_boot: int,
    seed: int,
) -> dict:
    from sklearn.metrics import average_precision_score, roc_auc_score

    d = averaged[averaged["model"] == model].copy()
    by_set = {k: g for k, g in d.groupby("match_set", sort=False)}
    sets = np.asarray(list(by_set.keys()))
    observed_auc = float(roc_auc_score(d["label"], d["probability"]))
    observed_ap = float(average_precision_score(d["label"], d["probability"]))

    rng = np.random.default_rng(seed)
    aucs = []
    aps = []
    for _ in range(n_boot):
        sampled = rng.choice(sets, size=len(sets), replace=True)
        boot = pd.concat([by_set[k] for k in sampled], ignore_index=True)
        aucs.append(float(roc_auc_score(boot["label"], boot["probability"])))
        aps.append(float(average_precision_score(boot["label"], boot["probability"])))
    a = np.asarray(aucs)
    p = np.asarray(aps)
    return {
        "auroc": observed_auc,
        "auroc_ci95": [float(np.quantile(a, 0.025)), float(np.quantile(a, 0.975))],
        "auprc": observed_ap,
        "auprc_ci95": [float(np.quantile(p, 0.025)), float(np.quantile(p, 0.975))],
        "bootstrap_replicates": int(n_boot),
        "cluster": "match_set",
    }


def bootstrap_auc_difference(
    averaged: pd.DataFrame,
    model_a: str,
    model_b: str,
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
        .dropna(subset=[model_a, model_b])
        .reset_index()
    )
    by_set = {k: g for k, g in wide.groupby("match_set", sort=False)}
    sets = np.asarray(list(by_set.keys()))
    observed = float(
        roc_auc_score(wide["label"], wide[model_a])
        - roc_auc_score(wide["label"], wide[model_b])
    )
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        sampled = rng.choice(sets, size=len(sets), replace=True)
        boot = pd.concat([by_set[k] for k in sampled], ignore_index=True)
        vals.append(
            float(
                roc_auc_score(boot["label"], boot[model_a])
                - roc_auc_score(boot["label"], boot[model_b])
            )
        )
    arr = np.asarray(vals)
    return {
        "difference": observed,
        "ci95": [float(np.quantile(arr, 0.025)), float(np.quantile(arr, 0.975))],
        "bootstrap_replicates": int(n_boot),
        "cluster": "match_set",
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Evaluate the eight Open-Jev/Laya semantic scores alone, without structured physiology or note-context adjustment."
    )
    ap.add_argument("--features", required=True)
    ap.add_argument("--openjev", required=True)
    ap.add_argument("--laya", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--repeats", type=int, default=20)
    ap.add_argument("--bootstrap-replicates", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20260922)
    args = ap.parse_args()

    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
    from sklearn.model_selection import StratifiedGroupKFold
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    features = pd.read_csv(Path(args.features).expanduser().resolve())
    oj = load_semantics(Path(args.openjev).expanduser().resolve(), "openjev")
    ly = load_semantics(Path(args.laya).expanduser().resolve(), "laya")
    df = features.merge(oj, on="case_id", how="inner").merge(ly, on="case_id", how="inner")
    if len(df) != len(features):
        raise RuntimeError(f"Expected {len(features)} complete rows but found {len(df)}.")

    y = df["label"].astype(int).to_numpy()
    groups = df["match_set"].astype(int).to_numpy()
    oj_cols = [f"openjev_{x}" for x in SEMANTIC_NAMES]
    ly_cols = [f"laya_{x}" for x in SEMANTIC_NAMES]
    context_num = [c for c in ["hours_since_icu"] if c in df.columns]
    context_cat = [c for c in ["category", "dbsource"] if c in df.columns]
    context_cols = context_num + context_cat

    models = {
        "context_only": context_cols,
        "openjev_8_scores_only": oj_cols,
        "laya_8_scores_only": ly_cols,
        "context_plus_openjev_8_scores": context_cols + oj_cols,
        "context_plus_laya_8_scores": context_cols + ly_cols,
    }

    def make_pipeline(cols: list[str]) -> Pipeline:
        cat = [c for c in cols if c in context_cat]
        num = [c for c in cols if c not in cat]
        transformers = []
        if num:
            transformers.append((
                "num",
                Pipeline([
                    ("impute", SimpleImputer(strategy="median", add_indicator=True)),
                    ("scale", StandardScaler()),
                ]),
                num,
            ))
        if cat:
            transformers.append(("cat", OneHotEncoder(handle_unknown="ignore"), cat))
        return Pipeline([
            ("pre", ColumnTransformer(transformers, remainder="drop")),
            ("model", LogisticRegression(max_iter=3000, solver="liblinear", C=1.0)),
        ])

    repeat_rows = []
    oof_rows = []
    total = args.folds * args.repeats
    current = 0
    for repeat in range(args.repeats):
        cv = StratifiedGroupKFold(
            n_splits=args.folds,
            shuffle=True,
            random_state=args.seed + repeat,
        )
        preds = {m: np.full(len(df), np.nan, dtype=float) for m in models}
        for fold, (tr, te) in enumerate(cv.split(df, y, groups=groups)):
            for model, cols in models.items():
                pipe = make_pipeline(cols)
                pipe.fit(df.iloc[tr][cols], y[tr])
                preds[model][te] = pipe.predict_proba(df.iloc[te][cols])[:, 1]
            current += 1
            update_progress(
                current=current,
                total=total,
                phase="semantic_scores_only",
                message=f"Completed repeat {repeat + 1}/{args.repeats}, fold {fold + 1}/{args.folds}",
                unit="fold",
            )

        for model, p in preds.items():
            if np.isnan(p).any():
                raise RuntimeError(f"Missing predictions: repeat={repeat}, model={model}")
            repeat_rows.append({
                "repeat": repeat,
                "model": model,
                "auroc": float(roc_auc_score(y, p)),
                "auprc": float(average_precision_score(y, p)),
                "brier": float(brier_score_loss(y, p)),
            })
            for i, value in enumerate(p):
                oof_rows.append({
                    "repeat": repeat,
                    "model": model,
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

    model_bootstrap = {}
    for j, model in enumerate(models):
        model_bootstrap[model] = bootstrap_model_metrics(
            averaged, model, args.bootstrap_replicates, args.seed + 100 + j
        )

    differences = {
        "openjev_8_scores_only_minus_context_only": bootstrap_auc_difference(
            averaged, "openjev_8_scores_only", "context_only",
            args.bootstrap_replicates, args.seed + 501,
        ),
        "laya_8_scores_only_minus_context_only": bootstrap_auc_difference(
            averaged, "laya_8_scores_only", "context_only",
            args.bootstrap_replicates, args.seed + 502,
        ),
        "context_plus_openjev_minus_context_only": bootstrap_auc_difference(
            averaged, "context_plus_openjev_8_scores", "context_only",
            args.bootstrap_replicates, args.seed + 503,
        ),
        "context_plus_laya_minus_context_only": bootstrap_auc_difference(
            averaged, "context_plus_laya_8_scores", "context_only",
            args.bootstrap_replicates, args.seed + 504,
        ),
    }

    prevalence = float(np.mean(y))
    report = {
        "analysis": "Eight semantic scores only versus baseline note-context covariates on frozen v5.",
        "n": int(len(df)),
        "cases": int(y.sum()),
        "controls": int((1 - y).sum()),
        "case_prevalence": prevalence,
        "random_reference": {
            "auroc": 0.5,
            "auprc": prevalence,
        },
        "semantic_features": SEMANTIC_NAMES,
        "context_features": context_cols,
        "cv": {
            "folds": args.folds,
            "repeats": args.repeats,
            "group": "match_set",
        },
        "models": summarize_repeat(repeat_df),
        "matched_set_bootstrap_metrics": model_bootstrap,
        "matched_set_bootstrap_auroc_differences": differences,
        "contains_note_text": False,
        "contains_source_patient_identifiers": False,
        "patient_level_predictions_shared": False,
        "interpretation_guardrail": (
            "The two '8_scores_only' models contain only the eight semantic scores and no structured physiology, "
            "hours-since-ICU, note category, or database-source covariates. This is a descriptive discrimination "
            "sanity check and does not establish clinical utility."
        ),
    }

    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
