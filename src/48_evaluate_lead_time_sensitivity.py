from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd

from common import resolve_root
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


def load_builder():
    path = Path(__file__).resolve().parent / "28_build_vasopressor_incremental_pilot.py"
    spec = importlib.util.spec_from_file_location("vasopressor_builder_v5", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load frozen cohort builder.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reconstruct_frozen_snapshots(root: Path, controls_per_case: int, seed: int, horizon: float) -> pd.DataFrame:
    b = load_builder()
    rng = random.Random(seed)

    events = b.first_vasopressor_events(root)
    icu = b.load_icustays(root)
    notes = b.load_bedside_notes(root, hadm_filter=set(icu["hadm_id"].astype(int)))
    note_icu = b.assign_icu(notes, icu)
    event_map = events.set_index("hadm_id")["event_time"]

    case_pool = note_icu.merge(events, on="hadm_id", how="inner")
    case_pool["hours_before_event"] = (
        case_pool["event_time"] - case_pool["note_time"]
    ).dt.total_seconds() / 3600.0
    case_pool = case_pool[
        (case_pool["hours_before_event"] > 0)
        & (case_pool["hours_before_event"] <= horizon)
        & (case_pool["event_time"] >= case_pool["intime"])
        & (case_pool["event_time"] <= case_pool["outtime"])
    ].copy()
    case_pool = (
        case_pool.sort_values(["subject_id", "event_time", "hours_before_event"])
        .groupby("subject_id", as_index=False)
        .first()
    )
    case_subjects = set(case_pool["subject_id"].astype(int))

    control_pool = note_icu[~note_icu["subject_id"].astype(int).isin(case_subjects)].copy()
    control_pool["first_event_time"] = control_pool["hadm_id"].map(event_map)
    control_pool["horizon_end"] = (
        control_pool["note_time"] + pd.to_timedelta(horizon, unit="h")
    )
    control_pool = control_pool[
        (
            control_pool["first_event_time"].isna()
            | (control_pool["first_event_time"] > control_pool["horizon_end"])
        )
        & (control_pool["outtime"] >= control_pool["horizon_end"])
    ].copy()
    control_pool = (
        control_pool.sort_values("note_time")
        .groupby(["subject_id", "hadm_id", "elapsed_bin_6h", "category"], as_index=False)
        .first()
    )

    used_control_subjects: set[int] = set()
    selected_controls = []
    matched_cases = []

    for case in case_pool.sort_values(
        ["dbsource", "category", "hours_since_icu", "subject_id"]
    ).itertuples(index=False):
        available = control_pool[
            ~control_pool["subject_id"].astype(int).isin(used_control_subjects)
        ].copy()
        if available.empty:
            break

        available["elapsed_distance"] = (
            available["hours_since_icu"] - case.hours_since_icu
        ).abs()
        priority = pd.Series(3, index=available.index, dtype=int)
        same_db = available["dbsource"].astype(str) == str(case.dbsource)
        same_cat = available["category"].astype(str) == str(case.category)
        close6 = available["elapsed_distance"] <= 6
        close12 = available["elapsed_distance"] <= 12
        priority.loc[same_db & same_cat & close6] = 0
        priority.loc[same_db & same_cat & close12 & (priority > 0)] = 1
        priority.loc[same_db & close6 & (priority > 1)] = 2
        available["match_priority"] = priority
        available = available[
            same_db & (available["elapsed_distance"] <= 12)
        ].copy()
        if available.empty:
            continue

        available["jitter"] = [rng.random() for _ in range(len(available))]
        available = available.sort_values(
            ["match_priority", "elapsed_distance", "jitter", "subject_id", "hadm_id"]
        )
        take = available.drop_duplicates("subject_id").head(controls_per_case)
        if len(take) < controls_per_case:
            continue

        matched_cases.append(case)
        selected_controls.append(take)
        used_control_subjects.update(take["subject_id"].astype(int).tolist())

    if not matched_cases:
        raise RuntimeError("Could not reconstruct any fully matched cases.")

    case_df = pd.DataFrame([x._asdict() for x in matched_cases])
    control_df = pd.concat(selected_controls, ignore_index=True)
    case_df["label"] = 1
    control_df["label"] = 0
    case_df["match_set"] = np.arange(1, len(case_df) + 1)
    control_df["match_set"] = np.repeat(
        np.arange(1, len(case_df) + 1),
        controls_per_case,
    )

    snapshots = pd.concat([case_df, control_df], ignore_index=True, sort=False).reset_index(drop=True)
    snapshots["case_id"] = [
        f"vasopilot_{'case' if y == 1 else 'control'}_{i:05d}"
        for i, y in enumerate(snapshots["label"].astype(int), start=1)
    ]
    subject_values = sorted(snapshots["subject_id"].astype(int).unique().tolist())
    subject_map = {sid: f"p{i:05d}" for i, sid in enumerate(subject_values, start=1)}
    snapshots["patient_group"] = snapshots["subject_id"].astype(int).map(subject_map)
    return snapshots


def load_frozen_cases(path: Path) -> pd.DataFrame:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            note = rec.get("model_state", {}).get("clinical_note")
            meta = rec.get("metadata", {})
            if not isinstance(note, str):
                raise RuntimeError("Frozen case lacks note text.")
            rows.append({
                "case_id": rec.get("case_id"),
                "label": int(meta.get("label")),
                "match_set": int(meta.get("match_set")),
                "patient_group": str(meta.get("patient_group")),
                "note_text": note,
            })
    out = pd.DataFrame(rows)
    if out.empty or out["case_id"].duplicated().any():
        raise RuntimeError("Frozen cases are empty or duplicated.")
    return out


def verify_reconstruction(recon: pd.DataFrame, features: pd.DataFrame, frozen_cases: pd.DataFrame) -> dict:
    if len(recon) != len(features) or len(recon) != len(frozen_cases):
        raise RuntimeError(
            f"Reconstruction row count mismatch: recon={len(recon)}, features={len(features)}, cases={len(frozen_cases)}."
        )

    r = recon[[
        "case_id", "label", "match_set", "patient_group", "category", "dbsource",
        "hours_since_icu", "text",
    ]].copy()
    f = features[[
        "case_id", "label", "match_set", "patient_group", "category", "dbsource",
        "hours_since_icu",
    ]].copy()
    c = frozen_cases.copy()

    merged = r.merge(f, on="case_id", suffixes=("_recon", "_frozen"), validate="one_to_one")
    if len(merged) != len(recon):
        raise RuntimeError("Reconstructed case IDs do not match frozen structured features.")

    exact_cols = ["label", "match_set", "patient_group", "category", "dbsource"]
    mismatch_counts = {}
    for col in exact_cols:
        a = merged[f"{col}_recon"].astype(str)
        b = merged[f"{col}_frozen"].astype(str)
        mismatch_counts[col] = int((a != b).sum())

    hours_diff = (
        pd.to_numeric(merged["hours_since_icu_recon"], errors="coerce")
        - pd.to_numeric(merged["hours_since_icu_frozen"], errors="coerce")
    ).abs()
    mismatch_counts["hours_since_icu_gt_1e-9"] = int((hours_diff > 1e-9).sum())

    note_check = r[["case_id", "text"]].merge(
        c[["case_id", "note_text"]],
        on="case_id",
        validate="one_to_one",
    )
    note_mismatch = int((note_check["text"].astype(str) != note_check["note_text"].astype(str)).sum())
    mismatch_counts["note_text"] = note_mismatch

    if any(v != 0 for v in mismatch_counts.values()):
        raise RuntimeError(f"Frozen cohort reconstruction mismatch: {mismatch_counts}")

    # Local digest only to make accidental changes detectable without exporting text.
    joined = "\n".join(
        f"{row.case_id}\t{hashlib.sha256(str(row.text).encode('utf-8')).hexdigest()}"
        for row in r.sort_values("case_id").itertuples(index=False)
    )
    return {
        "exact_case_id_overlap": True,
        "row_count": int(len(recon)),
        "mismatch_counts": mismatch_counts,
        "local_note_digest_sha256": hashlib.sha256(joined.encode("utf-8")).hexdigest(),
    }


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


def bootstrap_auc_diff(averaged: pd.DataFrame, a: str, b: str, n_boot: int, seed: int) -> dict:
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
    observed = float(roc_auc_score(wide["label"], wide[a]) - roc_auc_score(wide["label"], wide[b]))
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        sampled = rng.choice(match_sets, size=len(match_sets), replace=True)
        boot = pd.concat([by_set[k] for k in sampled], ignore_index=True)
        vals.append(float(roc_auc_score(boot["label"], boot[a]) - roc_auc_score(boot["label"], boot[b])))
    arr = np.asarray(vals, dtype=float)
    return {
        "difference": observed,
        "ci95": [float(np.quantile(arr, 0.025)), float(np.quantile(arr, 0.975))],
        "bootstrap_replicates": int(len(arr)),
        "cluster": "match_set",
    }


def evaluate_subset(df: pd.DataFrame, name: str, folds: int, repeats: int, n_boot: int, seed: int) -> dict:
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
        "case_id", "label", "match_set", "patient_group",
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
        return Pipeline([
            ("pre", ColumnTransformer(transformers, remainder="drop")),
            ("model", LogisticRegression(max_iter=3000, solver="liblinear", C=1.0)),
        ])

    repeat_rows = []
    oof_rows = []
    for repeat in range(repeats):
        cv = StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=seed + repeat)
        preds = {k: np.full(len(df), np.nan, dtype=float) for k in model_cols}
        for train_idx, test_idx in cv.split(df, y, groups=groups):
            for model_name, cols in model_cols.items():
                pipe = make_pipeline(cols)
                pipe.fit(df.iloc[train_idx][cols], y[train_idx])
                preds[model_name][test_idx] = pipe.predict_proba(df.iloc[test_idx][cols])[:, 1]

        for model_name, p in preds.items():
            if np.isnan(p).any():
                raise RuntimeError(f"Missing OOF predictions in {name}, repeat {repeat}, {model_name}.")
            repeat_rows.append({
                "repeat": repeat,
                "model": model_name,
                "auroc": float(roc_auc_score(y, p)),
                "auprc": float(average_precision_score(y, p)),
                "brier": float(brier_score_loss(y, p)),
            })
            for i, value in enumerate(p):
                oof_rows.append({
                    "repeat": repeat,
                    "model": model_name,
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
        boot[key] = bootstrap_auc_diff(averaged, a, b, n_boot=n_boot, seed=seed + 1000 + j)

    return {
        "subset": name,
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
        description="Lead-time sensitivity for semantic increment on the frozen v5 matched cohort."
    )
    ap.add_argument("--root", required=True)
    ap.add_argument("--features", required=True)
    ap.add_argument("--cases", required=True)
    ap.add_argument("--openjev", required=True)
    ap.add_argument("--laya", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--thresholds-hours", nargs="+", type=float, default=[0, 1, 2, 3, 4])
    ap.add_argument("--controls-per-case", type=int, default=3)
    ap.add_argument("--cohort-seed", type=int, default=20260920)
    ap.add_argument("--prediction-horizon-hours", type=float, default=6.0)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--repeats", type=int, default=20)
    ap.add_argument("--bootstrap-replicates", type=int, default=2000)
    ap.add_argument("--analysis-seed", type=int, default=20260920)
    args = ap.parse_args()

    root = resolve_root(args.root)
    features = pd.read_csv(Path(args.features).expanduser().resolve())
    frozen_cases = load_frozen_cases(Path(args.cases).expanduser().resolve())

    update_progress(
        current=0,
        total=len(args.thresholds_hours) + 1,
        phase="lead_time_reconstruction",
        message="Reconstructing frozen v5 matched snapshots locally",
        unit="stage",
    )
    recon = reconstruct_frozen_snapshots(
        root,
        controls_per_case=args.controls_per_case,
        seed=args.cohort_seed,
        horizon=args.prediction_horizon_hours,
    )
    verification = verify_reconstruction(recon, features, frozen_cases)

    case_leads = recon.loc[
        recon["label"].astype(int) == 1,
        ["match_set", "hours_before_event"],
    ].copy()
    if case_leads["match_set"].duplicated().any() or len(case_leads) != recon["match_set"].nunique():
        raise RuntimeError("Case lead-time reconstruction does not have one case per matched set.")

    lead = case_leads["hours_before_event"].astype(float)
    lead_summary = {
        "n_cases": int(len(lead)),
        "min": float(lead.min()),
        "p05": float(lead.quantile(0.05)),
        "p25": float(lead.quantile(0.25)),
        "median": float(lead.median()),
        "p75": float(lead.quantile(0.75)),
        "p95": float(lead.quantile(0.95)),
        "max": float(lead.max()),
    }

    oj = load_semantics(Path(args.openjev).expanduser().resolve(), "openjev")
    ly = load_semantics(Path(args.laya).expanduser().resolve(), "laya")
    df = features.merge(oj, on="case_id", how="inner").merge(ly, on="case_id", how="inner")
    if len(df) != len(features):
        raise RuntimeError(f"Expected {len(features)} complete rows after semantic merge but got {len(df)}.")

    results = {}
    retention = {}
    thresholds = sorted(set(float(x) for x in args.thresholds_hours))
    for i, threshold in enumerate(thresholds, start=1):
        keep_sets = case_leads.loc[
            case_leads["hours_before_event"].astype(float) >= threshold,
            "match_set",
        ].astype(int)
        sub = df[df["match_set"].astype(int).isin(set(keep_sets))].copy()
        key = f"case_note_at_least_{threshold:g}h_before_event"
        retention[key] = {
            "threshold_hours": threshold,
            "match_sets": int(len(keep_sets)),
            "percent_of_full_sets": float(100.0 * len(keep_sets) / len(case_leads)),
        }
        if len(keep_sets) < max(args.folds * 5, 50):
            raise RuntimeError(f"Lead-time threshold {threshold:g}h retained only {len(keep_sets)} matched sets.")
        results[key] = evaluate_subset(
            sub,
            key,
            folds=args.folds,
            repeats=args.repeats,
            n_boot=args.bootstrap_replicates,
            seed=args.analysis_seed,
        )
        update_progress(
            current=i,
            total=len(thresholds) + 1,
            phase="lead_time_sensitivity",
            message=f"Completed threshold >= {threshold:g} hours",
            unit="stage",
        )

    report = {
        "analysis": "Case-note lead-time sensitivity on the frozen v5 complete-matched cohort.",
        "design": (
            "This is a restriction sensitivity using the originally selected frozen v5 note for each case. "
            "For threshold t, the entire 1:3 matched set is retained only when the case note was prospectively "
            "available at least t hours before first vasopressor initiation. Notes are not re-anchored or reselected."
        ),
        "prediction_horizon_hours": float(args.prediction_horizon_hours),
        "thresholds_hours": thresholds,
        "frozen_cohort_verification": verification,
        "case_note_lead_time_hours": lead_summary,
        "retention": retention,
        "results": results,
        "contains_note_text": False,
        "contains_source_patient_identifiers": False,
        "patient_level_predictions_shared": False,
        "interpretation_guardrail": (
            "Persistence of semantic increment at longer thresholds reduces concern that the association is confined "
            "to immediately pre-treatment documentation. Because this analysis restricts the frozen selected-note cohort "
            "rather than selecting new earlier notes at each landmark, it does not estimate performance of a newly "
            "anchored 1h/2h/3h/4h prediction system."
        ),
    }

    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    update_progress(
        current=len(thresholds) + 1,
        total=len(thresholds) + 1,
        phase="complete",
        message="Lead-time sensitivity complete",
        unit="stage",
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
