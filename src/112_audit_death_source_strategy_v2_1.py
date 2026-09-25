from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from runrelay_progress import update_progress


def collapse_note_category(value: object) -> str:
    x = str(value or "").strip().lower()
    if x in {"nursing", "nursing/other"}:
        return "nursing"
    if x in {"physician", "consult"}:
        return "physician"
    if x == "respiratory":
        return "respiratory"
    return "other"


def source_proxy_auc(
    df: pd.DataFrame,
    numeric_cols: list[str],
    cat_cols: list[str],
    *,
    add_missing_indicators: bool,
) -> float:
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import StratifiedGroupKFold
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder

    x = df[numeric_cols + cat_cols].copy()
    y = df["source_target"].astype(int).to_numpy()
    groups = df["subject_id"].to_numpy()

    transformers = []
    if numeric_cols:
        transformers.append(
            (
                "num",
                SimpleImputer(strategy="median", add_indicator=add_missing_indicators),
                numeric_cols,
            )
        )
    if cat_cols:
        transformers.append(
            (
                "cat",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
                    ]
                ),
                cat_cols,
            )
        )
    if not transformers:
        raise ValueError("at least one feature is required")

    pred = np.full(len(df), np.nan, dtype=float)
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=20260924)
    for tr, te in cv.split(x, y, groups=groups):
        pre = ColumnTransformer(transformers, remainder="drop")
        xtr = pre.fit_transform(x.iloc[tr])
        xte = pre.transform(x.iloc[te])
        model = HistGradientBoostingClassifier(
            learning_rate=0.05,
            max_iter=200,
            max_leaf_nodes=15,
            min_samples_leaf=50,
            l2_regularization=1.0,
            early_stopping=False,
            random_state=20260924,
        )
        model.fit(xtr, y[tr])
        pred[te] = model.predict_proba(xte)[:, 1]

    if np.isnan(pred).any():
        raise RuntimeError("source-proxy decomposition produced missing predictions")
    return float(roc_auc_score(y, pred))


def source_descriptives(idx: pd.DataFrame) -> dict:
    out = {}
    for source, g in idx.groupby("dbsource"):
        label = pd.to_numeric(g["label"], errors="raise").astype(int)
        has_note = pd.to_numeric(g["has_note"], errors="coerce").fillna(0).ne(0)
        cases = int(label.sum())
        controls = int(len(g) - cases)
        case_note = int((has_note & label.eq(1)).sum())
        control_note = int((has_note & label.eq(0)).sum())
        out[str(source)] = {
            "rows": int(len(g)),
            "unique_patients": int(g["subject_id"].nunique()),
            "cases": cases,
            "controls": controls,
            "prevalence": float(cases / len(g)) if len(g) else None,
            "note_available_rows": int(has_note.sum()),
            "note_coverage": float(has_note.mean()) if len(g) else None,
            "case_note_coverage": float(case_note / cases) if cases else None,
            "control_note_coverage": float(control_note / controls) if controls else None,
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Preregistration-only decomposition of CareVue/MetaVision recoverability in the v2.1 ICU-death cohort."
    )
    ap.add_argument("--local-root", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    local_root = Path(args.local_root).expanduser().resolve()
    out_path = Path(args.output).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    update_progress(current=1, total=4, phase="source_decomposition", message="Loading frozen death cohort and feature blocks", unit="stage")
    idx = pd.read_csv(local_root / "icu_death" / "population_index_local.csv", low_memory=False)
    idx["dbsource"] = idx["dbsource"].fillna("unknown").astype(str).str.strip().str.lower()
    idx["category_group"] = idx["category"].map(collapse_note_category)
    idx = idx[idx["dbsource"].isin(["carevue", "metavision"])].copy()
    idx["source_target"] = idx["dbsource"].eq("metavision").astype(int)

    struct = pd.read_csv(
        local_root / "icu_death" / "enhanced_structured_features_v2_1_local.csv",
        low_memory=False,
    ).drop(columns=["label"], errors="ignore")
    doc = pd.read_csv(
        local_root / "icu_death" / "documentation_behavior_v2_1_local.csv",
        low_memory=False,
    )

    death = idx[
        [
            "case_id", "subject_id", "icustay_id", "label", "dbsource", "source_target",
            "has_note", "note_age_at_landmark_hours", "category_group",
        ]
    ].merge(
        struct,
        on=["case_id", "subject_id", "icustay_id", "has_note"],
        how="left",
        validate="one_to_one",
    )
    death = death.merge(doc, on=["case_id", "icustay_id"], how="left", validate="one_to_one")

    feature_names = [
        c for c in struct.columns
        if c not in {"case_id", "subject_id", "icustay_id", "has_note", "sex"}
    ]
    core_numeric = [c for c in feature_names if c in death.columns and pd.api.types.is_numeric_dtype(death[c])]
    core_cat = ["sex"] if "sex" in death.columns else []

    doc_numeric = [
        c for c in death.columns
        if c.startswith("doc_") and pd.api.types.is_numeric_dtype(death[c])
    ]
    note_context_numeric = ["has_note", "note_age_at_landmark_hours"]

    update_progress(current=2, total=4, phase="source_decomposition", message="Computing label-free source-prediction decomposition", unit="stage")
    blocks = {
        "latest_note_category_only": ([], ["category_group"], False),
        "note_context_without_category": (note_context_numeric, [], True),
        "documentation_behavior_without_category": (doc_numeric + note_context_numeric, [], True),
        "documentation_behavior_with_category": (doc_numeric + note_context_numeric, ["category_group"], True),
        "core_structured_values_only": (core_numeric, core_cat, False),
        "core_structured_with_missingness": (core_numeric, core_cat, True),
        "core_plus_documentation_without_category": (
            core_numeric + doc_numeric + note_context_numeric,
            core_cat,
            True,
        ),
        "current_full_comparator": (
            core_numeric + doc_numeric + note_context_numeric,
            core_cat + ["category_group"],
            True,
        ),
    }
    aucs = {}
    for name, (num, cat, indicators) in blocks.items():
        aucs[name] = source_proxy_auc(
            death,
            list(dict.fromkeys(num)),
            list(dict.fromkeys(cat)),
            add_missing_indicators=indicators,
        )

    update_progress(current=3, total=4, phase="source_decomposition", message="Summarizing source-specific counts and structured missingness fingerprints", unit="stage")
    desc = source_descriptives(idx)

    missingness = {}
    for c in core_numeric:
        per_source = death.groupby("dbsource")[c].apply(lambda x: float(x.notna().mean())).to_dict()
        if "carevue" in per_source and "metavision" in per_source:
            missingness[c] = {
                "carevue_nonmissing": per_source["carevue"],
                "metavision_nonmissing": per_source["metavision"],
                "absolute_difference": abs(per_source["carevue"] - per_source["metavision"]),
            }
    top_missingness = dict(
        sorted(missingness.items(), key=lambda kv: kv[1]["absolute_difference"], reverse=True)[:15]
    )

    update_progress(current=4, total=4, phase="source_decomposition", message="Writing aggregate source-system design audit", unit="stage")
    report = {
        "analysis": "v2.1 ICU-death CareVue/MetaVision source-proxy decomposition",
        "outcome_performance_computed": False,
        "outcome_labels_used_only_for_descriptive_source_counts": True,
        "source_specific_cohort_counts": desc,
        "source_proxy_auroc_by_feature_block": aucs,
        "source_proxy_threshold": 0.80,
        "pooled_death_comparator_registration_blocked": bool(
            aucs["current_full_comparator"] > 0.80
        ),
        "top_structured_nonmissingness_differences": top_missingness,
        "design_interpretation": (
            "Source-prediction AUROC is a confounding diagnostic, not clinical outcome performance. "
            "If the pooled comparator remains strongly source-identifying, the death analysis must "
            "use a revised prespecified source-system strategy before split freezing and registration."
        ),
        "candidate_source_strategies_for_protocol_decision": [
            "MetaVision-only confirmatory ICU-death analysis with CareVue as prespecified replication/sensitivity.",
            "Separate CareVue and MetaVision death models with a prespecified endpoint-level combination rule.",
        ],
        "guardrails": [
            "No mortality AUROC, AUPRC, calibration, Brier score, log loss, or decision curve was computed.",
            "No semantic or lexical model was run.",
            "Source labels were used only for source-system diagnostics.",
            "Clinical outcome labels were used only for descriptive counts by source.",
        ],
    }
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
