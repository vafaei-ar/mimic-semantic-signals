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


def load_cases(path: Path) -> pd.DataFrame:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            note = rec.get("model_state", {}).get("clinical_note")
            if not isinstance(note, str) or not note.strip():
                continue
            rows.append({"case_id": str(rec.get("case_id")), "note_text": note})
    out = pd.DataFrame(rows)
    if out.empty or out["case_id"].duplicated().any():
        raise RuntimeError("Cases file is empty or has duplicate case_id values.")
    return out


def load_diffusiongemma(path: Path) -> pd.DataFrame:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("status") != "ok":
                continue
            row = {"case_id": str(rec.get("case_id"))}
            answers = rec.get("response", {}).get("answers", {})
            valid = True
            for name in SEMANTIC_NAMES:
                a = answers.get(name, {})
                value = a.get("score") if isinstance(a, dict) else None
                if not isinstance(value, (int, float)) or not np.isfinite(float(value)):
                    valid = False
                    break
                value = float(value)
                if not 0.0 <= value <= 1.0:
                    valid = False
                    break
                row[f"dg_{name}"] = value
            if valid:
                rows.append(row)
    out = pd.DataFrame(rows)
    if out.empty or out["case_id"].duplicated().any():
        raise RuntimeError("DiffusionGemma semantic file is empty or duplicated.")
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


def evaluate_one(
    outcome: str,
    base: Path,
    folds: int,
    repeats: int,
    bootstrap_replicates: int,
    max_features: int,
    seed: int,
    progress_offset: int,
    progress_total: int,
) -> dict:
    from scipy import sparse
    from sklearn.compose import ColumnTransformer
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
    from sklearn.model_selection import StratifiedGroupKFold
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    d = base / outcome
    features = pd.read_csv(d / "structured_features.csv")
    features["case_id"] = features["case_id"].astype(str)
    cases = load_cases(d / "cases.jsonl")
    dg = load_diffusiongemma(d / "diffusiongemma_hf_raw.jsonl")
    df = features.merge(cases, on="case_id", how="inner").merge(dg, on="case_id", how="inner")

    if len(df) != len(features):
        raise RuntimeError(
            f"{outcome}: expected {len(features)} complete rows but merged {len(df)}."
        )

    y = df["label"].astype(int).to_numpy()
    groups = df["match_set"].astype(int).to_numpy()
    categorical = [c for c in ["category", "dbsource"] if c in df.columns]
    baseline_numeric = [c for c in ["hours_since_icu"] if c in df.columns]
    dg_cols = [f"dg_{x}" for x in SEMANTIC_NAMES]
    excluded = {
        "case_id",
        "label",
        "match_set",
        "patient_group",
        "note_text",
        *categorical,
        *baseline_numeric,
        *dg_cols,
    }
    physiology = [
        c for c in df.columns
        if c not in excluded and pd.api.types.is_numeric_dtype(df[c])
    ]
    baseline = baseline_numeric + categorical
    structured = baseline + physiology

    def make_preprocessor(cols: list[str]):
        num = [c for c in cols if c not in categorical]
        cat = [c for c in cols if c in categorical]
        transformers = []
        if num:
            transformers.append(
                (
                    "num",
                    Pipeline(
                        [
                            ("impute", SimpleImputer(strategy="median", add_indicator=True)),
                            ("scale", StandardScaler()),
                        ]
                    ),
                    num,
                )
            )
        if cat:
            transformers.append(("cat", OneHotEncoder(handle_unknown="ignore"), cat))
        return ColumnTransformer(transformers, remainder="drop")

    def fit_sem(train: pd.DataFrame, test: pd.DataFrame):
        pipe = Pipeline(
            [
                ("impute", SimpleImputer(strategy="median", add_indicator=True)),
                ("scale", StandardScaler()),
            ]
        )
        a = pipe.fit_transform(train[dg_cols])
        b = pipe.transform(test[dg_cols])
        return sparse.csr_matrix(a), sparse.csr_matrix(b)

    model_names = [
        "physiology_only",
        "lexical_only",
        "physiology_plus_lexical",
        "physiology_plus_diffusiongemma",
        "physiology_plus_lexical_plus_diffusiongemma",
    ]
    repeat_rows = []
    oof_rows = []
    vocab_sizes = []
    done = progress_offset

    for repeat in range(repeats):
        cv = StratifiedGroupKFold(
            n_splits=folds,
            shuffle=True,
            random_state=seed + repeat,
        )
        preds = {name: np.full(len(df), np.nan, dtype=float) for name in model_names}

        for fold, (train_idx, test_idx) in enumerate(cv.split(df, y, groups=groups)):
            train = df.iloc[train_idx]
            test = df.iloc[test_idx]

            base_pre = make_preprocessor(baseline)
            phys_pre = make_preprocessor(structured)
            xb_train = sparse.csr_matrix(base_pre.fit_transform(train[baseline]))
            xb_test = sparse.csr_matrix(base_pre.transform(test[baseline]))
            xp_train = sparse.csr_matrix(phys_pre.fit_transform(train[structured]))
            xp_test = sparse.csr_matrix(phys_pre.transform(test[structured]))

            vectorizer = TfidfVectorizer(
                lowercase=True,
                strip_accents="unicode",
                ngram_range=(1, 2),
                min_df=5,
                max_df=0.98,
                max_features=max_features,
                sublinear_tf=True,
                dtype=np.float64,
            )
            xl_train = vectorizer.fit_transform(train["note_text"].astype(str))
            xl_test = vectorizer.transform(test["note_text"].astype(str))
            vocab_sizes.append(
                {
                    "repeat": repeat,
                    "fold": fold,
                    "vocabulary_size": int(len(vectorizer.vocabulary_)),
                }
            )

            xd_train, xd_test = fit_sem(train, test)
            matrices = {
                "physiology_only": (xp_train, xp_test),
                "lexical_only": (
                    sparse.hstack([xb_train, xl_train], format="csr"),
                    sparse.hstack([xb_test, xl_test], format="csr"),
                ),
                "physiology_plus_lexical": (
                    sparse.hstack([xp_train, xl_train], format="csr"),
                    sparse.hstack([xp_test, xl_test], format="csr"),
                ),
                "physiology_plus_diffusiongemma": (
                    sparse.hstack([xp_train, xd_train], format="csr"),
                    sparse.hstack([xp_test, xd_test], format="csr"),
                ),
                "physiology_plus_lexical_plus_diffusiongemma": (
                    sparse.hstack([xp_train, xl_train, xd_train], format="csr"),
                    sparse.hstack([xp_test, xl_test, xd_test], format="csr"),
                ),
            }

            for name, (xtr, xte) in matrices.items():
                model = LogisticRegression(
                    max_iter=3000,
                    solver="liblinear",
                    C=1.0,
                )
                model.fit(xtr, y[train_idx])
                preds[name][test_idx] = model.predict_proba(xte)[:, 1]

            done += 1
            update_progress(
                current=done,
                total=progress_total,
                phase="diffusiongemma_lexical_robustness",
                message=f"{outcome}: repeat {repeat + 1}/{repeats}, fold {fold + 1}/{folds}",
                unit="fold",
            )

        for name, p in preds.items():
            if np.isnan(p).any():
                raise RuntimeError(f"{outcome}: missing OOF predictions for {name}, repeat {repeat}.")
            repeat_rows.append(
                {
                    "repeat": repeat,
                    "model": name,
                    "auroc": float(roc_auc_score(y, p)),
                    "auprc": float(average_precision_score(y, p)),
                    "brier": float(brier_score_loss(y, p)),
                }
            )
            for i, value in enumerate(p):
                oof_rows.append(
                    {
                        "repeat": repeat,
                        "model": name,
                        "case_id": df.iloc[i]["case_id"],
                        "label": int(y[i]),
                        "match_set": int(df.iloc[i]["match_set"]),
                        "probability": float(value),
                    }
                )

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
    models = {row["model"]: row for row in summary.to_dict(orient="records")}

    comparisons = [
        ("physiology_plus_lexical", "physiology_only"),
        ("physiology_plus_diffusiongemma", "physiology_only"),
        ("physiology_plus_lexical_plus_diffusiongemma", "physiology_plus_lexical"),
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
            n_boot=bootstrap_replicates,
            seed=seed + 1000 + j,
        )

    return {
        "n": int(len(df)),
        "cases": int(y.sum()),
        "controls": int((1 - y).sum()),
        "tfidf": {
            "ngram_range": [1, 2],
            "min_df": 5,
            "max_df": 0.98,
            "max_features": max_features,
            "sublinear_tf": True,
            "fit_scope": "training fold only",
            "vocabulary_size_mean": float(pd.DataFrame(vocab_sizes)["vocabulary_size"].mean()),
        },
        "models": {name: models[name] for name in model_names},
        "paired_repeat_auroc_differences": paired,
        "matched_set_bootstrap_auroc_differences": boot,
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Test native-HF DiffusionGemma semantic scores after fold-fitted TF-IDF on the frozen multitask benchmark."
    )
    ap.add_argument("--base", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--repeats", type=int, default=10)
    ap.add_argument("--bootstrap-replicates", type=int, default=2000)
    ap.add_argument("--max-features", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=20260921)
    args = ap.parse_args()

    base = Path(args.base).expanduser().resolve()
    progress_total = len(OUTCOMES) * args.repeats * args.folds
    update_progress(
        current=0,
        total=progress_total,
        phase="diffusiongemma_lexical_robustness",
        message="Starting native-HF DiffusionGemma lexical robustness cross-validation",
        unit="fold",
    )

    results = {}
    for j, outcome in enumerate(OUTCOMES):
        results[outcome] = evaluate_one(
            outcome=outcome,
            base=base,
            folds=args.folds,
            repeats=args.repeats,
            bootstrap_replicates=args.bootstrap_replicates,
            max_features=args.max_features,
            seed=args.seed,
            progress_offset=j * args.repeats * args.folds,
            progress_total=progress_total,
        )

    report = {
        "analysis": "Cross-outcome fold-fitted TF-IDF lexical robustness for native-HF DiffusionGemma prompted semantic scores on frozen multitask benchmark v1",
        "protocol": "docs/multitask_benchmark_protocol_v1.md",
        "implementation_addendum": "docs/multitask_diffusiongemma_hf_addendum_v1.md",
        "semantic_model": "google/diffusiongemma-26B-A4B-it",
        "backend": "transformers_native_bf16_prompted_semantic_scores",
        "score_definition": "Prompted zero-shot 0-1 support scores for the frozen eight semantic constructs; not Jev noul probabilities.",
        "encoder_outcome_tuning": False,
        "fit_scope": "TF-IDF vocabulary fitted within each training fold only",
        "local_only": True,
        "contains_note_text": False,
        "contains_source_patient_identifiers": False,
        "patient_level_predictions_shared": False,
        "outcomes": results,
        "interpretation_guardrail": (
            "This is the prespecified lexical control applied to the native-HF DiffusionGemma "
            "robustness representation. It tests whether its compact prompted semantic scores add "
            "discrimination after a simple fold-fitted bag-of-words/bigram representation of the "
            "same note is included. DiffusionGemma support scores are not Jev noul probabilities."
        ),
    }
    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
