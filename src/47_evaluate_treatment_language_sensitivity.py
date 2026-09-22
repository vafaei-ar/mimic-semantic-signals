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

# These terms were already excluded before cohort matching by the frozen v5 builder.
EXPLICIT_PRESSOR_PATTERNS = [
    r"\bvasopressor(?:s)?\b",
    r"\bpressor(?:s)?\b",
    r"\bnorepinephrine\b",
    r"\blevophed\b",
    r"\bphenylephrine\b",
    r"\bneo[- ]?synephrine\b",
    r"\bvasopressin\b",
    r"\bdopamine\b",
    r"\bepinephrine\b",
    r"\badrenaline\b",
    r"\bvasoactive\b",
]

# Strict residual treatment-intent language. These rules deliberately require
# action/target wording around hemodynamic concepts rather than flagging
# hypotension or shock alone.
STRICT_PATTERNS = {
    "hemodynamic_action": [
        r"\b(?:start|initiat\w*|begin|add|resume|restart|increase|escalat\w*|titrate|wean|consider|plan(?:ning)?|will|may need|might need|need(?:s)? to)\b.{0,60}\b(?:hemodynamic support|blood pressure|bp|mean arterial pressure|map)\b",
        r"\b(?:hemodynamic support|blood pressure|bp|mean arterial pressure|map)\b.{0,60}\b(?:start|initiat\w*|begin|add|resume|restart|increase|escalat\w*|titrate|wean|consider|plan(?:ning)?|will|may need|might need)\b",
        r"\b(?:support|augment|stabiliz\w*|maintain)\b.{0,30}\b(?:blood pressure|bp|hemodynamic\w*)\b",
    ],
    "bp_map_target": [
        r"\b(?:maintain|target|goal|keep)\b.{0,30}\b(?:map|mean arterial pressure|blood pressure|bp)\b",
        r"\b(?:map|mean arterial pressure|blood pressure|bp)\b.{0,30}\b(?:goal|target|maintain|keep)\b",
    ],
}

# Broad management language adds resuscitation and invasive-access planning.
BROAD_ONLY_PATTERNS = {
    "fluid_resuscitation": [
        r"\b(?:fluid|ivf|normal saline|ns|lactated ringer(?:s)?|lr)\b.{0,25}\bbolus(?:es)?\b",
        r"\bbolus(?:es)?\b.{0,25}\b(?:fluid|ivf|normal saline|ns|lactated ringer(?:s)?|lr)\b",
        r"\b(?:volume|fluid)\s+resuscitat\w*\b",
    ],
    "invasive_access_plan": [
        r"\b(?:place|insert|obtain|need|plan(?:ning)?|consider)\b.{0,35}\b(?:arterial line|art line|a-line|central line|central venous catheter|cvc)\b",
        r"\b(?:arterial line|art line|a-line|central line|central venous catheter|cvc)\b.{0,35}\b(?:place|insert|obtain|need|plan(?:ning)?|consider)\b",
    ],
}


def compile_groups(groups: dict[str, list[str]]) -> dict[str, list[re.Pattern[str]]]:
    return {
        name: [re.compile(p, flags=re.IGNORECASE | re.DOTALL) for p in patterns]
        for name, patterns in groups.items()
    }


EXPLICIT_RX = [re.compile(p, flags=re.IGNORECASE) for p in EXPLICIT_PRESSOR_PATTERNS]
STRICT_RX = compile_groups(STRICT_PATTERNS)
BROAD_ONLY_RX = compile_groups(BROAD_ONLY_PATTERNS)


def any_match(text: str, patterns: list[re.Pattern[str]]) -> bool:
    return any(p.search(text) is not None for p in patterns)


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
            row = {
                "case_id": rec.get("case_id"),
                "note_text": note,
                "explicit_pressor_term": any_match(note, EXPLICIT_RX),
            }
            for name, patterns in STRICT_RX.items():
                row[name] = any_match(note, patterns)
            for name, patterns in BROAD_ONLY_RX.items():
                row[name] = any_match(note, patterns)
            row["strict_treatment_intent"] = any(row[name] for name in STRICT_RX)
            row["broad_management_language"] = (
                row["strict_treatment_intent"]
                or any(row[name] for name in BROAD_ONLY_RX)
            )
            rows.append(row)
    out = pd.DataFrame(rows)
    if out.empty or out["case_id"].duplicated().any():
        raise RuntimeError("Cases file is empty or contains duplicate case_id values.")
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


def prevalence_table(df: pd.DataFrame, flags: list[str]) -> dict:
    out = {}
    for flag in flags:
        by_label = {}
        for label, name in [(1, "cases"), (0, "controls")]:
            g = df[df["label"].astype(int) == label]
            n = int(len(g))
            positive = int(g[flag].astype(bool).sum())
            by_label[name] = {
                "n": n,
                "positive": positive,
                "percent": float(100.0 * positive / n) if n else None,
            }
        out[flag] = by_label
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
    oj_cols = [f"openjev_{x}" for x in SEMANTIC_NAMES]
    ly_cols = [f"laya_{x}" for x in SEMANTIC_NAMES]
    excluded = {
        "case_id", "label", "match_set", "patient_group", "note_text",
        "explicit_pressor_term", "strict_treatment_intent", "broad_management_language",
        *STRICT_RX.keys(), *BROAD_ONLY_RX.keys(),
        *categorical, *baseline_numeric, *oj_cols, *ly_cols,
    }
    physiology = [
        c for c in df.columns
        if c not in excluded and pd.api.types.is_numeric_dtype(df[c])
    ]
    structured = baseline_numeric + categorical + physiology

    model_cols = {
        "physiology_only": structured,
        "physiology_plus_openjev": structured + oj_cols,
        "physiology_plus_laya": structured + ly_cols,
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
        pre = ColumnTransformer(transformers, remainder="drop")
        return Pipeline([
            ("pre", pre),
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
                raise RuntimeError(f"Missing OOF predictions in {subset_name}, repeat {repeat}, {name}.")
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

    paired = {}
    boot = {}
    for j, (a, b) in enumerate([
        ("physiology_plus_openjev", "physiology_only"),
        ("physiology_plus_laya", "physiology_only"),
    ]):
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
        "physiology_features": physiology,
        "models": summary.to_dict(orient="records"),
        "paired_repeat_auroc_differences": paired,
        "matched_set_bootstrap_auroc_differences": boot,
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Audit residual hemodynamic treatment-intent language and test semantic "
            "increment in complete matched sets free of flagged language."
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
        raise RuntimeError(f"Expected {len(features)} complete rows but merged {len(df)}.")

    match_check = df.groupby("match_set")["label"].agg(["size", "sum"])
    invalid = match_check[(match_check["size"] != 4) | (match_check["sum"] != 1)]
    if not invalid.empty:
        raise RuntimeError(f"Matched-set integrity failure before sensitivity: {len(invalid)} sets.")

    flag_cols = [
        "explicit_pressor_term",
        *STRICT_RX.keys(),
        *BROAD_ONLY_RX.keys(),
        "strict_treatment_intent",
        "broad_management_language",
    ]
    prevalence = prevalence_table(df, flag_cols)

    explicit_count = int(df["explicit_pressor_term"].sum())
    if explicit_count != 0:
        raise RuntimeError(
            f"Frozen v5 cohort unexpectedly contains {explicit_count} direct pressor-term notes."
        )

    set_flags = (
        df.groupby("match_set")[["strict_treatment_intent", "broad_management_language"]]
        .max()
        .astype(bool)
    )
    strict_clean_sets = set_flags.index[~set_flags["strict_treatment_intent"]]
    broad_clean_sets = set_flags.index[~set_flags["broad_management_language"]]

    subsets = {
        "full_frozen_v5": df,
        "no_strict_treatment_intent_complete_sets": df[df["match_set"].isin(strict_clean_sets)].copy(),
        "no_broad_management_language_complete_sets": df[df["match_set"].isin(broad_clean_sets)].copy(),
    }

    for name, d in subsets.items():
        sets = int(d["match_set"].nunique())
        if sets < max(args.folds * 5, 50):
            raise RuntimeError(f"Subset {name} retained only {sets} complete matched sets.")

    results = {}
    total = len(subsets)
    update_progress(
        current=0,
        total=total,
        phase="treatment_language_sensitivity",
        message="Starting treatment-language matched-set sensitivities",
        unit="subset",
    )
    for i, (name, d) in enumerate(subsets.items(), start=1):
        results[name] = evaluate_subset(
            d,
            name,
            folds=args.folds,
            repeats=args.repeats,
            n_boot=args.bootstrap_replicates,
            seed=args.seed + i * 100,
        )
        update_progress(
            current=i,
            total=total,
            phase="treatment_language_sensitivity",
            message=f"Completed {name}",
            unit="subset",
        )

    report = {
        "analysis": (
            "Residual treatment-language sensitivity on the frozen v5 complete-matched cohort."
        ),
        "cohort_guardrail": (
            "The frozen v5 cohort builder already excluded notes containing direct vasopressor, "
            "pressor, drug-name, adrenaline, or vasoactive terms before matching. This analysis "
            "therefore targets broader residual hemodynamic management wording."
        ),
        "direct_pressor_terms_confirmed_absent": explicit_count == 0,
        "n_full": int(len(df)),
        "match_sets_full": int(df["match_set"].nunique()),
        "language_categories": {
            "strict": list(STRICT_PATTERNS.keys()),
            "broad_additions": list(BROAD_ONLY_PATTERNS.keys()),
            "strict_definition": (
                "Action-oriented hemodynamic escalation/support language or explicit BP/MAP target wording."
            ),
            "broad_definition": (
                "Strict language plus fluid-resuscitation and invasive-access planning wording."
            ),
        },
        "row_level_prevalence_by_label": prevalence,
        "complete_set_retention": {
            "no_strict_treatment_intent": {
                "match_sets": int(len(strict_clean_sets)),
                "percent_of_sets": float(100.0 * len(strict_clean_sets) / df["match_set"].nunique()),
            },
            "no_broad_management_language": {
                "match_sets": int(len(broad_clean_sets)),
                "percent_of_sets": float(100.0 * len(broad_clean_sets) / df["match_set"].nunique()),
            },
        },
        "results": results,
        "contains_note_text": False,
        "contains_source_patient_identifiers": False,
        "patient_level_predictions_shared": False,
        "interpretation_guardrail": (
            "This is a conservative rule-based sensitivity, not a validated clinical NLP classifier. "
            "It asks whether semantic increment persists after excluding entire matched sets containing "
            "specified treatment-management wording. It does not prove that all treatment intent has "
            "been removed, and it intentionally does not flag hypotension or shock language alone."
        ),
    }

    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
