from __future__ import annotations

import argparse
import json
import re
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


def load_cases(path: Path) -> pd.DataFrame:
    rows = []
    token_rx = re.compile(r"\S+")
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            note = rec.get("model_state", {}).get("clinical_note")
            meta = rec.get("metadata", {})
            if not isinstance(note, str) or not note.strip():
                continue
            stored_chars = meta.get("note_characters")
            actual_chars = len(note)
            if stored_chars is not None and int(stored_chars) != actual_chars:
                raise RuntimeError(
                    f"note_characters mismatch for {rec.get('case_id')}: "
                    f"metadata={stored_chars}, actual={actual_chars}"
                )
            words = len(token_rx.findall(note))
            rows.append({
                "case_id": rec.get("case_id"),
                "note_characters": actual_chars,
                "note_words": words,
                "log1p_note_characters": float(np.log1p(actual_chars)),
                "log1p_note_words": float(np.log1p(words)),
            })
    out = pd.DataFrame(rows)
    if out.empty or out["case_id"].duplicated().any():
        raise RuntimeError("Frozen cases are empty or have duplicate case_id values.")
    return out


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


def distribution(x: pd.Series) -> dict:
    x = pd.to_numeric(x, errors="coerce").dropna()
    return {
        "n": int(len(x)),
        "p05": float(x.quantile(0.05)),
        "p25": float(x.quantile(0.25)),
        "median": float(x.median()),
        "p75": float(x.quantile(0.75)),
        "p95": float(x.quantile(0.95)),
        "mean": float(x.mean()),
    }


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


def evaluate_subset(
    df: pd.DataFrame,
    subset_name: str,
    *,
    folds: int,
    repeats: int,
    n_boot: int,
    seed: int,
) -> dict:
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
    from sklearn.model_selection import StratifiedGroupKFold
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    y = df["label"].astype(int).to_numpy()
    groups = df["match_set"].astype(int).to_numpy()
    categorical = [c for c in ["category", "dbsource"] if c in df.columns]
    baseline_numeric = [c for c in ["hours_since_icu"] if c in df.columns]
    doc_cols = ["log1p_note_characters", "log1p_note_words"]
    oj_cols = [f"openjev_{x}" for x in SEMANTIC_NAMES]
    ly_cols = [f"laya_{x}" for x in SEMANTIC_NAMES]
    excluded = {
        "case_id", "label", "match_set", "patient_group",
        "note_characters", "note_words",
        *doc_cols, *categorical, *baseline_numeric, *oj_cols, *ly_cols,
    }
    physiology = [
        c for c in df.columns
        if c not in excluded and pd.api.types.is_numeric_dtype(df[c])
    ]
    structured = baseline_numeric + categorical + physiology
    structured_doc = structured + doc_cols

    model_cols = {
        "physiology_only": structured,
        "physiology_plus_doclength": structured_doc,
        "physiology_plus_openjev": structured + oj_cols,
        "physiology_plus_laya": structured + ly_cols,
        "physiology_plus_doclength_plus_openjev": structured_doc + oj_cols,
        "physiology_plus_doclength_plus_laya": structured_doc + ly_cols,
    }

    def make_pipeline(cols: list[str]) -> Pipeline:
        num = [c for c in cols if c not in categorical]
        cat = [c for c in cols if c in categorical]
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
    for repeat in range(repeats):
        cv = StratifiedGroupKFold(
            n_splits=folds,
            shuffle=True,
            random_state=seed + repeat,
        )
        preds = {name: np.full(len(df), np.nan, dtype=float) for name in model_cols}
        for train_idx, test_idx in cv.split(df, y, groups=groups):
            for name, cols in model_cols.items():
                pipe = make_pipeline(cols)
                pipe.fit(df.iloc[train_idx][cols], y[train_idx])
                preds[name][test_idx] = pipe.predict_proba(df.iloc[test_idx][cols])[:, 1]

        for name, p in preds.items():
            if np.isnan(p).any():
                raise RuntimeError(
                    f"Missing OOF predictions in {subset_name}, repeat {repeat}, {name}."
                )
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
        ("physiology_plus_doclength", "physiology_only"),
        ("physiology_plus_openjev", "physiology_only"),
        ("physiology_plus_laya", "physiology_only"),
        ("physiology_plus_doclength_plus_openjev", "physiology_plus_doclength"),
        ("physiology_plus_doclength_plus_laya", "physiology_plus_doclength"),
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
            n_boot=n_boot,
            seed=seed + 1000 + j,
        )

    return {
        "subset": subset_name,
        "n": int(len(df)),
        "match_sets": int(df["match_set"].nunique()),
        "cases": int(y.sum()),
        "controls": int((1 - y).sum()),
        "folds": int(folds),
        "repeats": int(repeats),
        "models": summary.to_dict(orient="records"),
        "paired_repeat_auroc_differences": paired,
        "matched_set_bootstrap_auroc_differences": boot,
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Test whether semantic increment is explained by note length or residual note-category "
            "matching differences in the frozen v5 cohort."
        )
    )
    ap.add_argument("--features", required=True)
    ap.add_argument("--cases", required=True)
    ap.add_argument("--openjev", required=True)
    ap.add_argument("--laya", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--repeats", type=int, default=20)
    ap.add_argument("--bootstrap-replicates", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20260922)
    args = ap.parse_args()

    features = pd.read_csv(Path(args.features).expanduser().resolve())
    cases = load_cases(Path(args.cases).expanduser().resolve())
    oj = load_semantics(Path(args.openjev).expanduser().resolve(), "openjev")
    ly = load_semantics(Path(args.laya).expanduser().resolve(), "laya")
    df = (
        features.merge(cases, on="case_id", how="inner")
        .merge(oj, on="case_id", how="inner")
        .merge(ly, on="case_id", how="inner")
    )
    if len(df) != len(features):
        raise RuntimeError(f"Expected {len(features)} rows after merge but found {len(df)}.")

    match_check = df.groupby("match_set")["label"].agg(["size", "sum"])
    invalid = match_check[(match_check["size"] != 4) | (match_check["sum"] != 1)]
    if not invalid.empty:
        raise RuntimeError(f"Matched-set integrity failure: {len(invalid)} sets.")

    note_length_by_label = {}
    for label, name in [(1, "cases"), (0, "controls")]:
        g = df[df["label"].astype(int) == label]
        note_length_by_label[name] = {
            "characters": distribution(g["note_characters"]),
            "words": distribution(g["note_words"]),
        }

    category_nunique = df.groupby("match_set")["category"].nunique(dropna=False)
    exact_category_sets = category_nunique.index[category_nunique == 1]
    exact_category_df = df[df["match_set"].isin(exact_category_sets)].copy()
    if len(exact_category_sets) < max(args.folds * 5, 50):
        raise RuntimeError(
            f"Only {len(exact_category_sets)} exact-category matched sets were retained."
        )

    subsets = {
        "full_frozen_v5": df,
        "exact_note_category_complete_sets": exact_category_df,
    }

    results = {}
    update_progress(
        current=0,
        total=len(subsets),
        phase="documentation_context_sensitivity",
        message="Starting documentation-context sensitivity",
        unit="subset",
    )
    for i, (name, d) in enumerate(subsets.items(), start=1):
        results[name] = evaluate_subset(
            d,
            name,
            folds=args.folds,
            repeats=args.repeats,
            n_boot=args.bootstrap_replicates,
            seed=args.seed,
        )
        update_progress(
            current=i,
            total=len(subsets),
            phase="documentation_context_sensitivity",
            message=f"Completed {name}",
            unit="subset",
        )

    report = {
        "analysis": "Documentation-intensity and exact note-category sensitivity on frozen v5.",
        "n_full": int(len(df)),
        "match_sets_full": int(df["match_set"].nunique()),
        "note_length_features": ["log1p_note_characters", "log1p_note_words"],
        "note_length_by_label": note_length_by_label,
        "exact_note_category_retention": {
            "match_sets": int(len(exact_category_sets)),
            "percent_of_full_sets": float(
                100.0 * len(exact_category_sets) / df["match_set"].nunique()
            ),
        },
        "results": results,
        "contains_note_text": False,
        "contains_source_patient_identifiers": False,
        "patient_level_predictions_shared": False,
        "interpretation_guardrail": (
            "This sensitivity addresses simple documentation-intensity and note-category context. "
            "It does not eliminate all documentation-process differences, author effects, or latent "
            "severity not represented in the structured physiology."
        ),
    }

    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
