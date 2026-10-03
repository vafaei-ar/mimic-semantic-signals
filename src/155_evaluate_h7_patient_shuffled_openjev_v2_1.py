from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from registration_gate import require_osf_registration
from runrelay_progress import update_progress


SHUFFLE_SEED = 20260929
RISK_DECILES = 10

ANALYSES = {
    "ventilation": {
        "outcome": "invasive_ventilation",
        "source": "metavision",
        "population_section": "confirmatory_outcomes",
        "population_key": "invasive_ventilation",
        "context_file": "preregistration_context_features_v2_1_local.csv",
        "semantics_file": "openjev_registered_v2_1_raw_local.jsonl",
        "label": "Ventilation",
    },
    "rrt": {
        "outcome": "renal_replacement_therapy",
        "source": "metavision",
        "population_section": "confirmatory_outcomes",
        "population_key": "renal_replacement_therapy",
        "context_file": "preregistration_context_features_v2_1_local.csv",
        "semantics_file": "openjev_registered_v2_1_raw_local.jsonl",
        "label": "RRT",
    },
    "death_metavision": {
        "outcome": "icu_death",
        "source": "metavision",
        "population_section": "confirmatory_outcomes",
        "population_key": "icu_death",
        "context_file": "preregistration_context_features_v2_1_local.csv",
        "semantics_file": "openjev_registered_v2_1_raw_local.jsonl",
        "label": "MetaVision ICU death",
    },
    "death_carevue": {
        "outcome": "icu_death",
        "source": "carevue",
        "population_section": "prespecified_replications",
        "population_key": "icu_death_carevue",
        "context_file": "preregistration_context_features_v2_1_carevue_local.csv",
        "semantics_file": "openjev_registered_v2_1_carevue_raw_local.jsonl",
        "label": "CareVue ICU death",
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


h1 = load_numbered_module("120_evaluate_h1_ventilation_openjev_v2_1.py", "h1_v2_1")
rich = h1.rich
carevue = load_numbered_module(
    "154_evaluate_h6_carevue_death_openjev_v2_1.py", "carevue_h6_v2_1"
)


def sha256_file(path: Path) -> str:
    return h1.sha256_file(path)


def crossfit_base(x_base: pd.DataFrame, y: np.ndarray, folds: np.ndarray) -> np.ndarray:
    p = np.full(len(y), np.nan, dtype=float)
    for fold in range(1, h1.FOLDS + 1):
        te = np.flatnonzero(folds == fold)
        tr = np.flatnonzero(folds != fold)
        if len(te) == 0:
            raise RuntimeError(f"Empty held-out fold {fold}")
        if y[tr].sum() == 0 or y[tr].sum() == len(tr):
            raise RuntimeError(f"Degenerate training labels in fold {fold}")
        model = rich.build_hgb(20260924)
        model.fit(x_base.iloc[tr], y[tr])
        p[te] = model.predict_proba(x_base.iloc[te])[:, 1]
    if np.isnan(p).any() or not np.isfinite(p).all():
        raise RuntimeError("Incomplete/non-finite comparator OOF predictions")
    return p


def balanced_patient_risk_deciles(
    subject_ids: np.ndarray,
    risks: np.ndarray,
    has_note: np.ndarray,
) -> tuple[dict[int, int], list[dict]]:
    d = pd.DataFrame(
        {
            "subject_id": pd.to_numeric(subject_ids, errors="raise").astype("int64"),
            "risk": np.asarray(risks, dtype=float),
            "has_note": np.asarray(has_note, dtype=int),
        }
    )
    p = (
        d[d["has_note"].eq(1)]
        .groupby("subject_id", as_index=False)["risk"]
        .mean()
        .sort_values(["risk", "subject_id"], kind="mergesort")
        .reset_index(drop=True)
    )
    if len(p) < RISK_DECILES:
        raise RuntimeError("Fewer than 10 note-available patients")
    p["risk_decile"] = (
        np.floor(np.arange(len(p), dtype=float) * RISK_DECILES / len(p)).astype(int) + 1
    )
    mapping = dict(zip(p["subject_id"].astype(int), p["risk_decile"].astype(int)))
    summary = []
    for decile, g in p.groupby("risk_decile", sort=True):
        summary.append(
            {
                "decile": int(decile),
                "patients": int(len(g)),
                "risk_min": float(g["risk"].min()),
                "risk_max": float(g["risk"].max()),
                "risk_mean": float(g["risk"].mean()),
            }
        )
    return mapping, summary


def shuffle_semantic_vectors_between_patients(
    sem_matrix: pd.DataFrame,
    subject_ids: np.ndarray,
    has_note: np.ndarray,
    patient_deciles: dict[int, int],
    *,
    seed: int = SHUFFLE_SEED,
) -> tuple[pd.DataFrame, dict]:
    subjects = pd.to_numeric(pd.Series(subject_ids), errors="raise").astype("int64").to_numpy()
    note_mask = np.asarray(has_note, dtype=int) == 1
    if sem_matrix.loc[note_mask].isna().any().any():
        raise RuntimeError("Note-available semantic matrix is incomplete")
    if sem_matrix.loc[~note_mask].notna().any().any():
        raise RuntimeError("No-note row unexpectedly has semantic scores before shuffle")

    rng = np.random.default_rng(seed)
    shuffled = sem_matrix.copy(deep=True)
    permutation_pairs = []
    decile_rows = []

    for decile in range(1, RISK_DECILES + 1):
        recipient = np.array(
            [
                i
                for i in np.flatnonzero(note_mask)
                if patient_deciles.get(int(subjects[i])) == decile
            ],
            dtype=int,
        )
        if len(recipient) < 2:
            raise RuntimeError(f"Risk decile {decile} has fewer than 2 note rows")
        counts = pd.Series(subjects[recipient]).value_counts()
        if int(counts.max()) * 2 > len(recipient):
            raise RuntimeError(
                f"Risk decile {decile} cannot be permuted strictly between patients"
            )

        donor = None
        for _ in range(10000):
            candidate = rng.permutation(recipient)
            if np.all(subjects[candidate] != subjects[recipient]):
                donor = candidate
                break
        if donor is None:
            raise RuntimeError(
                f"Could not construct deterministic between-patient permutation in decile {decile}"
            )

        shuffled.iloc[recipient, :] = sem_matrix.iloc[donor, :].to_numpy()
        permutation_pairs.extend(zip(recipient.tolist(), donor.tolist()))
        decile_rows.append(
            {
                "decile": decile,
                "note_rows": int(len(recipient)),
                "note_patients": int(pd.Series(subjects[recipient]).nunique()),
                "same_patient_assignments": int(
                    np.sum(subjects[recipient] == subjects[donor])
                ),
            }
        )

    if int(sum(x["note_rows"] for x in decile_rows)) != int(note_mask.sum()):
        raise RuntimeError("Not all note-available rows were assigned to a risk decile")
    if any(x["same_patient_assignments"] != 0 for x in decile_rows):
        raise RuntimeError("Shuffle retained within-patient semantic assignments")

    for col in h1.SEMANTIC_NAMES:
        before = np.sort(sem_matrix.loc[note_mask, col].to_numpy(dtype=float))
        after = np.sort(shuffled.loc[note_mask, col].to_numpy(dtype=float))
        if not np.array_equal(before, after):
            raise RuntimeError(f"Shuffle did not preserve marginal values for {col}")

    pair_arr = np.asarray(permutation_pairs, dtype="<i8")
    permutation_sha256 = hashlib.sha256(pair_arr.tobytes()).hexdigest()
    return shuffled, {
        "seed": int(seed),
        "risk_deciles": RISK_DECILES,
        "patient_risk_aggregation": (
            "mean repeat-1 rich-comparator OOF risk across that patient's note-available rows"
        ),
        "decile_assignment": (
            "sort note-available patients by mean risk then subject_id; assign balanced deciles "
            "by deterministic rank"
        ),
        "permutation_unit": "complete eight-score row vector",
        "permutation_constraint": (
            "vectors permuted only within patient risk decile and donor patient must differ "
            "from recipient patient"
        ),
        "note_rows_permuted": int(note_mask.sum()),
        "note_patients": int(pd.Series(subjects[note_mask]).nunique()),
        "same_patient_assignments": 0,
        "marginal_semantic_values_preserved_exactly": True,
        "permutation_index_sha256": permutation_sha256,
        "decile_rows": decile_rows,
    }


def load_analysis_inputs(args, spec):
    base = Path(args.base).expanduser().resolve()
    split_manifest_path = Path(args.split_manifest).expanduser().resolve()
    split_manifest = json.loads(split_manifest_path.read_text(encoding="utf-8"))
    context_freeze_path = Path(args.context_freeze).expanduser().resolve()
    context_freeze = json.loads(context_freeze_path.read_text(encoding="utf-8"))
    population_path = Path(args.analysis_populations).expanduser().resolve()
    population = json.loads(population_path.read_text(encoding="utf-8"))
    clarify_path = Path(args.preanalysis_clarifications).expanduser().resolve()
    clarifications = json.loads(clarify_path.read_text(encoding="utf-8"))

    outcome = spec["outcome"]
    expected = population[spec["population_section"]][spec["population_key"]]
    source = str(expected["source"]).strip().lower()

    structured_path = base / outcome / "enhanced_structured_features_v2_1_local.csv"
    context_path = base / outcome / spec["context_file"]
    semantic_path = base / outcome / spec["semantics_file"]
    index_path = base / outcome / "population_index_local.csv"

    structured = pd.read_csv(structured_path, low_memory=False)
    context = pd.read_csv(context_path, low_memory=False)
    idx = pd.read_csv(index_path, usecols=["case_id", "dbsource"], low_memory=False)

    structured["case_id"] = structured["case_id"].astype(str)
    idx["case_id"] = idx["case_id"].astype(str)
    idx["dbsource"] = (
        idx["dbsource"].fillna("unknown").astype(str).str.strip().str.lower()
    )
    structured = structured.merge(idx, on="case_id", how="left", validate="one_to_one")
    structured = (
        structured[structured["dbsource"].eq(source)]
        .drop(columns=["dbsource"])
        .reset_index(drop=True)
    )

    observed = {
        "rows": int(len(structured)),
        "unique_patients": int(structured["subject_id"].nunique()),
        "cases": int(structured["label"].astype(int).sum()),
        "controls": int(len(structured) - structured["label"].astype(int).sum()),
    }
    for key, value in observed.items():
        if int(expected[key]) != value:
            raise RuntimeError(
                f"{args.analysis}: registered population mismatch {key}: "
                f"{value} != {expected[key]}"
            )

    merged, x_base, _ = rich.prepare_rich_features(
        structured, context, outcome, context_freeze
    )
    y = merged["label"].astype(int).to_numpy()
    groups = pd.to_numeric(merged["subject_id"], errors="raise").astype("int64").to_numpy()

    if args.analysis == "death_carevue":
        frozen_splits, split_hash = carevue.load_carevue_splits(
            merged, base, split_manifest
        )
    else:
        frozen_splits, split_hash = rich.load_frozen_splits(
            merged, outcome, base, split_manifest
        )

    sem = h1.load_semantics(semantic_path)
    sem_ids = set(sem["case_id"])
    merged_ids = set(merged["case_id"].astype(str))
    if not sem_ids.issubset(merged_ids):
        raise RuntimeError(
            f"{args.analysis}: semantic inference contains case_ids outside frozen population"
        )

    has_note = pd.to_numeric(merged["has_note"], errors="raise").astype(int)
    note_ids = set(merged.loc[has_note.eq(1), "case_id"].astype(str))
    if sem_ids != note_ids:
        raise RuntimeError(
            f"{args.analysis}: semantic/note availability mismatch "
            f"missing={len(note_ids-sem_ids)}, extra={len(sem_ids-note_ids)}"
        )

    sem = sem.set_index("case_id").reindex(merged["case_id"].astype(str))
    sem_matrix = sem.loc[:, h1.SEMANTIC_NAMES].astype(float).reset_index(drop=True)
    has_note = has_note.reset_index(drop=True)
    if sem_matrix.loc[has_note.eq(1)].isna().any().any():
        raise RuntimeError("Note-available row has incomplete semantic scores")
    if sem_matrix.loc[has_note.eq(0)].notna().any().any():
        raise RuntimeError("No-note row unexpectedly has semantic scores")

    return {
        "base": base,
        "split_manifest_path": split_manifest_path,
        "context_freeze_path": context_freeze_path,
        "population_path": population_path,
        "clarify_path": clarify_path,
        "clarifications": clarifications,
        "outcome": outcome,
        "source": source,
        "expected": expected,
        "structured_path": structured_path,
        "context_path": context_path,
        "semantic_path": semantic_path,
        "merged": merged,
        "x_base": x_base.reset_index(drop=True),
        "y": y,
        "groups": groups,
        "frozen_splits": frozen_splits,
        "split_hash": split_hash,
        "sem_matrix": sem_matrix,
        "has_note": has_note.to_numpy(dtype=int),
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Registered v2.1 H7 patient-shuffled semantic negative control."
    )
    ap.add_argument("--analysis", required=True, choices=sorted(ANALYSES))
    ap.add_argument("--base", required=True)
    ap.add_argument("--split-manifest", required=True)
    ap.add_argument("--context-freeze", required=True)
    ap.add_argument("--analysis-populations", required=True)
    ap.add_argument("--preanalysis-clarifications", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    require_osf_registration()
    spec = ANALYSES[args.analysis]
    d = load_analysis_inputs(args, spec)

    primary_folds = pd.to_numeric(
        d["frozen_splits"]["repeat_1_fold"], errors="raise"
    ).astype(int).to_numpy()
    check = pd.DataFrame({"subject_id": d["groups"], "fold": primary_folds})
    if (check.groupby("subject_id")["fold"].nunique() > 1).any():
        raise RuntimeError("Patient crosses folds in repeat 1")

    comparator_risk = crossfit_base(d["x_base"], d["y"], primary_folds)
    patient_deciles, decile_patient_summary = balanced_patient_risk_deciles(
        d["groups"], comparator_risk, d["has_note"]
    )
    shuffled_sem, shuffle_report = shuffle_semantic_vectors_between_patients(
        d["sem_matrix"], d["groups"], d["has_note"], patient_deciles
    )
    shuffle_report["decile_patients"] = decile_patient_summary

    x_aug = pd.concat([d["x_base"], shuffled_sem], axis=1)

    repeat_results = []
    repeat_predictions = []
    for ri, seed in enumerate(h1.REPEAT_SEEDS, start=1):
        folds = pd.to_numeric(
            d["frozen_splits"][f"repeat_{ri}_fold"], errors="raise"
        ).astype(int).to_numpy()
        check = pd.DataFrame({"subject_id": d["groups"], "fold": folds})
        if (check.groupby("subject_id")["fold"].nunique() > 1).any():
            raise RuntimeError(f"Patient crosses folds in repeat {ri}")
        pb, pa = h1.crossfit_pair(d["x_base"], x_aug, d["y"], folds)
        if ri == 1 and not np.array_equal(pb, comparator_risk):
            if not np.allclose(pb, comparator_risk, rtol=0.0, atol=1e-15):
                raise RuntimeError("Repeat-1 comparator predictions changed during H7 evaluation")
        mb, ma, delta = h1.metric_pair(d["y"], pb, pa)
        repeat_results.append(
            {
                "repeat": ri,
                "seed": int(seed),
                "comparator": mb,
                "shuffled_augmented": ma,
                "delta": delta,
            }
        )
        repeat_predictions.append((pb, pa))
        update_progress(
            current=ri,
            total=5,
            phase="v2_1_h7_point_estimates",
            message=f"{spec['label']} H7 repeat {ri}/5 complete",
            unit="repeat",
        )

    primary_pb, primary_pa = repeat_predictions[0]
    observed_delta = float(
        roc_auc_score(d["y"], primary_pa) - roc_auc_score(d["y"], primary_pb)
    )

    target = int(
        d["clarifications"]["bootstrap_failure_rule"]["target_valid_replicates"]
    )
    max_frac = float(
        d["clarifications"]["bootstrap_failure_rule"][
            "maximum_degenerate_replacement_fraction"
        ]
    )
    max_replacements = int(np.floor(target * max_frac))
    seed_sequence = np.random.SeedSequence(20260924)
    child_seeds = seed_sequence.spawn(target + max_replacements + 1)

    boot = []
    dca_boot = {
        str(t): [] for t in d["clarifications"]["decision_curve"]["thresholds"]
    }
    replacements = []
    child_index = 0

    while len(boot) < target:
        if child_index >= len(child_seeds):
            raise RuntimeError("Exhausted deterministic bootstrap replacement seeds")
        child = child_seeds[child_index]
        child_index += 1
        rng = np.random.default_rng(child)

        split_indices = h1.patient_cluster_refit_indices(
            d["groups"], primary_folds, rng
        )
        eval_y, eval_pb, eval_pa = [], [], []

        for fold in range(1, h1.FOLDS + 1):
            tr, te = split_indices[fold]
            if len(te) == 0:
                raise RuntimeError(
                    f"Bootstrap replicate {len(boot)+1}: empty fold {fold}"
                )
            if d["y"][tr].sum() == 0 or d["y"][tr].sum() == len(tr):
                raise RuntimeError(
                    f"Bootstrap replicate {len(boot)+1}: degenerate training fold {fold}"
                )
            p0, p1 = h1.fit_pair(d["x_base"], x_aug, d["y"], tr, te)
            eval_y.append(d["y"][te])
            eval_pb.append(p0)
            eval_pa.append(p1)

        yy = np.concatenate(eval_y)
        pb = np.concatenate(eval_pb)
        pa = np.concatenate(eval_pa)

        if yy.sum() == 0 or yy.sum() == len(yy):
            replacements.append(
                {
                    "child_seed_index": child_index - 1,
                    "reason": "single_class_heldout_evaluation",
                }
            )
            if len(replacements) > max_replacements:
                raise RuntimeError(
                    "Degenerate bootstrap replacement fraction exceeded frozen 5% limit"
                )
            continue

        metrics = h1.simple_bootstrap_metrics(yy, pb, pa)
        nb0 = h1.decision_curve_net_benefit(
            yy, pb, d["clarifications"]["decision_curve"]["thresholds"]
        )
        nb1 = h1.decision_curve_net_benefit(
            yy, pa, d["clarifications"]["decision_curve"]["thresholds"]
        )
        for t in dca_boot:
            dca_boot[t].append(float(nb1[t] - nb0[t]))
        boot.append(metrics)

        if len(boot) % 5 == 0 or len(boot) == target:
            update_progress(
                current=len(boot),
                total=target,
                phase="v2_1_h7_refit_bootstrap",
                message=f"{spec['label']} H7 refit bootstrap {len(boot)}/{target}",
                unit="replicate",
            )

    boot_summary = {}
    for key in ("delta_auroc", "delta_auprc", "delta_brier", "delta_log_loss"):
        values = [r[key] for r in boot]
        boot_summary[key] = {
            "mean": float(np.mean(values)),
            "sd": float(np.std(values, ddof=1)),
            "ci95_percentile": h1.percentile_ci(values),
        }

    dca_primary_base = h1.decision_curve_net_benefit(
        d["y"], primary_pb, d["clarifications"]["decision_curve"]["thresholds"]
    )
    dca_primary_aug = h1.decision_curve_net_benefit(
        d["y"], primary_pa, d["clarifications"]["decision_curve"]["thresholds"]
    )
    dca = {}
    for t in dca_boot:
        dca[t] = {
            "comparator_net_benefit": dca_primary_base[t],
            "shuffled_augmented_net_benefit": dca_primary_aug[t],
            "delta_net_benefit": float(
                dca_primary_aug[t] - dca_primary_base[t]
            ),
            "delta_ci95_percentile": h1.percentile_ci(dca_boot[t]),
        }

    pred_path = (
        d["base"]
        / d["outcome"]
        / f"h7_patient_shuffled_{args.analysis}_predictions_v2_1_local.csv"
    )
    local_pred = d["merged"][["case_id", "subject_id", "icustay_id", "label"]].copy()
    for ri, (pb, pa) in enumerate(repeat_predictions, start=1):
        local_pred[f"comparator_repeat_{ri}"] = pb
        local_pred[f"shuffled_augmented_repeat_{ri}"] = pa
    local_pred.to_csv(pred_path, index=False)

    split_deltas = [float(r["delta"]["auroc"]) for r in repeat_results]
    report = {
        "analysis": "Registered v2.1 H7 patient-shuffled semantic negative control",
        "status": "completed",
        "registration_id": "ahxn9",
        "doi": "10.17605/OSF.IO/AHXN9",
        "analysis_key": args.analysis,
        "outcome": d["outcome"],
        "source": d["source"],
        "n": int(len(d["y"])),
        "cases": int(d["y"].sum()),
        "controls": int(len(d["y"]) - d["y"].sum()),
        "note_available_rows_with_complete_openjev": int(d["has_note"].sum()),
        "semantic_constructs": list(h1.SEMANTIC_NAMES),
        "shuffle": shuffle_report,
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
        "estimand": (
            "repeat-1 OOF delta_AUROC = AUROC(rich comparator + patient-shuffled "
            "stripped Open-Jev) - AUROC(rich comparator)"
        ),
        "primary_repeat": repeat_results[0],
        "split_stability": {
            "repeat_delta_auroc": split_deltas,
            "repeats_2_to_5_range": [
                float(min(split_deltas[1:])),
                float(max(split_deltas[1:])),
            ],
            "all_five_range": [float(min(split_deltas)), float(max(split_deltas))],
        },
        "refit_bootstrap": {
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
            "structured_input_sha256": sha256_file(d["structured_path"]),
            "context_input_sha256": sha256_file(d["context_path"]),
            "semantic_input_sha256": sha256_file(d["semantic_path"]),
            "split_sha256": d["split_hash"],
            "split_manifest_sha256": sha256_file(d["split_manifest_path"]),
            "context_freeze_sha256": sha256_file(d["context_freeze_path"]),
            "analysis_population_contract_sha256": sha256_file(d["population_path"]),
            "preanalysis_clarifications_sha256": sha256_file(d["clarify_path"]),
        },
        "local_prediction_file": str(pred_path),
        "guardrails": [
            "Patient risk strata use repeat-1 rich-comparator out-of-fold risk only.",
            "The shuffle seed is frozen at 20260929.",
            "Complete eight-score vectors are permuted only within risk decile and only between different patients.",
            "No-note rows remain no-note rows with missing semantic values.",
            "The shuffled semantic matrix preserves each construct's note-row marginal values exactly.",
            "The same frozen folds, preprocessing, HGB settings, and patient-cluster refit-bootstrap procedure are reused.",
            "No p-values, multiplicity testing, or binary success criterion is produced.",
            "Row-level predictions and permutation mappings remain local; the shared artifact is aggregate only.",
        ],
    }

    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
