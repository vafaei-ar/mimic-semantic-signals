from __future__ import annotations

import argparse
import importlib.util
import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.metrics import average_precision_score, roc_auc_score

from preregistration_stats import patient_cluster_refit_indices
from runrelay_progress import update_progress


def load_numbered_module(filename: str, name: str):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {filename}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


base = load_numbered_module(
    "174_evaluate_extension_t1_embedding_v2_1.py",
    "extension_t1_early_fusion_base",
)

EARLY_FUSION_CLARIFICATION = Path(
    "docs/registration/exploratory_extension_t1_early_fusion_clarification_2026-10-06.md"
)
N_COMPONENTS = 32


def build_pca() -> PCA:
    return PCA(n_components=N_COMPONENTS, svd_solver="full", whiten=False)


def fit_outer_fold(
    x_base: pd.DataFrame,
    embedding_matrix: np.ndarray,
    embedding_rows: np.ndarray,
    y: np.ndarray,
    has_note: np.ndarray,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
):
    train_idx = np.asarray(train_idx, dtype=int)
    test_idx = np.asarray(test_idx, dtype=int)
    train_note_mask = has_note[train_idx]
    test_note_mask = has_note[test_idx]
    note_train_idx = train_idx[train_note_mask]
    note_test_idx = test_idx[test_note_mask]

    if len(note_train_idx) < N_COMPONENTS:
        raise RuntimeError("Too few note-available training rows for 32-component PCA")

    pca = build_pca()
    pca.fit(embedding_matrix[embedding_rows[note_train_idx]])

    train_pc = np.zeros((len(train_idx), N_COMPONENTS), dtype=np.float64)
    test_pc = np.zeros((len(test_idx), N_COMPONENTS), dtype=np.float64)
    train_pc[train_note_mask] = pca.transform(
        embedding_matrix[embedding_rows[note_train_idx]]
    )
    if len(note_test_idx):
        test_pc[test_note_mask] = pca.transform(
            embedding_matrix[embedding_rows[note_test_idx]]
        )

    if not np.isfinite(train_pc).all() or not np.isfinite(test_pc).all():
        raise RuntimeError("Non-finite PCA component values")

    xb_tr = x_base.iloc[train_idx].reset_index(drop=True)
    xb_te = x_base.iloc[test_idx].reset_index(drop=True)
    xa_tr = xb_tr.copy()
    xa_te = xb_te.copy()
    for j in range(N_COMPONENTS):
        name = f"extension_embedding_pc_{j + 1:02d}"
        xa_tr[name] = train_pc[:, j]
        xa_te[name] = test_pc[:, j]

    base_model = base.rich.build_hgb(20260924)
    aug_model = base.rich.build_hgb(20260924)
    base_model.fit(xb_tr, y[train_idx])
    aug_model.fit(xa_tr, y[train_idx])
    pb = base_model.predict_proba(xb_te)[:, 1]
    pa = aug_model.predict_proba(xa_te)[:, 1]
    if not np.isfinite(pb).all() or not np.isfinite(pa).all():
        raise RuntimeError("Non-finite HGB predictions")
    return pb, pa, {
        "explained_variance_ratio_sum": float(
            np.sum(pca.explained_variance_ratio_)
        ),
        "note_train_rows": int(len(note_train_idx)),
        "note_test_rows": int(len(note_test_idx)),
    }


def point_estimates(outcome: str, *, write_local_predictions: bool) -> dict:
    data = base.load_population(outcome)
    (
        merged,
        x_base,
        _feature_names,
        y,
        groups,
        case_id,
        has_note,
        embedding_matrix,
        embedding_rows,
        frozen_splits,
        registered_pred,
        hashes,
        source,
    ) = data

    repeats = []
    local_pred = merged[["case_id", "subject_id", "icustay_id", "label"]].copy()
    total = len(base.REPEAT_SEEDS) * base.FOLDS
    current = 0

    for ri, seed in enumerate(base.REPEAT_SEEDS, start=1):
        folds = pd.to_numeric(
            frozen_splits[f"repeat_{ri}_fold"], errors="raise"
        ).astype(int).to_numpy()
        check = pd.DataFrame({"subject_id": groups, "fold": folds})
        if (check.groupby("subject_id")["fold"].nunique() > 1).any():
            raise RuntimeError(f"{outcome}: patient crosses outer folds in repeat {ri}")

        pb = np.full(len(y), np.nan, dtype=float)
        pa = np.full(len(y), np.nan, dtype=float)
        pca_fold = {}

        for fold in range(1, base.FOLDS + 1):
            te = np.flatnonzero(folds == fold)
            tr = np.flatnonzero(folds != fold)
            p0, p1, diag = fit_outer_fold(
                x_base,
                embedding_matrix,
                embedding_rows,
                y,
                has_note,
                tr,
                te,
            )
            pb[te] = p0
            pa[te] = p1
            pca_fold[str(fold)] = diag

            current += 1
            update_progress(
                current=current,
                total=total,
                phase="extension_t1_early_fusion_point_estimation",
                message=f"{outcome}: repeat {ri}/5 outer fold {fold}/5",
                unit="fold",
            )

        if np.isnan(pb).any() or np.isnan(pa).any():
            raise RuntimeError(f"{outcome}: incomplete repeat {ri} predictions")

        expected = pd.to_numeric(
            registered_pred[f"comparator_repeat_{ri}"], errors="raise"
        ).to_numpy(dtype=float)
        max_abs_diff = float(np.max(np.abs(expected - pb)))
        if max_abs_diff > 1e-12:
            raise RuntimeError(
                f"{outcome}: regenerated comparator differs from registered repeat {ri}; "
                f"max_abs_diff={max_abs_diff}"
            )

        mb = base.metrics_mod.basic_metrics(y, pb)
        ma = base.metrics_mod.basic_metrics(y, pa)
        alert5 = base.deterministic_alert_5(y, pb, pa, case_id)
        repeats.append(
            {
                "repeat": ri,
                "seed": int(seed),
                "comparator": {
                    "auroc": float(mb["auroc"]),
                    "auprc": float(mb["auprc"]),
                },
                "augmented": {
                    "auroc": float(ma["auroc"]),
                    "auprc": float(ma["auprc"]),
                },
                "delta": {
                    "auroc": float(ma["auroc"] - mb["auroc"]),
                    "auprc": float(ma["auprc"] - mb["auprc"]),
                },
                "fixed_5_percent_alert": alert5,
                "pca_by_outer_fold": pca_fold,
                "comparator_regeneration_max_abs_diff": max_abs_diff,
            }
        )
        local_pred[f"extension_t1_early_fusion_comparator_repeat_{ri}"] = pb
        local_pred[f"extension_t1_early_fusion_augmented_repeat_{ri}"] = pa

    if write_local_predictions:
        pred_path = (
            base.BASE / outcome / "extension_t1_early_fusion_predictions_v2_1_local.csv"
        )
        local_pred.to_csv(pred_path, index=False)
    else:
        pred_path = None

    deltas_auc = [float(r["delta"]["auroc"]) for r in repeats]
    deltas_pr = [float(r["delta"]["auprc"]) for r in repeats]
    hashes = dict(hashes)
    hashes["early_fusion_clarification_sha256"] = base.sha256_file(
        EARLY_FUSION_CLARIFICATION
    )
    return {
        "outcome": outcome,
        "source": source,
        "n": int(len(y)),
        "cases": int(y.sum()),
        "note_available_n": int(has_note.sum()),
        "analysis_status": "post-registration exploratory",
        "representation": "32-component frozen-embedding PCA early fusion",
        "standalone_text_reference": (
            "T1.2 frozen-embedding supervised score; T1.2b has no standalone score"
        ),
        "primary_estimand": (
            "repeat-1 OOF delta_AUROC = AUROC(rich comparator D + 32 training-fold "
            "PCA embedding components) - AUROC(rich comparator D)"
        ),
        "primary_repeat": repeats[0],
        "repeat_results": repeats,
        "five_partition_summary": {
            "delta_auroc_values": deltas_auc,
            "delta_auroc_range": [float(min(deltas_auc)), float(max(deltas_auc))],
            "delta_auprc_values": deltas_pr,
            "delta_auprc_range": [float(min(deltas_pr)), float(max(deltas_pr))],
        },
        "local_prediction_file": None if pred_path is None else str(pred_path),
        "hashes": hashes,
    }


def bootstrap_refit_once(
    outcome: str,
    data,
    primary_folds: np.ndarray,
    rng: np.random.Generator,
):
    (
        _merged,
        x_base,
        _feature_names,
        y,
        groups,
        case_id,
        has_note,
        embedding_matrix,
        embedding_rows,
        _frozen_splits,
        _registered_pred,
        _hashes,
        _source,
    ) = data

    split_indices = patient_cluster_refit_indices(groups, primary_folds, rng)
    eval_y = []
    eval_pb = []
    eval_pa = []
    eval_case = []

    for fold in range(1, base.FOLDS + 1):
        tr, te = split_indices[fold]
        if len(te) == 0:
            raise RuntimeError(f"Bootstrap outer fold {fold} has no held-out rows")
        if len(np.unique(y[tr])) != 2:
            raise RuntimeError(
                f"Bootstrap outer fold {fold} training data contain one class"
            )
        p0, p1, _diag = fit_outer_fold(
            x_base,
            embedding_matrix,
            embedding_rows,
            y,
            has_note,
            tr,
            te,
        )
        eval_y.append(y[te])
        eval_pb.append(p0)
        eval_pa.append(p1)
        eval_case.append(case_id[te])

    yy = np.concatenate(eval_y)
    pb = np.concatenate(eval_pb)
    pa = np.concatenate(eval_pa)
    cc = np.concatenate(eval_case)
    if yy.sum() == 0 or yy.sum() == len(yy):
        return None

    alert = base.deterministic_alert_5(yy, pb, pa, cc)
    return {
        "delta_auroc": float(roc_auc_score(yy, pa) - roc_auc_score(yy, pb)),
        "delta_auprc": float(
            average_precision_score(yy, pa) - average_precision_score(yy, pb)
        ),
        "fixed_5_percent_alert_delta_sensitivity": float(
            alert["delta_sensitivity"]
        ),
        "fixed_5_percent_alert_delta_ppv": float(alert["delta_ppv"]),
        "fixed_5_percent_alert_net_events_per_1000": float(
            alert["net_events_caught_per_1000_stays"]
        ),
    }


def timing_gate(outcome: str) -> dict:
    data = base.load_population(outcome)
    frozen_splits = data[9]
    groups = data[4]
    primary_folds = pd.to_numeric(
        frozen_splits["repeat_1_fold"], errors="raise"
    ).astype(int).to_numpy()

    children = np.random.SeedSequence(base.BOOTSTRAP_SEED).spawn(600)
    runtimes = []
    replacements = 0
    child_index = 0

    while len(runtimes) < base.BOOTSTRAP_TIMING_VALID:
        child = children[child_index]
        child_index += 1
        start = time.perf_counter()
        result = bootstrap_refit_once(
            outcome, data, primary_folds, np.random.default_rng(child)
        )
        elapsed = float(time.perf_counter() - start)
        if result is None:
            replacements += 1
            continue
        runtimes.append(elapsed)
        update_progress(
            current=len(runtimes),
            total=base.BOOTSTRAP_TIMING_VALID,
            phase="extension_t1_early_fusion_bootstrap_timing",
            message=(
                f"{outcome}: timing-only valid bootstrap replicate "
                f"{len(runtimes)}/{base.BOOTSTRAP_TIMING_VALID}"
            ),
            unit="replicate",
        )

    median_seconds = float(np.median(np.asarray(runtimes, dtype=float)))
    projected_seconds_500 = float(median_seconds * base.BOOTSTRAP_MAX)
    projected_hours_500 = float(projected_seconds_500 / 3600.0)
    target = (
        base.BOOTSTRAP_REDUCED
        if projected_hours_500 > base.BOOTSTRAP_RUNTIME_CAP_HOURS
        else base.BOOTSTRAP_MAX
    )
    return {
        "timing_valid_replicates": base.BOOTSTRAP_TIMING_VALID,
        "timing_replacements_single_class": int(replacements),
        "timing_seconds_per_valid_replicate": [float(x) for x in runtimes],
        "median_seconds_per_valid_replicate": median_seconds,
        "projected_seconds_for_500": projected_seconds_500,
        "projected_hours_for_500": projected_hours_500,
        "runtime_cap_hours": base.BOOTSTRAP_RUNTIME_CAP_HOURS,
        "selected_final_valid_replicates": int(target),
        "selection_rule": (
            "If median runtime of first 10 frozen-seed valid replicates times 500 "
            "exceeds 72 hours, use 200 valid replicates; otherwise use 500. "
            "Performance estimates from timing-only execution are discarded."
        ),
        "bootstrap_seed_sequence": base.BOOTSTRAP_SEED,
    }


def run_full_bootstrap(outcome: str, timing: dict) -> dict:
    target = int(timing["selected_final_valid_replicates"])
    if target not in (base.BOOTSTRAP_REDUCED, base.BOOTSTRAP_MAX):
        raise RuntimeError(f"Unexpected timing-selected bootstrap target {target}")

    data = base.load_population(outcome)
    frozen_splits = data[9]
    groups = data[4]
    primary_folds = pd.to_numeric(
        frozen_splits["repeat_1_fold"], errors="raise"
    ).astype(int).to_numpy()
    max_replacements = int(math.floor(target * base.MAX_REPLACEMENT_FRACTION))
    children = np.random.SeedSequence(base.BOOTSTRAP_SEED).spawn(
        target + max_replacements + 10
    )
    results = []
    replacements = []
    child_index = 0

    while len(results) < target:
        child = children[child_index]
        seed_index = child_index
        child_index += 1
        result = bootstrap_refit_once(
            outcome, data, primary_folds, np.random.default_rng(child)
        )
        if result is None:
            replacements.append(
                {
                    "child_seed_index": seed_index,
                    "reason": "single_class_heldout_evaluation",
                }
            )
            if len(replacements) > max_replacements:
                raise RuntimeError(
                    "Single-class bootstrap replacement fraction exceeded frozen 5% cap"
                )
            continue
        results.append(result)
        if len(results) == 1 or len(results) % 5 == 0 or len(results) == target:
            update_progress(
                current=len(results),
                total=target,
                phase="extension_t1_early_fusion_refit_bootstrap",
                message=f"{outcome}: valid refit bootstrap {len(results)}/{target}",
                unit="replicate",
            )

    return {
        "valid_replicates": int(len(results)),
        "target_valid_replicates": int(target),
        "replacement_count": int(len(replacements)),
        "replacement_log": replacements,
        "bootstrap_unit": "source_patient",
        "outer_partition": "repeat_1",
        "bootstrap_seed_sequence": base.BOOTSTRAP_SEED,
        "interval_type": "two-sided 95% percentile",
        "pca_refit_each_replicate": True,
        "full_hgb_refit_each_replicate": True,
        "delta_auroc": base.percentile_summary(
            [r["delta_auroc"] for r in results]
        ),
        "delta_auprc": base.percentile_summary(
            [r["delta_auprc"] for r in results]
        ),
        "fixed_5_percent_alert_delta_sensitivity": base.percentile_summary(
            [r["fixed_5_percent_alert_delta_sensitivity"] for r in results]
        ),
        "fixed_5_percent_alert_delta_ppv": base.percentile_summary(
            [r["fixed_5_percent_alert_delta_ppv"] for r in results]
        ),
        "fixed_5_percent_alert_net_events_per_1000": base.percentile_summary(
            [r["fixed_5_percent_alert_net_events_per_1000"] for r in results]
        ),
    }


def self_test() -> None:
    rng = np.random.default_rng(20261006)
    emb = rng.normal(size=(80, 64))
    y = np.asarray([0, 1] * 40, dtype=int)
    has_note = np.ones(80, dtype=bool)
    has_note[::7] = False
    emb_rows = np.full(80, -1, dtype=int)
    note_idx = np.flatnonzero(has_note)
    cache = emb[note_idx].copy()
    for j, i in enumerate(note_idx):
        emb_rows[i] = j
    x = pd.DataFrame({"x": rng.normal(size=80), "has_note": has_note.astype(int)})
    tr = np.arange(0, 60, dtype=int)
    te = np.arange(60, 80, dtype=int)
    pb, pa, diag = fit_outer_fold(
        x, cache, emb_rows, y, has_note, tr, te
    )
    if pb.shape != (20,) or pa.shape != (20,):
        raise RuntimeError("T1.2b self-test failed: prediction shape")
    if not np.isfinite(pb).all() or not np.isfinite(pa).all():
        raise RuntimeError("T1.2b self-test failed: non-finite predictions")
    if not (0.0 <= diag["explained_variance_ratio_sum"] <= 1.0 + 1e-12):
        raise RuntimeError("T1.2b self-test failed: PCA variance")
    print(json.dumps({"t1_2b_self_test": "passed", "diag": diag}, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Paper 1 extension T1.2b 32-component embedding early fusion."
    )
    ap.add_argument("--outcome", choices=tuple(base.OUTCOME_SPECS), required=True)
    ap.add_argument("--mode", choices=("timing", "full"), required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--timing-input")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return

    base.require_osf_registration()
    for gate in (
        base.ATTESTATION,
        base.T1_IMPLEMENTATION,
        base.EMBEDDING_IMPLEMENTATION,
        EARLY_FUSION_CLARIFICATION,
    ):
        if not gate.exists():
            raise RuntimeError(f"Required extension gate missing: {gate}")

    outcome = args.outcome
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    point = point_estimates(outcome, write_local_predictions=True)
    report = {
        "analysis": "Paper 1 exploratory extension T1.2b embedding early fusion",
        "status": "completed",
        "extension_status": "post-registration exploratory",
        "parent_registration": "ahxn9",
        "extension_osf_project": "wmyb2",
        "outcome": outcome,
        "mode": args.mode,
        "method": {
            "embedding": "frozen BAAI/bge-large-en-v1.5 document vectors",
            "pca_components": N_COMPONENTS,
            "pca_solver": "full",
            "whiten": False,
            "pca_fit_population": "note-available rows in each outer training sample",
            "no_note_encoding": "32 zeros; registered has_note remains in comparator D",
            "fusion": "32 PCA components appended directly to comparator D HGB",
        },
        "point_estimates": point,
        "standalone_text_learnability": (
            "Inherited from T1.2 frozen-embedding supervised score; T1.2b has no "
            "standalone text score by protocol."
        ),
        "guardrails": [
            "PCA is refit inside every outer training sample and bootstrap replicate.",
            "PCA uses no outcome labels.",
            "No alternative component count, solver, whitening rule, or missing-note encoding is compared.",
            "Every result is reported regardless of direction.",
            "Row-level PCA scores and predictions remain local and are not declared as artifacts.",
        ],
    }

    if args.mode == "timing":
        timing = timing_gate(outcome)
        report["bootstrap_runtime_gate"] = timing
        report["bootstrap_status"] = (
            "timing gate complete; performance estimates from timing replicates discarded"
        )
    else:
        if not args.timing_input:
            raise RuntimeError("--timing-input is required in full mode")
        timing_path = Path(args.timing_input)
        timing_report = json.loads(timing_path.read_text(encoding="utf-8"))
        if timing_report.get("outcome") != outcome or timing_report.get("mode") != "timing":
            raise RuntimeError("Timing input does not match requested T1.2b outcome/mode")
        timing = timing_report["bootstrap_runtime_gate"]
        report["bootstrap_runtime_gate"] = timing
        report["primary_refit_bootstrap"] = run_full_bootstrap(outcome, timing)
        report["bootstrap_status"] = "completed"

    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "completed",
                "analysis": "T1.2b",
                "outcome": outcome,
                "mode": args.mode,
                "primary_delta_auroc": point["primary_repeat"]["delta"]["auroc"],
                "selected_bootstrap_replicates": int(
                    report["bootstrap_runtime_gate"][
                        "selected_final_valid_replicates"
                    ]
                ),
                "output": str(output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
