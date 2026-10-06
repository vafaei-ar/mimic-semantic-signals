from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold

from preregistration_stats import patient_cluster_refit_indices
from registration_gate import require_osf_registration
from runrelay_progress import update_progress


BASE = Path("data/real_mimic_local/population_landmark12_v2_1")
SPLIT_MANIFEST = Path("outputs/multitask_benchmark/enhanced_structured_cv_splits_v2_1.json")
CONTEXT_FREEZE = Path("config/v2_1_context_feature_freeze.json")
POPULATION_CONTRACT = Path("config/v2_1_analysis_population_contract.json")
PREANALYSIS = Path("config/v2_1_preanalysis_clarifications_2026-09-25.json")
ATTESTATION = Path("docs/registration/exploratory_extension_osf_upload_attestation_2026-10-05.md")
T1_IMPLEMENTATION = Path(
    "docs/registration/exploratory_extension_t1_implementation_clarification_2026-10-05.md"
)
EMBEDDING_IMPLEMENTATION = Path(
    "docs/registration/exploratory_extension_embedding_implementation_clarification_2026-10-05.md"
)
CLASSIFIER_CLARIFICATION = Path(
    "docs/registration/exploratory_extension_t1_embedding_classifier_clarification_2026-10-05.md"
)

REPEAT_SEEDS = (20260924, 20260925, 20260926, 20260927, 20260928)
FOLDS = 5
INNER_FOLDS = 5
INNER_SEED_BASE = 20261005
BOOTSTRAP_SEED = 20260924
BOOTSTRAP_TIMING_VALID = 10
BOOTSTRAP_MAX = 500
BOOTSTRAP_REDUCED = 200
BOOTSTRAP_RUNTIME_CAP_HOURS = 72.0
MAX_REPLACEMENT_FRACTION = 0.05
ALERT_RATE = 0.05
C_GRID = (0.01, 0.1, 1.0, 10.0, 100.0)
C_TIE_TOL = 1e-12

OUTCOME_SPECS = {
    "invasive_ventilation": {
        "registered_pred": "h1_openjev_predictions_v2_1_local.csv",
        "timing_output": Path(
            "outputs/multitask_benchmark/extension_t1_embedding_timing_v2_1_ventilation.json"
        ),
        "full_output": Path(
            "outputs/multitask_benchmark/extension_t1_embedding_v2_1_ventilation.json"
        ),
    },
    "renal_replacement_therapy": {
        "registered_pred": "h2_openjev_predictions_v2_1_local.csv",
        "timing_output": Path(
            "outputs/multitask_benchmark/extension_t1_embedding_timing_v2_1_rrt.json"
        ),
        "full_output": Path(
            "outputs/multitask_benchmark/extension_t1_embedding_v2_1_rrt.json"
        ),
    },
    "icu_death": {
        "registered_pred": "h3_openjev_predictions_v2_1_local.csv",
        "timing_output": Path(
            "outputs/multitask_benchmark/extension_t1_embedding_timing_v2_1_death.json"
        ),
        "full_output": Path(
            "outputs/multitask_benchmark/extension_t1_embedding_v2_1_death.json"
        ),
    },
}


def load_numbered_module(filename: str, name: str):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {filename}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rich = load_numbered_module("117_evaluate_rich_comparator_v2_1.py", "rich_extension_t12")
metrics_mod = rich.legacy_metrics


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sigmoid(x: np.ndarray) -> np.ndarray:
    z = np.clip(np.asarray(x, dtype=float), -35.0, 35.0)
    return 1.0 / (1.0 + np.exp(-z))


def build_embedding_model(c_value: float) -> LogisticRegression:
    return LogisticRegression(
        penalty="l2",
        C=float(c_value),
        solver="liblinear",
        max_iter=5000,
        tol=1e-4,
        fit_intercept=True,
        class_weight=None,
    )


def make_inner_splits(
    y: np.ndarray,
    groups: np.ndarray,
    *,
    seed: int,
) -> list[tuple[np.ndarray, np.ndarray]]:
    if len(y) != len(groups):
        raise RuntimeError("Inner split input lengths differ")
    if len(np.unique(y)) != 2:
        raise RuntimeError("Inner split population contains one outcome class")
    if len(np.unique(groups)) < INNER_FOLDS:
        raise RuntimeError("Too few unique patients for five inner folds")

    splitter = StratifiedGroupKFold(
        n_splits=INNER_FOLDS,
        shuffle=True,
        random_state=int(seed),
    )
    splits = []
    for fold, (tr, va) in enumerate(
        splitter.split(np.zeros(len(y), dtype=np.int8), y, groups),
        start=1,
    ):
        if set(groups[tr]).intersection(set(groups[va])):
            raise RuntimeError(f"Patient leakage in inner fold {fold}")
        if len(np.unique(y[tr])) != 2:
            raise RuntimeError(f"Inner fold {fold} training data contain one class")
        if len(np.unique(y[va])) != 2:
            raise RuntimeError(f"Inner fold {fold} validation data contain one class")
        splits.append((np.asarray(tr, dtype=int), np.asarray(va, dtype=int)))
    return splits


def select_c(
    embeddings: np.ndarray,
    y: np.ndarray,
    splits: list[tuple[np.ndarray, np.ndarray]],
) -> tuple[float, dict[str, float]]:
    means: dict[str, float] = {}
    best_c = None
    best_score = -np.inf

    for c_value in C_GRID:
        scores = []
        for tr, va in splits:
            model = build_embedding_model(c_value)
            model.fit(embeddings[tr], y[tr])
            p = model.predict_proba(embeddings[va])[:, 1]
            if not np.isfinite(p).all():
                raise RuntimeError("Non-finite embedding classifier CV prediction")
            scores.append(float(roc_auc_score(y[va], p)))
        mean_score = float(np.mean(np.asarray(scores, dtype=float)))
        means[f"{c_value:g}"] = mean_score

        if mean_score > best_score + C_TIE_TOL:
            best_score = mean_score
            best_c = float(c_value)
        elif abs(mean_score - best_score) <= C_TIE_TOL:
            if best_c is None or float(c_value) < best_c:
                best_c = float(c_value)

    if best_c is None or not np.isfinite(best_score):
        raise RuntimeError("Could not select embedding logistic C")
    return best_c, means


def inner_crossfit_embedding(
    embeddings: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray,
    *,
    seed: int,
) -> tuple[np.ndarray, float, dict[str, float]]:
    splits = make_inner_splits(y, groups, seed=seed)
    selected_c, cv_means = select_c(embeddings, y, splits)

    score = np.full(len(y), np.nan, dtype=float)
    for tr, va in splits:
        model = build_embedding_model(selected_c)
        model.fit(embeddings[tr], y[tr])
        score[va] = model.decision_function(embeddings[va])

    if np.isnan(score).any() or not np.isfinite(score).all():
        raise RuntimeError("Incomplete or non-finite inner embedding scores")
    return score, selected_c, cv_means


def deterministic_alert_5(
    y: np.ndarray,
    pb: np.ndarray,
    pa: np.ndarray,
    case_id: np.ndarray,
) -> dict:
    n = len(y)
    k = int(math.ceil(ALERT_RATE * n))
    case_id = case_id.astype(str)
    case_order = np.argsort(case_id, kind="mergesort")
    rank = np.empty(n, dtype=np.int64)
    rank[case_order] = np.arange(n, dtype=np.int64)
    occurrence = np.arange(n, dtype=np.int64)
    ob = np.lexsort((occurrence, rank, -pb))
    oa = np.lexsort((occurrence, rank, -pa))
    mb = np.zeros(n, dtype=bool)
    ma = np.zeros(n, dtype=bool)
    mb[ob[:k]] = True
    ma[oa[:k]] = True
    eb = int(y[mb].sum())
    ea = int(y[ma].sum())
    moved_in = ma & ~mb
    moved_out = mb & ~ma
    total_events = int(y.sum())
    return {
        "alert_budget": ALERT_RATE,
        "alerts": k,
        "comparator_sensitivity": float(eb / total_events),
        "augmented_sensitivity": float(ea / total_events),
        "delta_sensitivity": float((ea - eb) / total_events),
        "comparator_ppv": float(eb / k),
        "augmented_ppv": float(ea / k),
        "delta_ppv": float((ea - eb) / k),
        "net_events_caught": int(ea - eb),
        "net_events_caught_per_1000_stays": float((ea - eb) / n * 1000.0),
        "alerts_moved_in_per_1000_stays": float(moved_in.sum() / n * 1000.0),
        "alerts_moved_out_per_1000_stays": float(moved_out.sum() / n * 1000.0),
        "events_moved_in_per_1000_stays": float(y[moved_in].sum() / n * 1000.0),
        "events_moved_out_per_1000_stays": float(y[moved_out].sum() / n * 1000.0),
    }


def load_embedding_cache(path: Path) -> tuple[np.ndarray, np.ndarray]:
    if not path.exists():
        raise RuntimeError(f"Frozen embedding cache missing: {path}")
    with np.load(path, allow_pickle=False) as npz:
        if set(npz.files) != {"case_id", "embeddings"}:
            raise RuntimeError(f"Unexpected embedding cache fields: {sorted(npz.files)}")
        case_id = np.asarray(npz["case_id"]).astype(str)
        embeddings = np.asarray(npz["embeddings"], dtype=np.float32)
    if embeddings.ndim != 2 or embeddings.shape[1] != 1024:
        raise RuntimeError(f"Unexpected embedding shape {embeddings.shape}")
    if len(case_id) != embeddings.shape[0]:
        raise RuntimeError("Embedding case_id/vector row counts differ")
    if len(set(case_id.tolist())) != len(case_id):
        raise RuntimeError("Duplicate case_id in embedding cache")
    if not np.isfinite(embeddings).all():
        raise RuntimeError("Non-finite cached embeddings")
    return case_id, embeddings


def load_population(outcome: str):
    population = json.loads(POPULATION_CONTRACT.read_text(encoding="utf-8"))
    split_manifest = json.loads(SPLIT_MANIFEST.read_text(encoding="utf-8"))
    context_freeze = json.loads(CONTEXT_FREEZE.read_text(encoding="utf-8"))
    contract = population["confirmatory_outcomes"][outcome]
    source = str(contract["source"]).strip().lower()

    structured_path = BASE / outcome / "enhanced_structured_features_v2_1_local.csv"
    context_path = BASE / outcome / "preregistration_context_features_v2_1_local.csv"
    index_path = BASE / outcome / "population_index_local.csv"
    embedding_path = BASE / outcome / "extension_bge_large_embeddings_v2_1_local.npz"
    registered_pred_path = BASE / outcome / OUTCOME_SPECS[outcome]["registered_pred"]

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
        if int(contract[key]) != int(value):
            raise RuntimeError(f"{outcome}: {key}={value} != frozen {contract[key]}")

    merged, x_base, feature_names = rich.prepare_rich_features(
        structured, context, outcome, context_freeze
    )
    frozen_splits, split_hash = rich.load_frozen_splits(
        merged, outcome, BASE, split_manifest
    )
    y = merged["label"].astype(int).to_numpy()
    groups = merged["subject_id"].to_numpy()
    case_id = merged["case_id"].astype(str).to_numpy()
    has_note = pd.to_numeric(merged["has_note"], errors="raise").astype(int).to_numpy() == 1

    emb_ids, emb = load_embedding_cache(embedding_path)
    expected_note_ids = set(case_id[has_note])
    if set(emb_ids.tolist()) != expected_note_ids:
        raise RuntimeError(
            f"{outcome}: embedding-cache IDs differ from frozen note-available cohort"
        )
    emb_map = {cid: i for i, cid in enumerate(emb_ids.tolist())}
    embedding_rows = np.full(len(case_id), -1, dtype=int)
    for i, cid in enumerate(case_id):
        if cid in emb_map:
            embedding_rows[i] = int(emb_map[cid])
    if np.any(embedding_rows[has_note] < 0) or np.any(embedding_rows[~has_note] >= 0):
        raise RuntimeError(f"{outcome}: embedding row alignment violates has_note")

    registered_pred = pd.read_csv(registered_pred_path, low_memory=False)
    registered_pred["case_id"] = registered_pred["case_id"].astype(str)
    if registered_pred["case_id"].duplicated().any():
        raise RuntimeError(f"{outcome}: duplicate case_id in registered prediction file")
    registered_pred = registered_pred.set_index("case_id").reindex(case_id)
    if registered_pred.isna().all(axis=1).any():
        raise RuntimeError(f"{outcome}: registered comparator predictions missing case_ids")

    hashes = {
        "structured_input_sha256": sha256_file(structured_path),
        "context_input_sha256": sha256_file(context_path),
        "embedding_cache_sha256": sha256_file(embedding_path),
        "registered_prediction_sha256": sha256_file(registered_pred_path),
        "split_manifest_sha256": sha256_file(SPLIT_MANIFEST),
        "split_sha256": split_hash,
        "context_freeze_sha256": sha256_file(CONTEXT_FREEZE),
        "analysis_population_contract_sha256": sha256_file(POPULATION_CONTRACT),
        "preanalysis_clarifications_sha256": sha256_file(PREANALYSIS),
        "t1_implementation_clarification_sha256": sha256_file(T1_IMPLEMENTATION),
        "embedding_implementation_clarification_sha256": sha256_file(
            EMBEDDING_IMPLEMENTATION
        ),
        "embedding_classifier_clarification_sha256": sha256_file(
            CLASSIFIER_CLARIFICATION
        ),
        "osf_upload_attestation_sha256": sha256_file(ATTESTATION),
    }
    return (
        merged,
        x_base.reset_index(drop=True),
        feature_names,
        y,
        groups,
        case_id,
        has_note,
        emb,
        embedding_rows,
        frozen_splits,
        registered_pred,
        hashes,
        source,
    )


def fit_outer_fold(
    x_base: pd.DataFrame,
    embedding_matrix: np.ndarray,
    embedding_rows: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray,
    has_note: np.ndarray,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    *,
    inner_seed: int,
):
    train_idx = np.asarray(train_idx, dtype=int)
    test_idx = np.asarray(test_idx, dtype=int)
    train_note_mask = has_note[train_idx]
    test_note_mask = has_note[test_idx]
    note_train_idx = train_idx[train_note_mask]
    note_test_idx = test_idx[test_note_mask]

    if len(note_train_idx) == 0:
        raise RuntimeError("Outer training fold has no note-available stays")
    if len(np.unique(y[note_train_idx])) != 2:
        raise RuntimeError("Outer note-available training rows contain one outcome class")

    train_emb = embedding_matrix[embedding_rows[note_train_idx]]
    inner_score, selected_c, cv_means = inner_crossfit_embedding(
        train_emb,
        y[note_train_idx],
        groups[note_train_idx],
        seed=int(inner_seed),
    )

    train_score = np.zeros(len(train_idx), dtype=float)
    train_score[train_note_mask] = inner_score

    full_model = build_embedding_model(selected_c)
    full_model.fit(train_emb, y[note_train_idx])
    test_score = np.zeros(len(test_idx), dtype=float)
    if len(note_test_idx):
        test_score[test_note_mask] = full_model.decision_function(
            embedding_matrix[embedding_rows[note_test_idx]]
        )

    xb_tr = x_base.iloc[train_idx].reset_index(drop=True)
    xb_te = x_base.iloc[test_idx].reset_index(drop=True)
    xa_tr = xb_tr.copy()
    xa_te = xb_te.copy()
    xa_tr["extension_embedding_log_odds"] = train_score
    xa_te["extension_embedding_log_odds"] = test_score

    base_model = rich.build_hgb(20260924)
    aug_model = rich.build_hgb(20260924)
    base_model.fit(xb_tr, y[train_idx])
    aug_model.fit(xa_tr, y[train_idx])
    pb = base_model.predict_proba(xb_te)[:, 1]
    pa = aug_model.predict_proba(xa_te)[:, 1]
    if not np.isfinite(pb).all() or not np.isfinite(pa).all():
        raise RuntimeError("Non-finite HGB predictions")
    return pb, pa, test_score, selected_c, cv_means


def point_estimates(outcome: str, *, write_local_predictions: bool) -> dict:
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
    ) = load_population(outcome)

    repeats = []
    local_pred = merged[["case_id", "subject_id", "icustay_id", "label"]].copy()
    total = len(REPEAT_SEEDS) * FOLDS
    current = 0

    for ri, seed in enumerate(REPEAT_SEEDS, start=1):
        folds = pd.to_numeric(
            frozen_splits[f"repeat_{ri}_fold"], errors="raise"
        ).astype(int).to_numpy()
        check = pd.DataFrame({"subject_id": groups, "fold": folds})
        if (check.groupby("subject_id")["fold"].nunique() > 1).any():
            raise RuntimeError(f"{outcome}: patient crosses outer folds in repeat {ri}")

        pb = np.full(len(y), np.nan, dtype=float)
        pa = np.full(len(y), np.nan, dtype=float)
        text_oof = np.full(len(y), np.nan, dtype=float)
        text_oof[~has_note] = 0.0
        selected_c_by_fold = {}
        cv_auc_by_fold = {}

        for fold in range(1, FOLDS + 1):
            te = np.flatnonzero(folds == fold)
            tr = np.flatnonzero(folds != fold)
            p0, p1, ts, selected_c, cv_means = fit_outer_fold(
                x_base,
                embedding_matrix,
                embedding_rows,
                y,
                groups,
                has_note,
                tr,
                te,
                inner_seed=INNER_SEED_BASE + 100 * ri + fold,
            )
            pb[te] = p0
            pa[te] = p1
            text_oof[te] = ts
            selected_c_by_fold[str(fold)] = float(selected_c)
            cv_auc_by_fold[str(fold)] = cv_means

            current += 1
            update_progress(
                current=current,
                total=total,
                phase="extension_t1_embedding_point_estimation",
                message=f"{outcome}: repeat {ri}/5 outer fold {fold}/5",
                unit="fold",
            )

        if (
            np.isnan(pb).any()
            or np.isnan(pa).any()
            or np.isnan(text_oof).any()
            or not np.isfinite(text_oof).all()
        ):
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

        mb = metrics_mod.basic_metrics(y, pb)
        ma = metrics_mod.basic_metrics(y, pa)
        note_y = y[has_note]
        note_score = sigmoid(text_oof[has_note])
        if len(np.unique(note_y)) != 2:
            raise RuntimeError(f"{outcome}: note-available rows contain one class")
        text_auroc = float(roc_auc_score(note_y, note_score))
        text_auprc = float(average_precision_score(note_y, note_score))
        alert5 = deterministic_alert_5(y, pb, pa, case_id)

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
                "standalone_text_note_available": {
                    "n": int(has_note.sum()),
                    "cases": int(note_y.sum()),
                    "prevalence": float(note_y.mean()),
                    "auroc": text_auroc,
                    "auprc": text_auprc,
                    "interpretive_threshold_auroc": 0.60,
                    "threshold_met": bool(text_auroc >= 0.60),
                },
                "fixed_5_percent_alert": alert5,
                "selected_c_by_outer_fold": selected_c_by_fold,
                "inner_cv_mean_auroc_by_outer_fold": cv_auc_by_fold,
                "comparator_regeneration_max_abs_diff": max_abs_diff,
            }
        )

        local_pred[f"extension_t1_embedding_text_logit_repeat_{ri}"] = text_oof
        local_pred[f"extension_t1_embedding_comparator_repeat_{ri}"] = pb
        local_pred[f"extension_t1_embedding_augmented_repeat_{ri}"] = pa

    if write_local_predictions:
        pred_path = BASE / outcome / "extension_t1_embedding_predictions_v2_1_local.csv"
        local_pred.to_csv(pred_path, index=False)
    else:
        pred_path = None

    deltas_auc = [float(r["delta"]["auroc"]) for r in repeats]
    deltas_pr = [float(r["delta"]["auprc"]) for r in repeats]
    text_auc = [float(r["standalone_text_note_available"]["auroc"]) for r in repeats]
    return {
        "outcome": outcome,
        "source": source,
        "n": int(len(y)),
        "cases": int(y.sum()),
        "note_available_n": int(has_note.sum()),
        "analysis_status": "post-registration exploratory",
        "representation": "frozen BGE-large supervised embedding log-odds late fusion",
        "primary_estimand": (
            "repeat-1 OOF delta_AUROC = AUROC(rich comparator D + cross-fitted "
            "supervised embedding log-odds) - AUROC(rich comparator D)"
        ),
        "primary_repeat": repeats[0],
        "repeat_results": repeats,
        "five_partition_summary": {
            "delta_auroc_values": deltas_auc,
            "delta_auroc_range": [float(min(deltas_auc)), float(max(deltas_auc))],
            "delta_auprc_values": deltas_pr,
            "delta_auprc_range": [float(min(deltas_pr)), float(max(deltas_pr))],
            "standalone_text_auroc_values": text_auc,
            "standalone_text_auroc_range": [float(min(text_auc)), float(max(text_auc))],
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
    selected_cs = []

    for fold in range(1, FOLDS + 1):
        tr, te = split_indices[fold]
        if len(te) == 0:
            raise RuntimeError(f"Bootstrap outer fold {fold} has no held-out rows")
        if len(np.unique(y[tr])) != 2:
            raise RuntimeError(f"Bootstrap outer fold {fold} training data contain one class")
        p0, p1, _ts, selected_c, _cv_means = fit_outer_fold(
            x_base,
            embedding_matrix,
            embedding_rows,
            y,
            groups,
            has_note,
            tr,
            te,
            inner_seed=INNER_SEED_BASE + fold,
        )
        eval_y.append(y[te])
        eval_pb.append(p0)
        eval_pa.append(p1)
        eval_case.append(case_id[te])
        selected_cs.append(float(selected_c))

    yy = np.concatenate(eval_y)
    pb = np.concatenate(eval_pb)
    pa = np.concatenate(eval_pa)
    cc = np.concatenate(eval_case)
    if yy.sum() == 0 or yy.sum() == len(yy):
        return None

    alert = deterministic_alert_5(yy, pb, pa, cc)
    return {
        "delta_auroc": float(roc_auc_score(yy, pa) - roc_auc_score(yy, pb)),
        "delta_auprc": float(
            average_precision_score(yy, pa) - average_precision_score(yy, pb)
        ),
        "fixed_5_percent_alert_delta_sensitivity": float(alert["delta_sensitivity"]),
        "fixed_5_percent_alert_delta_ppv": float(alert["delta_ppv"]),
        "fixed_5_percent_alert_net_events_per_1000": float(
            alert["net_events_caught_per_1000_stays"]
        ),
        "selected_c_values": selected_cs,
    }


def timing_gate(outcome: str) -> dict:
    data = load_population(outcome)
    frozen_splits = data[9]
    groups = data[4]
    primary_folds = pd.to_numeric(
        frozen_splits["repeat_1_fold"], errors="raise"
    ).astype(int).to_numpy()
    check = pd.DataFrame({"subject_id": groups, "fold": primary_folds})
    if (check.groupby("subject_id")["fold"].nunique() > 1).any():
        raise RuntimeError("Patient crosses primary outer folds")

    children = np.random.SeedSequence(BOOTSTRAP_SEED).spawn(600)
    runtimes = []
    replacements = 0
    child_index = 0

    while len(runtimes) < BOOTSTRAP_TIMING_VALID:
        child = children[child_index]
        child_index += 1
        start = time.perf_counter()
        result = bootstrap_refit_once(
            outcome,
            data,
            primary_folds,
            np.random.default_rng(child),
        )
        elapsed = float(time.perf_counter() - start)
        if result is None:
            replacements += 1
            continue
        runtimes.append(elapsed)
        update_progress(
            current=len(runtimes),
            total=BOOTSTRAP_TIMING_VALID,
            phase="extension_t1_embedding_bootstrap_timing",
            message=(
                f"{outcome}: timing-only valid bootstrap replicate "
                f"{len(runtimes)}/{BOOTSTRAP_TIMING_VALID}"
            ),
            unit="replicate",
        )

    median_seconds = float(np.median(np.asarray(runtimes, dtype=float)))
    projected_seconds_500 = float(median_seconds * BOOTSTRAP_MAX)
    projected_hours_500 = float(projected_seconds_500 / 3600.0)
    target = (
        BOOTSTRAP_REDUCED
        if projected_hours_500 > BOOTSTRAP_RUNTIME_CAP_HOURS
        else BOOTSTRAP_MAX
    )
    return {
        "timing_valid_replicates": BOOTSTRAP_TIMING_VALID,
        "timing_replacements_single_class": int(replacements),
        "timing_seconds_per_valid_replicate": [float(x) for x in runtimes],
        "median_seconds_per_valid_replicate": median_seconds,
        "projected_seconds_for_500": projected_seconds_500,
        "projected_hours_for_500": projected_hours_500,
        "runtime_cap_hours": BOOTSTRAP_RUNTIME_CAP_HOURS,
        "selected_final_valid_replicates": int(target),
        "selection_rule": (
            "If median runtime of first 10 frozen-seed valid replicates times 500 "
            "exceeds 72 hours, use 200 valid replicates; otherwise use 500. "
            "Performance estimates from timing-only execution are discarded."
        ),
        "bootstrap_seed_sequence": BOOTSTRAP_SEED,
    }


def percentile_summary(values: list[float]) -> dict:
    arr = np.asarray(values, dtype=float)
    lo, hi = np.quantile(arr, [0.025, 0.975])
    return {
        "mean": float(arr.mean()),
        "sd": float(arr.std(ddof=1)),
        "ci95_percentile": [float(lo), float(hi)],
    }


def run_full_bootstrap(outcome: str, timing: dict) -> dict:
    target = int(timing["selected_final_valid_replicates"])
    if target not in (BOOTSTRAP_REDUCED, BOOTSTRAP_MAX):
        raise RuntimeError(f"Unexpected timing-selected bootstrap target {target}")

    data = load_population(outcome)
    frozen_splits = data[9]
    groups = data[4]
    primary_folds = pd.to_numeric(
        frozen_splits["repeat_1_fold"], errors="raise"
    ).astype(int).to_numpy()
    max_replacements = int(math.floor(target * MAX_REPLACEMENT_FRACTION))
    children = np.random.SeedSequence(BOOTSTRAP_SEED).spawn(
        target + max_replacements + 10
    )
    results = []
    replacements = []
    child_index = 0
    c_counter: Counter[str] = Counter()

    while len(results) < target:
        if child_index >= len(children):
            raise RuntimeError("Exhausted deterministic bootstrap child seeds")
        child = children[child_index]
        seed_index = child_index
        child_index += 1

        result = bootstrap_refit_once(
            outcome,
            data,
            primary_folds,
            np.random.default_rng(child),
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

        for c_value in result.pop("selected_c_values"):
            c_counter[f"{float(c_value):g}"] += 1
        results.append(result)

        if len(results) == 1 or len(results) % 5 == 0 or len(results) == target:
            update_progress(
                current=len(results),
                total=target,
                phase="extension_t1_embedding_refit_bootstrap",
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
        "bootstrap_seed_sequence": BOOTSTRAP_SEED,
        "interval_type": "two-sided 95% percentile",
        "full_embedding_logistic_refit_each_replicate": True,
        "full_hgb_refit_each_replicate": True,
        "same_patient_inner_fold_guard": True,
        "bootstrap_outer_fold_selected_c_counts": dict(sorted(c_counter.items())),
        "delta_auroc": percentile_summary([r["delta_auroc"] for r in results]),
        "delta_auprc": percentile_summary([r["delta_auprc"] for r in results]),
        "fixed_5_percent_alert_delta_sensitivity": percentile_summary(
            [r["fixed_5_percent_alert_delta_sensitivity"] for r in results]
        ),
        "fixed_5_percent_alert_delta_ppv": percentile_summary(
            [r["fixed_5_percent_alert_delta_ppv"] for r in results]
        ),
        "fixed_5_percent_alert_net_events_per_1000": percentile_summary(
            [r["fixed_5_percent_alert_net_events_per_1000"] for r in results]
        ),
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Paper 1 extension T1.2 cross-fitted frozen-embedding benchmark."
    )
    ap.add_argument("--outcome", choices=tuple(OUTCOME_SPECS), required=True)
    ap.add_argument("--mode", choices=("timing", "full"), required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--timing-input")
    args = ap.parse_args()

    require_osf_registration()
    for gate in (
        ATTESTATION,
        T1_IMPLEMENTATION,
        EMBEDDING_IMPLEMENTATION,
        CLASSIFIER_CLARIFICATION,
    ):
        if not gate.exists():
            raise RuntimeError(f"Required extension gate missing: {gate}")

    outcome = args.outcome
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    point = point_estimates(outcome, write_local_predictions=True)
    report = {
        "analysis": "Paper 1 exploratory extension T1.2 frozen-embedding supervised benchmark",
        "status": "completed",
        "extension_status": "post-registration exploratory",
        "parent_registration": "ahxn9",
        "extension_osf_project": "wmyb2",
        "outcome": outcome,
        "mode": args.mode,
        "embedding_representation": {
            "model_id": "BAAI/bge-large-en-v1.5",
            "revision": "d4aa6901d3a41ba39fb536a557fa166f842b0e09",
            "dimension": 1024,
            "cache_is_label_free": True,
        },
        "classifier": {
            "family": "L2-penalized logistic regression",
            "solver": "liblinear",
            "C_grid": list(C_GRID),
            "selection": "highest mean AUROC across frozen five patient-grouped inner folds",
            "tie_rule": "within 1e-12 choose smallest C",
            "max_iter": 5000,
            "tol": 1e-4,
            "class_weight": None,
        },
        "fusion": {
            "type": "late fusion",
            "feature": "one cross-fitted embedding log-odds feature added to comparator D",
            "downstream": "registered v2.1 HistGradientBoostingClassifier",
        },
        "point_estimates": point,
        "guardrails": [
            "Every point estimate is reported regardless of direction.",
            "Standalone text AUROC 0.60 is interpretive only, not a validity threshold.",
            "No-note rows receive embedding score 0 while has_note remains in comparator D.",
            "C selection occurs only inside each outer training sample.",
            "The held-out outer fold is never used for C selection.",
            "Comparator D is regenerated and required to match the registered local OOF comparator prediction to 1e-12.",
            "Row-level embedding scores and model predictions remain local and are not declared as artifacts.",
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
            raise RuntimeError("Timing input does not match requested outcome/mode")
        timing = timing_report["bootstrap_runtime_gate"]
        report["bootstrap_runtime_gate"] = timing
        report["primary_refit_bootstrap"] = run_full_bootstrap(outcome, timing)
        report["bootstrap_status"] = "completed"

    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "completed",
                "outcome": outcome,
                "mode": args.mode,
                "primary_delta_auroc": point["primary_repeat"]["delta"]["auroc"],
                "standalone_text_auroc": point["primary_repeat"][
                    "standalone_text_note_available"
                ]["auroc"],
                "selected_bootstrap_replicates": int(
                    report["bootstrap_runtime_gate"]["selected_final_valid_replicates"]
                ),
                "output": str(output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
