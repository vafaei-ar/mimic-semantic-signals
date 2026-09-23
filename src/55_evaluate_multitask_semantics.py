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

OUTCOMES = [
    "invasive_ventilation",
    "renal_replacement_therapy",
    "icu_death",
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
    if out.empty:
        raise RuntimeError(f"No successful semantic rows in {path}")
    if out["case_id"].duplicated().any():
        raise RuntimeError(f"Duplicate case_id values in {path}")
    return out


def summarize_models(repeat_df: pd.DataFrame) -> list[dict]:
    return (
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
        .to_dict(orient="records")
    )


def repeat_diff(repeat_df: pd.DataFrame, a: str, b: str) -> dict:
    wide = (
        repeat_df.pivot_table(index="repeat", columns="model", values="auroc")
        .dropna(subset=[a, b])
    )
    d = (wide[a] - wide[b]).to_numpy(dtype=float)
    if len(d) == 0:
        return {"mean": None, "sd": None, "p2_5": None, "p97_5": None, "repeats": 0, "pct_positive": None}
    return {
        "mean": float(d.mean()),
        "sd": float(d.std(ddof=1)) if len(d) > 1 else 0.0,
        "p2_5": float(np.quantile(d, 0.025)),
        "p97_5": float(np.quantile(d, 0.975)),
        "repeats": int(len(d)),
        "pct_positive": float(100 * np.mean(d > 0)),
    }


def bootstrap_auc_diff(
    averaged: pd.DataFrame,
    a: str,
    b: str,
    seed: int,
    n_boot: int,
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
    sets = wide["match_set"].drop_duplicates().to_numpy()
    by_set = {k: g for k, g in wide.groupby("match_set", sort=False)}
    observed = float(
        roc_auc_score(wide["label"], wide[a])
        - roc_auc_score(wide["label"], wide[b])
    )
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        sampled = rng.choice(sets, size=len(sets), replace=True)
        boot = pd.concat([by_set[k] for k in sampled], ignore_index=True)
        vals.append(
            float(
                roc_auc_score(boot["label"], boot[a])
                - roc_auc_score(boot["label"], boot[b])
            )
        )
    arr = np.asarray(vals)
    return {
        "difference": observed,
        "ci95": [float(np.quantile(arr, 0.025)), float(np.quantile(arr, 0.975))],
        "bootstrap_replicates": int(n_boot),
        "cluster": "match_set",
    }


def bootstrap_model_metrics(
    averaged: pd.DataFrame,
    model: str,
    seed: int,
    n_boot: int,
) -> dict:
    from sklearn.metrics import average_precision_score, roc_auc_score

    d = averaged[averaged["model"] == model].copy()
    sets = d["match_set"].drop_duplicates().to_numpy()
    by_set = {k: g for k, g in d.groupby("match_set", sort=False)}
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
    return {
        "auroc": observed_auc,
        "auroc_ci95": [float(np.quantile(aucs, 0.025)), float(np.quantile(aucs, 0.975))],
        "auprc": observed_ap,
        "auprc_ci95": [float(np.quantile(aps, 0.025)), float(np.quantile(aps, 0.975))],
        "bootstrap_replicates": int(n_boot),
        "cluster": "match_set",
    }


def evaluate_one(
    outcome: str,
    base: Path,
    folds: int,
    repeats: int,
    bootstrap_replicates: int,
    seed: int,
    progress_offset: int,
    progress_total: int,
) -> dict:
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
    from sklearn.model_selection import StratifiedGroupKFold
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    d = base / outcome
    features = pd.read_csv(d / "structured_features.csv")
    oj = load_semantics(d / "open_jev_raw.jsonl", "openjev")
    ly = load_semantics(d / "laya_raw.jsonl", "laya")
    df = features.merge(oj, on="case_id", how="inner").merge(ly, on="case_id", how="inner")
    if len(df) != len(features):
        raise RuntimeError(
            f"{outcome}: expected {len(features)} complete semantic rows but found {len(df)}"
        )

    y = df["label"].astype(int).to_numpy()
    groups = df["match_set"].astype(int).to_numpy()

    categorical = [c for c in ["category", "dbsource"] if c in df.columns]
    context_numeric = [c for c in ["hours_since_icu"] if c in df.columns]
    context = context_numeric + categorical

    oj_cols = [f"openjev_{x}" for x in SEMANTIC_NAMES]
    ly_cols = [f"laya_{x}" for x in SEMANTIC_NAMES]

    excluded = {
        "case_id", "label", "match_set", "patient_group",
        *categorical, *context_numeric, *oj_cols, *ly_cols,
    }
    physiology = [
        c for c in df.columns
        if c not in excluded and pd.api.types.is_numeric_dtype(df[c])
    ]

    models = {
        "context_only": context,
        "structured_only": context + physiology,
        "openjev_8_scores_only": oj_cols,
        "laya_8_scores_only": ly_cols,
        "context_plus_openjev": context + oj_cols,
        "context_plus_laya": context + ly_cols,
        "structured_plus_openjev": context + physiology + oj_cols,
        "structured_plus_laya": context + physiology + ly_cols,
    }

    def pipeline(cols: list[str]) -> Pipeline:
        cat = [c for c in cols if c in categorical]
        num = [c for c in cols if c not in cat]
        tx = []
        if num:
            tx.append((
                "num",
                Pipeline([
                    ("impute", SimpleImputer(strategy="median", add_indicator=True)),
                    ("scale", StandardScaler()),
                ]),
                num,
            ))
        if cat:
            tx.append(("cat", OneHotEncoder(handle_unknown="ignore"), cat))
        return Pipeline([
            ("pre", ColumnTransformer(tx, remainder="drop")),
            ("model", LogisticRegression(max_iter=3000, solver="liblinear", C=1.0)),
        ])

    repeat_rows = []
    oof_rows = []
    done = progress_offset
    for repeat in range(repeats):
        cv = StratifiedGroupKFold(
            n_splits=folds,
            shuffle=True,
            random_state=seed + repeat,
        )
        preds = {m: np.full(len(df), np.nan) for m in models}
        for fold, (tr, te) in enumerate(cv.split(df, y, groups=groups)):
            for name, cols in models.items():
                p = pipeline(cols)
                p.fit(df.iloc[tr][cols], y[tr])
                preds[name][te] = p.predict_proba(df.iloc[te][cols])[:, 1]
            done += 1
            update_progress(
                current=done,
                total=progress_total,
                phase="multitask_semantic_evaluation",
                message=f"{outcome}: repeat {repeat + 1}/{repeats}, fold {fold + 1}/{folds}",
                unit="fold",
            )

        for name, probs in preds.items():
            if np.isnan(probs).any():
                raise RuntimeError(f"{outcome}: missing OOF predictions for {name}")
            repeat_rows.append({
                "repeat": repeat,
                "model": name,
                "auroc": float(roc_auc_score(y, probs)),
                "auprc": float(average_precision_score(y, probs)),
                "brier": float(brier_score_loss(y, probs)),
            })
            for i, prob in enumerate(probs):
                oof_rows.append({
                    "repeat": repeat,
                    "model": name,
                    "case_id": df.iloc[i]["case_id"],
                    "label": int(y[i]),
                    "match_set": int(df.iloc[i]["match_set"]),
                    "probability": float(prob),
                })

    repeat_df = pd.DataFrame(repeat_rows)
    oof_df = pd.DataFrame(oof_rows)
    averaged = (
        oof_df.groupby(["case_id", "label", "match_set", "model"], as_index=False)["probability"]
        .mean()
    )

    comparisons = {
        "openjev_semantics_only_minus_context": repeat_diff(
            repeat_df, "openjev_8_scores_only", "context_only"
        ),
        "laya_semantics_only_minus_context": repeat_diff(
            repeat_df, "laya_8_scores_only", "context_only"
        ),
        "structured_plus_openjev_minus_structured": repeat_diff(
            repeat_df, "structured_plus_openjev", "structured_only"
        ),
        "structured_plus_laya_minus_structured": repeat_diff(
            repeat_df, "structured_plus_laya", "structured_only"
        ),
    }

    bootstrap_diffs = {
        "structured_plus_openjev_minus_structured": bootstrap_auc_diff(
            averaged, "structured_plus_openjev", "structured_only",
            seed + 500, bootstrap_replicates,
        ),
        "structured_plus_laya_minus_structured": bootstrap_auc_diff(
            averaged, "structured_plus_laya", "structured_only",
            seed + 501, bootstrap_replicates,
        ),
    }

    bootstrap_metrics = {
        model: bootstrap_model_metrics(
            averaged, model, seed + 1000 + i, bootstrap_replicates
        )
        for i, model in enumerate([
            "context_only",
            "structured_only",
            "openjev_8_scores_only",
            "laya_8_scores_only",
            "structured_plus_openjev",
            "structured_plus_laya",
        ])
    }

    return {
        "n": int(len(df)),
        "cases": int(y.sum()),
        "controls": int((1 - y).sum()),
        "prevalence": float(y.mean()),
        "random_reference": {"auroc": 0.5, "auprc": float(y.mean())},
        "context_features": context,
        "physiology_features": physiology,
        "semantic_features": {
            "openjev": oj_cols,
            "laya": ly_cols,
        },
        "cv": {"folds": folds, "repeats": repeats, "group": "match_set"},
        "models": summarize_models(repeat_df),
        "paired_repeat_auroc_differences": comparisons,
        "matched_set_bootstrap_auroc_differences": bootstrap_diffs,
        "matched_set_bootstrap_model_metrics": bootstrap_metrics,
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Evaluate frozen zero-shot Open-Jev and Laya semantics across multiple MIMIC outcomes."
    )
    ap.add_argument("--base", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--repeats", type=int, default=20)
    ap.add_argument("--bootstrap-replicates", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20260923)
    args = ap.parse_args()

    base = Path(args.base).expanduser().resolve()
    total_folds = len(OUTCOMES) * args.folds * args.repeats
    offset = 0
    results = {}
    for j, outcome in enumerate(OUTCOMES):
        results[outcome] = evaluate_one(
            outcome=outcome,
            base=base,
            folds=args.folds,
            repeats=args.repeats,
            bootstrap_replicates=args.bootstrap_replicates,
            seed=args.seed + 100 * j,
            progress_offset=offset,
            progress_total=total_folds,
        )
        offset += args.folds * args.repeats

    report = {
        "analysis": "Frozen v1 multi-outcome zero-shot semantic evaluation",
        "protocol": "docs/multitask_benchmark_protocol_v1.md",
        "semantic_models": [
            "com-kotobalabs/open-jev-deberta-v3-large",
            "convaiinnovations/laya-typed-decisions",
        ],
        "encoder_outcome_tuning": False,
        "local_only": True,
        "contains_note_text": False,
        "contains_source_patient_identifiers": False,
        "strict_semantics_only_definition": (
            "The 8-scores-only models contain exactly the eight semantic scores and no "
            "hours-since-ICU, note category, dbsource, or physiology variables."
        ),
        "outcomes": results,
        "interpretation_guardrail": (
            "This analysis measures discrimination of frozen zero-shot semantic representations "
            "across prespecified outcomes. It does not establish causality or clinical utility, and "
            "it does not compare against fold-fitted TF-IDF yet."
        ),
    }

    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
