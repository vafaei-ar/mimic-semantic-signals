from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score

from preregistration_stats import patient_cluster_refit_indices
from registration_gate import require_osf_registration
from runrelay_progress import update_progress


OUTCOME = "icu_death"
REPEAT_SEEDS = (20260924, 20260925, 20260926, 20260927, 20260928)
FOLDS = 5
SEMANTIC_NAMES = (
    "overall_clinician_concern",
    "worsening_trajectory",
    "respiratory_concern",
    "hemodynamic_concern",
    "diagnostic_uncertainty",
    "reassuring_stability",
)


def load_numbered_module(filename: str, name: str):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {filename}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rich = load_numbered_module("117_evaluate_rich_comparator_v2_1.py", "rich_v2_1")
legacy_metrics = rich.legacy_metrics


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_semantics(path: Path) -> pd.DataFrame:
    rows = []
    seen = set()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            rec = json.loads(line)
            cid = str(rec.get("case_id"))
            if not cid or cid == "None" or cid in seen:
                raise RuntimeError("Missing or duplicate case_id in Open-Jev inference output")
            seen.add(cid)
            if rec.get("status") != "ok":
                raise RuntimeError(f"Open-Jev inference status not ok for case_id={cid}")
            ans = (rec.get("response") or {}).get("answers") or {}
            row = {"case_id": cid}
            for name in SEMANTIC_NAMES:
                item = ans.get(name)
                value = item.get("noul") if isinstance(item, dict) else None
                if not isinstance(value, (int, float)) or not np.isfinite(float(value)):
                    raise RuntimeError(f"Missing/non-finite semantic score {name} for case_id={cid}")
                row[name] = float(value)
            rows.append(row)
    if not rows:
        raise RuntimeError("No Open-Jev inference rows found")
    return pd.DataFrame(rows)


def fit_pair(x_base: pd.DataFrame, x_aug: pd.DataFrame, y: np.ndarray, train_idx, test_idx):
    base = rich.build_hgb(20260924)
    aug = rich.build_hgb(20260924)
    base.fit(x_base.iloc[train_idx], y[train_idx])
    aug.fit(x_aug.iloc[train_idx], y[train_idx])
    pb = base.predict_proba(x_base.iloc[test_idx])[:, 1]
    pa = aug.predict_proba(x_aug.iloc[test_idx])[:, 1]
    if not np.isfinite(pb).all() or not np.isfinite(pa).all():
        raise RuntimeError("Non-finite HGB predictions")
    return pb, pa


def crossfit_pair(x_base, x_aug, y, folds, *, progress_prefix=None):
    pb = np.full(len(y), np.nan, dtype=float)
    pa = np.full(len(y), np.nan, dtype=float)
    for fold in range(1, FOLDS + 1):
        te = np.flatnonzero(folds == fold)
        tr = np.flatnonzero(folds != fold)
        if len(te) == 0:
            raise RuntimeError(f"Empty held-out fold {fold}")
        if y[tr].sum() == 0 or y[tr].sum() == len(tr):
            raise RuntimeError(f"Degenerate training labels in fold {fold}")
        p0, p1 = fit_pair(x_base, x_aug, y, tr, te)
        pb[te] = p0
        pa[te] = p1
    if np.isnan(pb).any() or np.isnan(pa).any():
        raise RuntimeError("Incomplete OOF predictions")
    return pb, pa


def metric_pair(y, pb, pa):
    mb = legacy_metrics.basic_metrics(y, pb)
    ma = legacy_metrics.basic_metrics(y, pa)
    keys = [
        "auroc", "auprc", "brier", "log_loss",
        "calibration_in_the_large", "joint_recalibration_intercept",
        "calibration_slope", "ece_10_equal_width_bins", "ece_10_quantile_bins",
    ]
    delta = {k: float(ma[k]) - float(mb[k]) for k in keys}
    return mb, ma, delta


def simple_bootstrap_metrics(y, pb, pa):
    return {
        "delta_auroc": float(roc_auc_score(y, pa) - roc_auc_score(y, pb)),
        "delta_auprc": float(average_precision_score(y, pa) - average_precision_score(y, pb)),
        "delta_brier": float(brier_score_loss(y, pa) - brier_score_loss(y, pb)),
        "delta_log_loss": float(log_loss(y, pa, labels=[0, 1]) - log_loss(y, pb, labels=[0, 1])),
    }


def decision_curve_net_benefit(y, p, thresholds):
    n = len(y)
    out = {}
    for t in thresholds:
        pred = p >= float(t)
        tp = int(np.sum(pred & (y == 1)))
        fp = int(np.sum(pred & (y == 0)))
        nb = tp / n - fp / n * (float(t) / (1.0 - float(t)))
        out[str(t)] = float(nb)
    return out


def percentile_ci(values):
    a = np.asarray(values, dtype=float)
    lo, hi = np.quantile(a, [0.025, 0.975])
    return [float(lo), float(hi)]


def main():
    ap = argparse.ArgumentParser(description="Registered v2.1 H4 ICU death six-construct rich comparator + stripped Open-Jev evaluation.")
    ap.add_argument("--base", required=True)
    ap.add_argument("--split-manifest", required=True)
    ap.add_argument("--context-freeze", required=True)
    ap.add_argument("--analysis-populations", required=True)
    ap.add_argument("--preanalysis-clarifications", required=True)
    ap.add_argument("--semantics", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    require_osf_registration()

    base = Path(args.base).expanduser().resolve()
    split_manifest_path = Path(args.split_manifest).expanduser().resolve()
    split_manifest = json.loads(split_manifest_path.read_text(encoding="utf-8"))
    context_freeze_path = Path(args.context_freeze).expanduser().resolve()
    context_freeze = json.loads(context_freeze_path.read_text(encoding="utf-8"))
    population_path = Path(args.analysis_populations).expanduser().resolve()
    population = json.loads(population_path.read_text(encoding="utf-8"))
    clarify_path = Path(args.preanalysis_clarifications).expanduser().resolve()
    clarifications = json.loads(clarify_path.read_text(encoding="utf-8"))
    semantic_path = Path(args.semantics).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()

    expected = population["confirmatory_outcomes"][OUTCOME]
    source = str(expected["source"]).strip().lower()

    structured_path = base / OUTCOME / "enhanced_structured_features_v2_1_local.csv"
    context_path = base / OUTCOME / "preregistration_context_features_v2_1_local.csv"
    index_path = base / OUTCOME / "population_index_local.csv"

    structured = pd.read_csv(structured_path, low_memory=False)
    context = pd.read_csv(context_path, low_memory=False)
    idx = pd.read_csv(index_path, usecols=["case_id", "dbsource"], low_memory=False)

    structured["case_id"] = structured["case_id"].astype(str)
    idx["case_id"] = idx["case_id"].astype(str)
    idx["dbsource"] = idx["dbsource"].fillna("unknown").astype(str).str.strip().str.lower()
    structured = structured.merge(idx, on="case_id", how="left", validate="one_to_one")
    structured = structured[structured["dbsource"].eq(source)].drop(columns=["dbsource"]).reset_index(drop=True)

    observed = {
        "rows": int(len(structured)),
        "unique_patients": int(structured["subject_id"].nunique()),
        "cases": int(structured["label"].astype(int).sum()),
        "controls": int(len(structured) - structured["label"].astype(int).sum()),
    }
    for key, value in observed.items():
        if int(expected[key]) != int(value):
            raise RuntimeError(f"Registered population mismatch {key}: {value} != {expected[key]}")

    merged, x_base, base_names = rich.prepare_rich_features(structured, context, OUTCOME, context_freeze)
    y = merged["label"].astype(int).to_numpy()
    groups = merged["subject_id"].to_numpy()
    frozen_splits, split_hash = rich.load_frozen_splits(merged, OUTCOME, base, split_manifest)

    sem = load_semantics(semantic_path)
    sem_ids = set(sem["case_id"])
    merged_ids = set(merged["case_id"].astype(str))
    if not sem_ids.issubset(merged_ids):
        raise RuntimeError("Semantic inference contains case_ids outside registered MetaVision ICU-death population")

    has_note = pd.to_numeric(merged["has_note"], errors="raise").astype(int)
    note_ids = set(merged.loc[has_note.eq(1), "case_id"].astype(str))
    if sem_ids != note_ids:
        missing = len(note_ids - sem_ids)
        extra = len(sem_ids - note_ids)
        raise RuntimeError(f"Semantic/note availability mismatch: missing={missing}, extra={extra}")

    sem = sem.set_index("case_id").reindex(merged["case_id"].astype(str))
    sem_matrix = sem.loc[:, SEMANTIC_NAMES].astype(float).reset_index(drop=True)
    has_note = has_note.reset_index(drop=True)
    if sem_matrix.loc[has_note.eq(1)].isna().any().any():
        raise RuntimeError("Note-available row has incomplete semantic scores")
    if sem_matrix.loc[has_note.eq(0)].notna().any().any():
        raise RuntimeError("No-note row unexpectedly has semantic scores")

    x_aug = pd.concat([x_base.reset_index(drop=True), sem_matrix.reset_index(drop=True)], axis=1)

    repeat_results = []
    repeat_predictions = []
    for ri, seed in enumerate(REPEAT_SEEDS, start=1):
        folds = pd.to_numeric(frozen_splits[f"repeat_{ri}_fold"], errors="raise").astype(int).to_numpy()
        check = pd.DataFrame({"subject_id": groups, "fold": folds})
        if (check.groupby("subject_id")["fold"].nunique() > 1).any():
            raise RuntimeError(f"Patient crosses folds in repeat {ri}")
        pb, pa = crossfit_pair(x_base, x_aug, y, folds)
        mb, ma, delta = metric_pair(y, pb, pa)
        repeat_results.append({
            "repeat": ri,
            "seed": int(seed),
            "comparator": mb,
            "augmented": ma,
            "delta": delta,
        })
        repeat_predictions.append((pb, pa))
        update_progress(
            current=ri,
            total=5,
            phase="v2_1_h1_point_estimates",
            message=f"ICU death H4 repeat {ri}/5 complete",
            unit="repeat",
        )

    primary_pb, primary_pa = repeat_predictions[0]
    primary_folds = pd.to_numeric(frozen_splits["repeat_1_fold"], errors="raise").astype(int).to_numpy()
    observed_delta = float(roc_auc_score(y, primary_pa) - roc_auc_score(y, primary_pb))

    target = int(clarifications["bootstrap_failure_rule"]["target_valid_replicates"])
    max_frac = float(clarifications["bootstrap_failure_rule"]["maximum_degenerate_replacement_fraction"])
    max_replacements = int(np.floor(target * max_frac))
    seed_sequence = np.random.SeedSequence(20260924)
    child_seeds = seed_sequence.spawn(target + max_replacements + 1)

    boot = []
    dca_boot = {str(t): [] for t in clarifications["decision_curve"]["thresholds"]}
    replacements = []
    child_index = 0

    while len(boot) < target:
        if child_index >= len(child_seeds):
            raise RuntimeError("Exhausted deterministic bootstrap replacement seeds")
        child = child_seeds[child_index]
        child_index += 1
        rng = np.random.default_rng(child)

        split_indices = patient_cluster_refit_indices(groups, primary_folds, rng)
        eval_y, eval_pb, eval_pa = [], [], []

        for fold in range(1, FOLDS + 1):
            tr, te = split_indices[fold]
            if len(te) == 0:
                raise RuntimeError(f"Bootstrap replicate {len(boot)+1}: empty fold {fold}")
            if y[tr].sum() == 0 or y[tr].sum() == len(tr):
                raise RuntimeError(f"Bootstrap replicate {len(boot)+1}: degenerate training fold {fold}")
            p0, p1 = fit_pair(x_base, x_aug, y, tr, te)
            eval_y.append(y[te])
            eval_pb.append(p0)
            eval_pa.append(p1)

        yy = np.concatenate(eval_y)
        pb = np.concatenate(eval_pb)
        pa = np.concatenate(eval_pa)

        if yy.sum() == 0 or yy.sum() == len(yy):
            replacements.append({
                "child_seed_index": child_index - 1,
                "reason": "single_class_heldout_evaluation",
            })
            if len(replacements) > max_replacements:
                raise RuntimeError("Degenerate bootstrap replacement fraction exceeded frozen 5% limit")
            continue

        metrics = simple_bootstrap_metrics(yy, pb, pa)
        nb0 = decision_curve_net_benefit(yy, pb, clarifications["decision_curve"]["thresholds"])
        nb1 = decision_curve_net_benefit(yy, pa, clarifications["decision_curve"]["thresholds"])
        for t in dca_boot:
            dca_boot[t].append(float(nb1[t] - nb0[t]))
        boot.append(metrics)

        if len(boot) % 5 == 0 or len(boot) == target:
            update_progress(
                current=len(boot),
                total=target,
                phase="v2_1_h1_refit_bootstrap",
                message=f"ICU death H4 refit bootstrap {len(boot)}/{target}",
                unit="replicate",
            )

    boot_summary = {}
    for key in ("delta_auroc", "delta_auprc", "delta_brier", "delta_log_loss"):
        values = [r[key] for r in boot]
        boot_summary[key] = {
            "mean": float(np.mean(values)),
            "sd": float(np.std(values, ddof=1)),
            "ci95_percentile": percentile_ci(values),
        }

    dca_primary_base = decision_curve_net_benefit(y, primary_pb, clarifications["decision_curve"]["thresholds"])
    dca_primary_aug = decision_curve_net_benefit(y, primary_pa, clarifications["decision_curve"]["thresholds"])
    dca = {}
    for t in dca_boot:
        dca[t] = {
            "comparator_net_benefit": dca_primary_base[t],
            "augmented_net_benefit": dca_primary_aug[t],
            "delta_net_benefit": float(dca_primary_aug[t] - dca_primary_base[t]),
            "delta_ci95_percentile": percentile_ci(dca_boot[t]),
        }

    pred_path = base / OUTCOME / "h4_six_construct_death_predictions_v2_1_local.csv"
    local_pred = merged[["case_id", "subject_id", "icustay_id", "label"]].copy()
    for ri, (pb, pa) in enumerate(repeat_predictions, start=1):
        local_pred[f"comparator_repeat_{ri}"] = pb
        local_pred[f"augmented_openjev_repeat_{ri}"] = pa
    local_pred.to_csv(pred_path, index=False)

    split_deltas = [float(r["delta"]["auroc"]) for r in repeat_results]
    report = {
        "analysis": "Registered v2.1 H4 ICU death six-construct rich comparator + stripped Open-Jev",
        "status": "completed",
        "registration_id": "ahxn9",
        "doi": "10.17605/OSF.IO/AHXN9",
        "outcome": OUTCOME,
        "source": source,
        "n": int(len(y)),
        "cases": int(y.sum()),
        "controls": int(len(y) - y.sum()),
        "note_available_rows_with_complete_openjev": int(has_note.sum()),
        "semantic_constructs": list(SEMANTIC_NAMES),
        "model_family": "HistGradientBoostingClassifier",
        "hgb_specification": {
            "learning_rate": 0.05,
            "max_iter": 300,
            "max_leaf_nodes": 15,
            "min_samples_leaf": 50,
            "l2_regularization": 1.0,
            "early_stopping": False,
            "random_state": 20260924,
        },
        "primary_estimand": "repeat-1 OOF delta_AUROC = AUROC(rich comparator + stripped Open-Jev) - AUROC(rich comparator)",
        "primary_repeat": repeat_results[0],
        "split_stability": {
            "repeat_delta_auroc": split_deltas,
            "repeats_2_to_5_range": [
                float(min(split_deltas[1:])),
                float(max(split_deltas[1:])),
            ],
            "all_five_range": [float(min(split_deltas)), float(max(split_deltas))],
        },
        "primary_refit_bootstrap": {
            "valid_replicates": int(len(boot)),
            "target_valid_replicates": target,
            "replacement_count": len(replacements),
            "replacement_log": replacements,
            "bootstrap_unit": "source_patient",
            "fixed_partition": "repeat_1",
            "seed_sequence": 20260924,
            "interval_type": "two-sided 95% percentile",
            "delta_auroc_observed": observed_delta,
            "delta_auroc_ci95": boot_summary["delta_auroc"]["ci95_percentile"],
            "secondary_delta_summaries": {
                k: v for k, v in boot_summary.items() if k != "delta_auroc"
            },
        },
        "decision_curve": dca,
        "hashes": {
            "structured_input_sha256": sha256_file(structured_path),
            "context_input_sha256": sha256_file(context_path),
            "semantic_input_sha256": sha256_file(semantic_path),
            "split_sha256": split_hash,
            "split_manifest_sha256": sha256_file(split_manifest_path),
            "context_freeze_sha256": sha256_file(context_freeze_path),
            "analysis_population_contract_sha256": sha256_file(population_path),
            "preanalysis_clarifications_sha256": sha256_file(clarify_path),
        },
        "local_prediction_file": str(pred_path),
        "guardrails": [
            "Uses only the registered MetaVision ICU-death population.",
            "Uses the frozen rich comparator feature block plus the six registered state-dominant stripped-note Open-Jev scores.",
            "Rows without notes remain in the cohort with missing semantic values handled natively by HGB.",
            "Note-available rows must have all six state-dominant semantic scores or the analysis halts.",
            "Primary uncertainty is 500 valid patient-cluster refit-bootstrap replicates of the full repeat-1 cross-fitting procedure.",
            "No p-values, Holm testing, or binary significance decision is produced.",
            "Row-level predictions remain local; shared artifact is aggregate only.",
        ],
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
