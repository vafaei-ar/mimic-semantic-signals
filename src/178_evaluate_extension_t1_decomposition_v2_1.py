from __future__ import annotations

import argparse
import importlib.util
import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd
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


tfidf = load_numbered_module(
    "172_evaluate_extension_t1_tfidf_v2_1.py",
    "extension_t1_decomp_tfidf",
)
embedding = load_numbered_module(
    "174_evaluate_extension_t1_embedding_v2_1.py",
    "extension_t1_decomp_embedding",
)
decomp = load_numbered_module(
    "160_evaluate_submission_exploratory_v2_1.py",
    "extension_t1_decomp_levels",
)

CLARIFICATION = Path(
    "docs/registration/exploratory_extension_t1_decomposition_clarification_2026-10-06.md"
)
BOOTSTRAP_TIMING_VALID = 10
BOOTSTRAP_MAX = 500
BOOTSTRAP_REDUCED = 200
BOOTSTRAP_RUNTIME_CAP_HOURS = 72.0
MAX_REPLACEMENT_FRACTION = 0.05
BOOTSTRAP_SEED = 20260924


def load_joint_population(outcome: str):
    dt = tfidf.load_population(outcome)
    de = embedding.load_population(outcome)

    # Shared row/order identity checks.
    for i in (3, 4, 5, 6):
        at = np.asarray(dt[i])
        ae = np.asarray(de[i])
        if at.shape != ae.shape or not np.array_equal(at, ae):
            raise RuntimeError(f"{outcome}: TF-IDF/embedding population mismatch at tuple index {i}")

    xt = dt[1]
    xe = de[1]
    if list(xt.columns) != list(xe.columns):
        raise RuntimeError(f"{outcome}: TF-IDF/embedding rich comparator columns differ")
    if not np.allclose(
        xt.apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float),
        xe.apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float),
        equal_nan=True,
    ):
        raise RuntimeError(f"{outcome}: TF-IDF/embedding rich comparator values differ")

    ft = dt[8]
    fe = de[9]
    if list(ft.columns) != list(fe.columns) or not ft.equals(fe):
        raise RuntimeError(f"{outcome}: frozen split matrices differ")

    return {
        "merged": dt[0],
        "x_base": dt[1],
        "feature_names": dt[2],
        "y": dt[3],
        "groups": dt[4],
        "case_id": dt[5],
        "has_note": dt[6],
        "text": dt[7],
        "frozen_splits": dt[8],
        "registered_pred": dt[9],
        "tfidf_hashes": dt[10],
        "embedding_hashes": de[11],
        "source": dt[11],
        "embedding_matrix": de[7],
        "embedding_rows": de[8],
    }


def tfidf_train_test_scores(
    text: np.ndarray,
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

    if len(note_train_idx) == 0 or len(np.unique(y[note_train_idx])) != 2:
        raise RuntimeError("TF-IDF outer note-available training sample is degenerate")

    train_score = np.zeros(len(train_idx), dtype=float)
    train_score[train_note_mask] = tfidf.inner_crossfit_text(
        text[note_train_idx],
        y[note_train_idx],
        groups[note_train_idx],
        seed=int(inner_seed),
    )

    vec, model = tfidf.fit_text_model(text[note_train_idx], y[note_train_idx])
    test_score = np.zeros(len(test_idx), dtype=float)
    if len(note_test_idx):
        test_score[test_note_mask] = model.decision_function(
            vec.transform(text[note_test_idx].tolist())
        )

    if not np.isfinite(train_score).all() or not np.isfinite(test_score).all():
        raise RuntimeError("Non-finite TF-IDF decomposition scores")
    return train_score, test_score


def embedding_train_test_scores(
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

    if len(note_train_idx) == 0 or len(np.unique(y[note_train_idx])) != 2:
        raise RuntimeError("Embedding outer note-available training sample is degenerate")

    train_emb = embedding_matrix[embedding_rows[note_train_idx]]
    inner_score, selected_c, cv_means = embedding.inner_crossfit_embedding(
        train_emb,
        y[note_train_idx],
        groups[note_train_idx],
        seed=int(inner_seed),
    )
    train_score = np.zeros(len(train_idx), dtype=float)
    train_score[train_note_mask] = inner_score

    model = embedding.build_embedding_model(selected_c)
    model.fit(train_emb, y[note_train_idx])
    test_score = np.zeros(len(test_idx), dtype=float)
    if len(note_test_idx):
        test_score[test_note_mask] = model.decision_function(
            embedding_matrix[embedding_rows[note_test_idx]]
        )

    if not np.isfinite(train_score).all() or not np.isfinite(test_score).all():
        raise RuntimeError("Non-finite embedding decomposition scores")
    return train_score, test_score, float(selected_c), cv_means


def fit_level_models(
    x_level: pd.DataFrame,
    y: np.ndarray,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    tfidf_train: np.ndarray,
    tfidf_test: np.ndarray,
    embed_train: np.ndarray,
    embed_test: np.ndarray,
):
    tr = np.asarray(train_idx, dtype=int)
    te = np.asarray(test_idx, dtype=int)
    xb_tr = x_level.iloc[tr].reset_index(drop=True)
    xb_te = x_level.iloc[te].reset_index(drop=True)

    xt_tr = xb_tr.copy()
    xt_te = xb_te.copy()
    xt_tr["extension_tfidf_log_odds"] = tfidf_train
    xt_te["extension_tfidf_log_odds"] = tfidf_test

    xe_tr = xb_tr.copy()
    xe_te = xb_te.copy()
    xe_tr["extension_embedding_log_odds"] = embed_train
    xe_te["extension_embedding_log_odds"] = embed_test

    mb = tfidf.rich.build_hgb(20260924)
    mt = tfidf.rich.build_hgb(20260924)
    me = tfidf.rich.build_hgb(20260924)
    mb.fit(xb_tr, y[tr])
    mt.fit(xt_tr, y[tr])
    me.fit(xe_tr, y[tr])
    pb = mb.predict_proba(xb_te)[:, 1]
    pt = mt.predict_proba(xt_te)[:, 1]
    pe = me.predict_proba(xe_te)[:, 1]

    if not np.isfinite(pb).all() or not np.isfinite(pt).all() or not np.isfinite(pe).all():
        raise RuntimeError("Non-finite T1.5 HGB prediction")
    return pb, pt, pe


def metric_triplet(y: np.ndarray, pb: np.ndarray, pt: np.ndarray, pe: np.ndarray) -> dict:
    mb = tfidf.metrics_mod.basic_metrics(y, pb)
    mt = tfidf.metrics_mod.basic_metrics(y, pt)
    me = tfidf.metrics_mod.basic_metrics(y, pe)
    return {
        "comparator": {"auroc": float(mb["auroc"]), "auprc": float(mb["auprc"])},
        "tfidf_augmented": {"auroc": float(mt["auroc"]), "auprc": float(mt["auprc"])},
        "embedding_augmented": {"auroc": float(me["auroc"]), "auprc": float(me["auprc"])},
        "tfidf_delta": {
            "auroc": float(mt["auroc"] - mb["auroc"]),
            "auprc": float(mt["auprc"] - mb["auprc"]),
        },
        "embedding_delta": {
            "auroc": float(me["auroc"] - mb["auroc"]),
            "auprc": float(me["auprc"] - mb["auprc"]),
        },
    }


def point_estimates(outcome: str) -> dict:
    d = load_joint_population(outcome)
    context_freeze = json.loads(tfidf.CONTEXT_FREEZE.read_text(encoding="utf-8"))
    levels = decomp.comparator_levels(d["x_base"], outcome, context_freeze)
    level_results = {name: [] for name in levels}
    total = len(tfidf.REPEAT_SEEDS) * tfidf.FOLDS
    current = 0

    for ri, seed in enumerate(tfidf.REPEAT_SEEDS, start=1):
        folds = pd.to_numeric(
            d["frozen_splits"][f"repeat_{ri}_fold"], errors="raise"
        ).astype(int).to_numpy()
        check = pd.DataFrame({"subject_id": d["groups"], "fold": folds})
        if (check.groupby("subject_id")["fold"].nunique() > 1).any():
            raise RuntimeError(f"{outcome}: patient crosses outer folds in repeat {ri}")

        pred = {
            name: {
                "base": np.full(len(d["y"]), np.nan),
                "tfidf": np.full(len(d["y"]), np.nan),
                "embedding": np.full(len(d["y"]), np.nan),
            }
            for name in levels
        }
        c_by_fold = {}

        for fold in range(1, tfidf.FOLDS + 1):
            te = np.flatnonzero(folds == fold)
            tr = np.flatnonzero(folds != fold)
            ttr, tte = tfidf_train_test_scores(
                d["text"], d["y"], d["groups"], d["has_note"], tr, te,
                inner_seed=tfidf.INNER_SEED_BASE + 100 * ri + fold,
            )
            etr, ete, selected_c, cv_means = embedding_train_test_scores(
                d["embedding_matrix"], d["embedding_rows"], d["y"], d["groups"],
                d["has_note"], tr, te,
                inner_seed=embedding.INNER_SEED_BASE + 100 * ri + fold,
            )
            c_by_fold[str(fold)] = {
                "selected_c": selected_c,
                "inner_cv_mean_auroc": cv_means,
            }

            for level_name, cols in levels.items():
                pb, pt, pe = fit_level_models(
                    d["x_base"].loc[:, cols], d["y"], tr, te,
                    ttr, tte, etr, ete,
                )
                pred[level_name]["base"][te] = pb
                pred[level_name]["tfidf"][te] = pt
                pred[level_name]["embedding"][te] = pe

            current += 1
            update_progress(
                current=current,
                total=total,
                phase="extension_t1_decomposition_point_estimation",
                message=f"{outcome}: repeat {ri}/5 outer fold {fold}/5",
                unit="fold",
            )

        for level_name in levels:
            pp = pred[level_name]
            if any(np.isnan(pp[k]).any() for k in pp):
                raise RuntimeError(f"{outcome}: incomplete T1.5 predictions for {level_name}")
            m = metric_triplet(d["y"], pp["base"], pp["tfidf"], pp["embedding"])
            m.update({"repeat": ri, "seed": int(seed)})
            level_results[level_name].append(m)

        expected = pd.to_numeric(
            d["registered_pred"][f"comparator_repeat_{ri}"], errors="raise"
        ).to_numpy(dtype=float)
        observed_d = pred["D_registered_rich_comparator"]["base"]
        diff = float(np.max(np.abs(expected - observed_d)))
        if diff > 1e-12:
            raise RuntimeError(
                f"{outcome}: T1.5 D comparator differs from registered repeat {ri}; "
                f"max_abs_diff={diff}"
            )

    summary = {}
    for level_name, rows in level_results.items():
        tf_auc = [float(r["tfidf_delta"]["auroc"]) for r in rows]
        em_auc = [float(r["embedding_delta"]["auroc"]) for r in rows]
        summary[level_name] = {
            "feature_count": int(len(levels[level_name])),
            "feature_names": levels[level_name],
            "primary_repeat": rows[0],
            "repeats": rows,
            "tfidf_delta_auroc_range": [float(min(tf_auc)), float(max(tf_auc))],
            "embedding_delta_auroc_range": [float(min(em_auc)), float(max(em_auc))],
        }

    return {
        "outcome": outcome,
        "source": d["source"],
        "n": int(len(d["y"])),
        "cases": int(d["y"].sum()),
        "note_available_n": int(d["has_note"].sum()),
        "analysis_status": "post-registration exploratory",
        "levels": summary,
        "hashes": {
            "tfidf": d["tfidf_hashes"],
            "embedding": d["embedding_hashes"],
            "t1_5_clarification_sha256": tfidf.sha256_file(CLARIFICATION),
        },
    }


def bootstrap_refit_once(
    outcome: str,
    d: dict,
    primary_folds: np.ndarray,
    rng: np.random.Generator,
):
    context_freeze = json.loads(tfidf.CONTEXT_FREEZE.read_text(encoding="utf-8"))
    levels = decomp.comparator_levels(d["x_base"], outcome, context_freeze)
    selected_levels = {
        "A_structured_34": levels["A_structured_34"],
        "D_registered_rich_comparator": levels["D_registered_rich_comparator"],
    }

    split_indices = patient_cluster_refit_indices(d["groups"], primary_folds, rng)
    agg = {
        name: {"y": [], "base": [], "tfidf": [], "embedding": []}
        for name in selected_levels
    }

    for fold in range(1, tfidf.FOLDS + 1):
        tr, te = split_indices[fold]
        if len(te) == 0 or len(np.unique(d["y"][tr])) != 2:
            raise RuntimeError("Invalid T1.5 bootstrap outer split")

        ttr, tte = tfidf_train_test_scores(
            d["text"], d["y"], d["groups"], d["has_note"], tr, te,
            inner_seed=tfidf.INNER_SEED_BASE + fold,
        )
        etr, ete, _selected_c, _cv = embedding_train_test_scores(
            d["embedding_matrix"], d["embedding_rows"], d["y"], d["groups"],
            d["has_note"], tr, te,
            inner_seed=embedding.INNER_SEED_BASE + fold,
        )

        for level_name, cols in selected_levels.items():
            pb, pt, pe = fit_level_models(
                d["x_base"].loc[:, cols], d["y"], tr, te,
                ttr, tte, etr, ete,
            )
            agg[level_name]["y"].append(d["y"][te])
            agg[level_name]["base"].append(pb)
            agg[level_name]["tfidf"].append(pt)
            agg[level_name]["embedding"].append(pe)

    out = {}
    for level_name, a in agg.items():
        yy = np.concatenate(a["y"])
        pb = np.concatenate(a["base"])
        pt = np.concatenate(a["tfidf"])
        pe = np.concatenate(a["embedding"])
        if yy.sum() == 0 or yy.sum() == len(yy):
            return None
        out[level_name] = {
            "tfidf_delta_auroc": float(roc_auc_score(yy, pt) - roc_auc_score(yy, pb)),
            "embedding_delta_auroc": float(roc_auc_score(yy, pe) - roc_auc_score(yy, pb)),
            "tfidf_delta_auprc": float(
                average_precision_score(yy, pt) - average_precision_score(yy, pb)
            ),
            "embedding_delta_auprc": float(
                average_precision_score(yy, pe) - average_precision_score(yy, pb)
            ),
        }
    return out


def timing_gate(outcome: str) -> dict:
    d = load_joint_population(outcome)
    primary_folds = pd.to_numeric(
        d["frozen_splits"]["repeat_1_fold"], errors="raise"
    ).astype(int).to_numpy()

    children = np.random.SeedSequence(BOOTSTRAP_SEED).spawn(600)
    runtimes = []
    replacements = 0
    child_index = 0
    while len(runtimes) < BOOTSTRAP_TIMING_VALID:
        child = children[child_index]
        child_index += 1
        start = time.perf_counter()
        result = bootstrap_refit_once(
            outcome, d, primary_folds, np.random.default_rng(child)
        )
        elapsed = float(time.perf_counter() - start)
        if result is None:
            replacements += 1
            continue
        runtimes.append(elapsed)
        update_progress(
            current=len(runtimes),
            total=BOOTSTRAP_TIMING_VALID,
            phase="extension_t1_decomposition_bootstrap_timing",
            message=f"{outcome}: timing-only valid replicate {len(runtimes)}/10",
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


def summarize(values: list[float]) -> dict:
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
        raise RuntimeError(f"Unexpected T1.5 bootstrap target {target}")

    d = load_joint_population(outcome)
    primary_folds = pd.to_numeric(
        d["frozen_splits"]["repeat_1_fold"], errors="raise"
    ).astype(int).to_numpy()
    max_replacements = int(math.floor(target * MAX_REPLACEMENT_FRACTION))
    children = np.random.SeedSequence(BOOTSTRAP_SEED).spawn(
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
            outcome, d, primary_folds, np.random.default_rng(child)
        )
        if result is None:
            replacements.append(
                {"child_seed_index": seed_index, "reason": "single_class_heldout_evaluation"}
            )
            if len(replacements) > max_replacements:
                raise RuntimeError("T1.5 replacement fraction exceeded frozen 5% cap")
            continue
        results.append(result)
        if len(results) == 1 or len(results) % 5 == 0 or len(results) == target:
            update_progress(
                current=len(results),
                total=target,
                phase="extension_t1_decomposition_refit_bootstrap",
                message=f"{outcome}: valid T1.5 refit bootstrap {len(results)}/{target}",
                unit="replicate",
            )

    out = {
        "valid_replicates": int(len(results)),
        "target_valid_replicates": int(target),
        "replacement_count": int(len(replacements)),
        "replacement_log": replacements,
        "bootstrap_unit": "source_patient",
        "outer_partition": "repeat_1",
        "bootstrap_seed_sequence": BOOTSTRAP_SEED,
        "interval_type": "two-sided 95% percentile",
        "full_text_refit_each_replicate": True,
        "full_hgb_refit_each_replicate": True,
        "levels": {},
    }
    for level_name in ("A_structured_34", "D_registered_rich_comparator"):
        out["levels"][level_name] = {}
        for key in (
            "tfidf_delta_auroc",
            "embedding_delta_auroc",
            "tfidf_delta_auprc",
            "embedding_delta_auprc",
        ):
            out["levels"][level_name][key] = summarize(
                [float(r[level_name][key]) for r in results]
            )
    return out


def self_test() -> None:
    # Test only leakage-safe score helpers; level reconstruction is already covered by
    # src/160's existing synthetic test.
    n = 80
    rng = np.random.default_rng(20261006)
    groups = np.repeat(np.arange(40), 2)
    y = np.asarray([0, 0, 1, 1] * 20, dtype=int)
    text = np.asarray(
        ["stable patient", "stable oxygen", "worsening shock", "escalating support"] * 20,
        dtype=object,
    )
    has_note = np.ones(n, dtype=bool)
    has_note[::9] = False
    text[~has_note] = ""
    tr = np.arange(0, 60)
    te = np.arange(60, 80)
    ttr, tte = tfidf_train_test_scores(
        text, y, groups, has_note, tr, te, inner_seed=20261006
    )
    if not np.isfinite(ttr).all() or not np.isfinite(tte).all():
        raise RuntimeError("T1.5 self-test failed: TF-IDF scores")
    print(json.dumps({"t1_5_self_test": "passed"}, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Paper 1 extension T1.5 supervised-text comparator decomposition."
    )
    ap.add_argument("--outcome", choices=tuple(tfidf.OUTCOME_SPECS), required=True)
    ap.add_argument("--mode", choices=("timing", "full"), required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--timing-input")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return

    tfidf.require_osf_registration()
    for gate in (
        tfidf.ATTESTATION,
        tfidf.IMPLEMENTATION_CLARIFICATION,
        embedding.EMBEDDING_IMPLEMENTATION,
        embedding.CLASSIFIER_CLARIFICATION,
        CLARIFICATION,
    ):
        if not gate.exists():
            raise RuntimeError(f"Required extension gate missing: {gate}")

    point = point_estimates(args.outcome)
    report = {
        "analysis": "Paper 1 exploratory extension T1.5 supervised-text comparator decomposition",
        "status": "completed",
        "extension_status": "post-registration exploratory",
        "parent_registration": "ahxn9",
        "extension_osf_project": "wmyb2",
        "outcome": args.outcome,
        "mode": args.mode,
        "point_estimates": point,
        "guardrails": [
            "T1.5 is post-registration exploratory and is not causal mediation.",
            "TF-IDF and embedding training scores are regenerated within each outer training fold.",
            "No global OOF text score is reused as an HGB training feature.",
            "Comparator levels A-D are identical to the existing Open-Jev decomposition.",
            "Only A and D receive refit-bootstrap intervals, as predeclared.",
            "Every result is reported regardless of direction.",
        ],
    }

    if args.mode == "timing":
        timing = timing_gate(args.outcome)
        report["bootstrap_runtime_gate"] = timing
        report["bootstrap_status"] = (
            "timing gate complete; performance estimates from timing replicates discarded"
        )
    else:
        if not args.timing_input:
            raise RuntimeError("--timing-input is required in full mode")
        timing_path = Path(args.timing_input)
        timing_report = json.loads(timing_path.read_text(encoding="utf-8"))
        if timing_report.get("outcome") != args.outcome or timing_report.get("mode") != "timing":
            raise RuntimeError("Timing input does not match requested T1.5 outcome/mode")
        timing = timing_report["bootstrap_runtime_gate"]
        report["bootstrap_runtime_gate"] = timing
        report["primary_refit_bootstrap"] = run_full_bootstrap(args.outcome, timing)
        report["bootstrap_status"] = "completed"

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "completed",
                "analysis": "T1.5",
                "outcome": args.outcome,
                "mode": args.mode,
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
