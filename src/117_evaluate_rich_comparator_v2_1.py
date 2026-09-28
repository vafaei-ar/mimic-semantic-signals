from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

from registration_gate import require_osf_registration
from runrelay_progress import update_progress


OUTCOMES = ("invasive_ventilation", "renal_replacement_therapy", "icu_death")
REPEAT_SEEDS = (20260924, 20260925, 20260926, 20260927, 20260928)
FOLDS = 5


def load_numbered_module(filename: str, name: str):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {filename}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


legacy_metrics = load_numbered_module(
    "107_evaluate_enhanced_structured_baseline_v2_1.py",
    "enhanced_structured_baseline_v2_1_metrics",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_hgb(seed: int):
    from sklearn.ensemble import HistGradientBoostingClassifier

    return HistGradientBoostingClassifier(
        loss="log_loss",
        learning_rate=0.05,
        max_iter=300,
        max_leaf_nodes=15,
        min_samples_leaf=50,
        l2_regularization=1.0,
        early_stopping=False,
        random_state=int(seed),
    )


def load_frozen_splits(
    df: pd.DataFrame,
    outcome: str,
    base: Path,
    split_manifest: dict,
):
    expected = split_manifest["outcomes"].get(outcome)
    if not isinstance(expected, dict):
        raise RuntimeError(f"{outcome}: missing from split manifest")

    observed_counts = {
        "rows": int(len(df)),
        "cases": int(df["label"].astype(int).sum()),
        "controls": int(len(df) - df["label"].astype(int).sum()),
        "unique_patients": int(df["subject_id"].nunique()),
    }
    for key, value in observed_counts.items():
        if int(expected[key]) != int(value):
            raise RuntimeError(
                f"{outcome}: {key}={value} differs from frozen split manifest {expected[key]}"
            )

    split_path = base / outcome / "enhanced_structured_cv_splits_v2_1_local.csv"
    observed_hash = sha256_file(split_path)
    if observed_hash != expected["split_sha256"]:
        raise RuntimeError(
            f"{outcome}: split hash mismatch {observed_hash} != {expected['split_sha256']}"
        )

    split_df = pd.read_csv(split_path, low_memory=False)
    required = {"case_id", "subject_id"} | {
        f"repeat_{i}_fold" for i in range(1, len(REPEAT_SEEDS) + 1)
    }
    missing = required - set(split_df.columns)
    if missing:
        raise RuntimeError(
            f"{outcome}: split file missing columns {sorted(missing)}"
        )
    if split_df["case_id"].duplicated().any():
        raise RuntimeError(f"{outcome}: duplicate case_id in frozen split file")

    aligned = split_df.set_index("case_id").reindex(df["case_id"].astype(str))
    if aligned.isna().all(axis=1).any():
        raise RuntimeError(f"{outcome}: feature rows missing from frozen split file")

    split_subject = pd.to_numeric(aligned["subject_id"], errors="raise").to_numpy()
    feature_subject = pd.to_numeric(df["subject_id"], errors="raise").to_numpy()
    if not np.array_equal(split_subject, feature_subject):
        raise RuntimeError(f"{outcome}: subject_id mismatch against frozen split file")

    return aligned.reset_index(drop=True), observed_hash


def prepare_rich_features(
    structured: pd.DataFrame,
    context: pd.DataFrame,
    outcome: str,
    context_freeze: dict,
):
    key_cols = ["case_id", "subject_id", "icustay_id"]
    for name, frame in (("structured", structured), ("context", context)):
        missing = [c for c in key_cols if c not in frame.columns]
        if missing:
            raise RuntimeError(f"{outcome}: {name} file missing keys {missing}")

    structured = structured.copy()
    context = context.copy()
    structured["case_id"] = structured["case_id"].astype(str)
    context["case_id"] = context["case_id"].astype(str)

    if structured["case_id"].duplicated().any() or context["case_id"].duplicated().any():
        raise RuntimeError(f"{outcome}: duplicate case_id in rich-comparator inputs")

    merged = structured.merge(
        context,
        on=key_cols,
        how="left",
        validate="one_to_one",
        suffixes=("", "_context"),
    )
    if len(merged) != len(structured):
        raise RuntimeError(f"{outcome}: rich-comparator merge changed row count")

    context_ids = set(context["case_id"])
    if not set(merged["case_id"]).issubset(context_ids):
        raise RuntimeError(f"{outcome}: missing preregistration context rows")

    id_cols = {"case_id", "subject_id", "icustay_id", "label", "has_note"}
    structured_cols = [c for c in structured.columns if c not in id_cols]
    if len(structured_cols) != 34:
        raise RuntimeError(
            f"{outcome}: expected 34 structured features, found {len(structured_cols)}"
        )

    x = pd.DataFrame(index=merged.index)

    for col in structured_cols:
        if col == "sex":
            sex = merged[col].astype(str).str.upper()
            unexpected = sorted(set(sex.dropna().unique()) - {"M", "F"})
            if unexpected:
                raise RuntimeError(f"{outcome}: unexpected sex values {unexpected}")
            x["sex_male"] = sex.map({"M": 1.0, "F": 0.0}).astype(float)
        else:
            x[col] = pd.to_numeric(merged[col], errors="coerce")

    freeze_doc = context_freeze["documentation_behavior"]["features"]
    numeric_context = [
        "has_note",
        "note_age_at_landmark_hours",
        *freeze_doc,
        "treat_fio2_last_6h",
        "treat_oxygen_flow_last_6h",
        "treat_high_flow_any_6h",
        "treat_niv_any_6h",
        "treat_vasoactive_any",
        "treat_vasoactive_agent_count",
        "treat_sedative_any",
        "treat_sedative_agent_count",
    ]
    if outcome == "icu_death":
        numeric_context += [
            "code_status_available",
            "code_status_limitation",
            "code_status_comfort_or_no_cpr",
            "code_status_other",
        ]

    missing_context = [c for c in numeric_context + ["category_group"] if c not in merged.columns]
    if missing_context:
        raise RuntimeError(f"{outcome}: missing registered context features {missing_context}")

    for col in numeric_context:
        x[col] = pd.to_numeric(merged[col], errors="coerce")

    categories = merged["category_group"].fillna("no_note").astype(str).str.strip().str.lower()
    allowed = ["nursing", "physician", "respiratory", "other", "no_note"]
    unexpected = sorted(set(categories.unique()) - set(allowed))
    if unexpected:
        raise RuntimeError(f"{outcome}: unexpected collapsed note categories {unexpected}")
    for level in allowed:
        x[f"note_category_{level}"] = categories.eq(level).astype(float)

    expected_feature_count = 34 + len(numeric_context) + len(allowed)
    if x.shape[1] != expected_feature_count:
        raise RuntimeError(
            f"{outcome}: rich comparator encoded feature count {x.shape[1]} "
            f"!= expected {expected_feature_count}"
        )

    return merged, x, list(x.columns)


def scalar_summary(rows: list[dict]) -> dict:
    keys = [
        "auroc",
        "auprc",
        "brier",
        "log_loss",
        "calibration_in_the_large",
        "joint_recalibration_intercept",
        "calibration_slope",
        "ece_10_equal_width_bins",
        "ece_10_quantile_bins",
    ]
    out = {}
    for key in keys:
        vals = np.asarray([float(r[key]) for r in rows], dtype=float)
        out[key] = {
            "mean": float(vals.mean()),
            "sd": float(vals.std(ddof=1)) if len(vals) > 1 else 0.0,
            "min": float(vals.min()),
            "max": float(vals.max()),
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Evaluate the registered v2.1 rich comparator only, before semantic inference. "
            "This preparatory run does not compute the registered paired refit-bootstrap delta."
        )
    )
    ap.add_argument("--base", required=True)
    ap.add_argument("--split-manifest", required=True)
    ap.add_argument("--context-freeze", required=True)
    ap.add_argument("--analysis-populations", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--outcome", choices=OUTCOMES, required=True)
    args = ap.parse_args()

    require_osf_registration()

    base = Path(args.base).expanduser().resolve()
    split_manifest_path = Path(args.split_manifest).expanduser().resolve()
    split_manifest = json.loads(split_manifest_path.read_text(encoding="utf-8"))
    context_freeze_path = Path(args.context_freeze).expanduser().resolve()
    context_freeze = json.loads(context_freeze_path.read_text(encoding="utf-8"))
    population_contract_path = Path(args.analysis_populations).expanduser().resolve()
    population_contract = json.loads(population_contract_path.read_text(encoding="utf-8"))
    outcome = args.outcome
    outcome_contract = population_contract["confirmatory_outcomes"][outcome]
    source = str(outcome_contract["source"]).strip().lower()

    structured_path = base / outcome / "enhanced_structured_features_v2_1_local.csv"
    context_name = (
        "preregistration_context_features_v2_1_local.csv"
    )
    context_path = base / outcome / context_name

    structured = pd.read_csv(structured_path, low_memory=False)
    context = pd.read_csv(context_path, low_memory=False)

    # Enforce the registered source-specific analysis population before any fitting.
    index_path = base / outcome / "population_index_local.csv"
    idx = pd.read_csv(index_path, usecols=["case_id", "dbsource"], low_memory=False)
    idx["case_id"] = idx["case_id"].astype(str)
    idx["dbsource"] = idx["dbsource"].fillna("unknown").astype(str).str.strip().str.lower()
    structured["case_id"] = structured["case_id"].astype(str)
    structured = structured.merge(idx, on="case_id", how="left", validate="one_to_one")
    structured = structured[structured["dbsource"].eq(source)].drop(columns=["dbsource"]).reset_index(drop=True)

    observed = {
        "rows": int(len(structured)),
        "unique_patients": int(structured["subject_id"].nunique()),
        "cases": int(structured["label"].astype(int).sum()),
        "controls": int(len(structured) - structured["label"].astype(int).sum()),
    }
    for key, value in observed.items():
        if int(outcome_contract[key]) != int(value):
            raise RuntimeError(
                f"{outcome}/{source}: registered population mismatch for {key}: "
                f"observed {value}, expected {outcome_contract[key]}"
            )

    required = {"case_id", "subject_id", "icustay_id", "label"}
    missing = required - set(structured.columns)
    if missing:
        raise RuntimeError(f"{outcome}: structured input missing {sorted(missing)}")

    merged, x, feature_names = prepare_rich_features(
        structured, context, outcome, context_freeze
    )
    y = merged["label"].astype(int).to_numpy()
    groups = merged["subject_id"].to_numpy()

    frozen_splits, split_hash = load_frozen_splits(
        merged, outcome, base, split_manifest
    )

    preds = np.full((len(merged), len(REPEAT_SEEDS)), np.nan, dtype=float)
    folds = []
    repeat_metrics = []

    total = len(REPEAT_SEEDS) * FOLDS
    current = 0

    for ri, seed in enumerate(REPEAT_SEEDS, start=1):
        fold_assignment = pd.to_numeric(
            frozen_splits[f"repeat_{ri}_fold"], errors="raise"
        ).astype(int).to_numpy()

        check = pd.DataFrame({"subject_id": groups, "fold": fold_assignment})
        if (check.groupby("subject_id")["fold"].nunique() > 1).any():
            raise RuntimeError(f"{outcome}: patient crosses folds in repeat {ri}")

        for fold in range(1, FOLDS + 1):
            te = np.flatnonzero(fold_assignment == fold)
            tr = np.flatnonzero(fold_assignment != fold)
            model = build_hgb(int(seed) + fold)
            model.fit(x.iloc[tr], y[tr])
            preds[te, ri - 1] = model.predict_proba(x.iloc[te])[:, 1]

            folds.append(
                {
                    "repeat": int(ri),
                    "seed": int(seed),
                    "fold": int(fold),
                    "train_n": int(len(tr)),
                    "test_n": int(len(te)),
                    "train_cases": int(y[tr].sum()),
                    "test_cases": int(y[te].sum()),
                    "test_unique_patients": int(pd.Series(groups[te]).nunique()),
                }
            )
            current += 1
            update_progress(
                current=current,
                total=total,
                phase="v2_1_rich_comparator_crossfit",
                message=f"{outcome}: repeat {ri}/5, fold {fold}/5",
                unit="fold",
            )

        if np.isnan(preds[:, ri - 1]).any():
            raise RuntimeError(f"{outcome}: incomplete OOF predictions in repeat {ri}")
        metrics = legacy_metrics.basic_metrics(y, preds[:, ri - 1])
        repeat_metrics.append({"repeat": ri, "seed": int(seed), **metrics})

    primary_metrics = repeat_metrics[0]
    mean_prediction = preds.mean(axis=1)
    averaged_metrics = legacy_metrics.basic_metrics(y, mean_prediction)

    local_pred = merged[["case_id", "subject_id", "icustay_id", "label"]].copy()
    for ri in range(len(REPEAT_SEEDS)):
        local_pred[f"rich_comparator_repeat_{ri + 1}"] = preds[:, ri]
    local_pred["rich_comparator_prediction_mean"] = mean_prediction
    pred_path = base / outcome / "rich_comparator_predictions_v2_1_local.csv"
    local_pred.to_csv(pred_path, index=False)

    report = {
        "analysis": "Registered v2.1 rich comparator preparatory evaluation",
        "status": "completed",
        "outcome": outcome,
        "registration_id": "ahxn9",
        "registered_source": source,
        "analysis_population_contract_sha256": sha256_file(population_contract_path),
        "registered_comparator_only": True,
        "semantic_or_lexical_features_used": False,
        "inferential_role": (
            "Preparatory comparator-only OOF evaluation. The registered H1-H3 delta-AUROC "
            "and its 500-replicate paired patient-cluster refit-bootstrap interval are not "
            "computed here and must be computed later with comparator and augmented models refit together."
        ),
        "n": int(len(merged)),
        "cases": int(y.sum()),
        "controls": int(len(y) - y.sum()),
        "prevalence": float(y.mean()),
        "frozen_split_sha256": split_hash,
        "split_manifest_sha256": sha256_file(split_manifest_path),
        "context_freeze_sha256": sha256_file(context_freeze_path),
        "structured_input_sha256": sha256_file(structured_path),
        "context_input_sha256": sha256_file(context_path),
        "model": {
            "classifier": "HistGradientBoostingClassifier",
            "learning_rate": 0.05,
            "max_iter": 300,
            "max_leaf_nodes": 15,
            "min_samples_leaf": 50,
            "l2_regularization": 1.0,
            "early_stopping": False,
            "native_missing_value_handling": True,
        },
        "feature_count_encoded": int(len(feature_names)),
        "feature_names_encoded": feature_names,
        "folds": folds,
        "primary_repeat_metrics": primary_metrics,
        "repeat_metrics": repeat_metrics,
        "repeat_variability": scalar_summary(repeat_metrics),
        "repeat_averaged_oof_metrics": averaged_metrics,
        "bootstrap": None,
        "local_prediction_file": str(pred_path),
        "guardrails": [
            "Uses the registered rich comparator only.",
            "No semantic or lexical features are used.",
            "No bootstrap interval is computed in this preparatory comparator-only run.",
            "The later H1-H3 paired refit bootstrap must refit comparator and augmented models together.",
            "All five partitions use the pre-frozen patient-grouped split files.",
            "Row-level predictions remain local.",
        ],
    }

    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
