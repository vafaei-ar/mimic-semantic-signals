from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd

from runrelay_progress import update_progress


SPLITS = ("train", "validation", "test")
OUTCOMES = ("invasive_ventilation", "renal_replacement_therapy", "icu_death")
SPLIT_SEED = 20260924
HASH_NAMESPACE = "multitask_tuning_v1"


def load_builder():
    path = Path(__file__).with_name("54_build_multitask_benchmark.py")
    spec = importlib.util.spec_from_file_location("frozen_multitask_builder_v1", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load frozen multitask benchmark builder.")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def patient_split(subject_id: int, seed: int) -> str:
    raw = f"{HASH_NAMESPACE}|{seed}|{int(subject_id)}".encode("utf-8")
    value = int.from_bytes(hashlib.sha256(raw).digest()[:8], "big") / float(2**64)
    if value < 0.70:
        return "train"
    if value < 0.85:
        return "validation"
    return "test"


def write_outputs(mod, base: Path, split: str, snapshots: pd.DataFrame, features: pd.DataFrame) -> dict:
    outcome = str(snapshots["outcome"].iloc[0])
    outdir = base / split / outcome
    outdir.mkdir(parents=True, exist_ok=True)

    index_cols = [
        "case_id", "label", "match_set", "patient_group",
        "subject_id", "hadm_id", "icustay_id",
        "note_time", "event_time", "category", "dbsource",
        "hours_since_icu", "hours_before_event",
        "storetime_available", "documentation_delay_hours",
    ]
    idx = snapshots[[c for c in index_cols if c in snapshots.columns]].copy()
    idx["tuning_split"] = split
    idx.to_csv(outdir / "snapshot_index_local.csv", index=False)

    safe_cols = [
        "case_id", "label", "match_set", "patient_group",
        "category", "dbsource", "hours_since_icu",
    ]
    safe = snapshots[safe_cols].merge(features, on="case_id", how="left")
    safe["tuning_split"] = split
    safe.to_csv(outdir / "structured_features.csv", index=False)

    with (outdir / "cases.jsonl").open("w", encoding="utf-8") as f:
        for row in snapshots.itertuples(index=False):
            rec = {
                "case_id": row.case_id,
                "synthetic_only": False,
                "local_only": True,
                "model_state": {"clinical_note": str(row.text)},
                "metadata": {
                    "analysis": "postfreeze_multitask_tuning_cohort_v1",
                    "tuning_split": split,
                    "outcome": outcome,
                    "label": int(row.label),
                    "match_set": int(row.match_set),
                    "patient_group": str(row.patient_group),
                    "note_category": str(row.category),
                    "dbsource": str(row.dbsource),
                    "hours_since_icu": round(float(row.hours_since_icu), 3),
                    "prediction_horizon_hours": float(mod.OUTCOME_SPECS[outcome]["horizon_hours"]),
                    "note_availability_basis": (
                        "max(charttime, storetime)"
                        if bool(getattr(row, "storetime_available", False))
                        else "charttime_fallback"
                    ),
                    "documentation_delay_hours": (
                        round(float(row.documentation_delay_hours), 3)
                        if pd.notna(getattr(row, "documentation_delay_hours", np.nan))
                        else None
                    ),
                    "note_characters": len(str(row.text)),
                },
                "questions": mod.SEMANTIC_CONSTRUCTS,
                "gold": None,
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    return {
        "cases_path": str(outdir / "cases.jsonl"),
        "features_path": str(outdir / "structured_features.csv"),
        "local_index_path": str(outdir / "snapshot_index_local.csv"),
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Build patient-first, split-specific post-freeze MIMIC tuning cohorts."
    )
    ap.add_argument("--root", required=True)
    ap.add_argument("--local-output-root", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--controls-per-case", type=int, default=3)
    ap.add_argument("--split-seed", type=int, default=SPLIT_SEED)
    ap.add_argument("--matching-seed", type=int, default=20260924)
    ap.add_argument("--washout-hours", type=float, default=6.0)
    ap.add_argument("--vital-lookback-hours", type=float, default=6.0)
    ap.add_argument("--lab-lookback-hours", type=float, default=24.0)
    args = ap.parse_args()

    mod = load_builder()
    root = mod.resolve_root(args.root)
    local_root = Path(args.local_output_root).expanduser().resolve()
    manifest_path = Path(args.manifest).expanduser().resolve()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    update_progress(current=1, total=8, phase="source", message="Loading ICU stays and endpoint evidence", unit="stage")
    icu = mod.load_icustays(root)
    icu["subject_id"] = pd.to_numeric(icu["subject_id"], errors="raise").astype(int)
    unique_subjects = sorted(icu["subject_id"].unique().tolist())
    split_map = {sid: patient_split(sid, args.split_seed) for sid in unique_subjects}
    icu["tuning_split"] = icu["subject_id"].map(split_map)

    evidence = mod.scan_event_evidence(root)
    assigned = mod.assign_evidence_to_icu(evidence, icu.drop(columns=["tuning_split"]))

    update_progress(current=2, total=8, phase="notes", message="Loading prospectively available bedside notes once", unit="stage")
    notes = mod.load_notes(root, set(icu["hadm_id"].astype(int)))
    note_icu = mod.assign_notes_to_icu(notes, icu.drop(columns=["tuning_split"]))
    note_icu["tuning_split"] = note_icu["subject_id"].astype(int).map(split_map)

    cohorts = {}
    split_reports = {}
    selected_subjects_by_split = {split: set() for split in SPLITS}
    assignment_counts = {
        split: int(sum(1 for sid in unique_subjects if split_map[sid] == split))
        for split in SPLITS
    }

    for split_idx, split in enumerate(SPLITS):
        update_progress(
            current=3 + split_idx,
            total=8,
            phase="matching",
            message=f"Building {split} split cohorts with within-split 1:3 matching",
            unit="stage",
        )
        split_subjects = {sid for sid in unique_subjects if split_map[sid] == split}
        icu_split = icu[icu["subject_id"].isin(split_subjects)].drop(columns=["tuning_split"]).copy()
        assigned_split = assigned[assigned["subject_id"].astype(int).isin(split_subjects)].copy()
        notes_split = note_icu[note_icu["subject_id"].astype(int).isin(split_subjects)].drop(columns=["tuning_split"]).copy()

        vent_events, vent_map, vent_prevalent = mod.build_incident_event_table(
            assigned_split,
            {"vent_procedure"},
            {"vent_procedure", "vent_explicit_chart", "vent_support"},
            args.washout_hours,
        )
        rrt_events, rrt_map, rrt_prevalent = mod.build_incident_event_table(
            assigned_split,
            {"rrt_procedure", "rrt_active_chart"},
            {"rrt_procedure", "rrt_active_chart", "rrt_strict_output"},
            args.washout_hours,
        )
        death_events, death_map = mod.load_death_table(root, icu_split, args.washout_hours)

        outcome_inputs = {
            "invasive_ventilation": (vent_events, vent_map, vent_prevalent),
            "renal_replacement_therapy": (rrt_events, rrt_map, rrt_prevalent),
            "icu_death": (death_events, death_map, set()),
        }

        split_reports[split] = {}
        for outcome_idx, outcome in enumerate(OUTCOMES):
            events, dmap, prevalent = outcome_inputs[outcome]
            rng = random.Random(args.matching_seed + split_idx * 1000 + outcome_idx * 100)
            s = mod.match_outcome(
                outcome,
                notes_split,
                events,
                dmap,
                prevalent,
                12.0,
                args.controls_per_case,
                rng,
            ).copy()
            s["case_id"] = split + "_" + s["case_id"].astype(str)
            s["patient_group"] = split + "_" + s["patient_group"].astype(str)
            cohorts[(split, outcome)] = s
            selected_subjects_by_split[split].update(s["subject_id"].astype(int).tolist())

            case = s[s["label"] == 1].copy()
            ctrl = s[s["label"] == 0].copy()
            exact_cat = s.groupby("match_set")["category"].nunique().eq(1).mean()
            split_reports[split][outcome] = {
                "matched_cases": int(len(case)),
                "matched_controls": int(len(ctrl)),
                "total_snapshots": int(len(s)),
                "unique_patients": int(s["subject_id"].nunique()),
                "case_note_lead_time_hours": mod.qstats(case["hours_before_event"]),
                "complete_sets_exact_note_category_fraction": float(exact_cat),
                "blank_notes": int(s["text"].astype(str).str.strip().eq("").sum()),
            }

    all_snaps = pd.concat(list(cohorts.values()), ignore_index=True, sort=False)
    if all_snaps["case_id"].duplicated().any():
        raise RuntimeError("Duplicate case_id across tuning splits/outcomes.")

    update_progress(current=6, total=8, phase="structured_scan", message="Extracting contemporaneous structured features for tuning cohorts", unit="stage")
    phys = mod.extract_physio(root, all_snaps, args.vital_lookback_hours, args.lab_lookback_hours)

    update_progress(current=7, total=8, phase="outputs", message="Writing local tuning cases and aggregate manifest", unit="stage")
    output_paths = {}
    for split in SPLITS:
        output_paths[split] = {}
        for outcome in OUTCOMES:
            s = cohorts[(split, outcome)]
            p = phys[phys["case_id"].isin(set(s["case_id"]))].copy()
            output_paths[split][outcome] = write_outputs(mod, local_root, split, s, p)

    overlaps = {}
    for i, a in enumerate(SPLITS):
        for b in SPLITS[i + 1:]:
            overlaps[f"{a}_vs_{b}"] = int(len(selected_subjects_by_split[a] & selected_subjects_by_split[b]))
    if any(overlaps.values()):
        raise RuntimeError(f"Patient leakage across tuning splits: {overlaps}")

    manifest = {
        "analysis": "Post-freeze patient-first multitask tuning cohort build v1",
        "protocol": "docs/multitask_tuning_cohort_protocol_v1.md",
        "zero_shot_freeze": "docs/multitask_zero_shot_freeze_v1.md",
        "local_only": True,
        "model_inference_performed": False,
        "tuning_performance_seen_before_cohort_freeze": False,
        "contains_credentialed_note_text_in_declared_artifact": False,
        "contains_source_patient_identifiers_in_declared_artifact": False,
        "patient_partition": {
            "method": "SHA-256 deterministic subject-level split before outcome matching",
            "namespace": HASH_NAMESPACE,
            "seed": int(args.split_seed),
            "ratios": {"train": 0.70, "validation": 0.15, "test": 0.15},
            "all_icu_unique_patient_counts": assignment_counts,
            "selected_cohort_patient_overlap": overlaps,
        },
        "controls_per_case": int(args.controls_per_case),
        "washout_hours": float(args.washout_hours),
        "matching": (
            "Rebuilt independently within each patient split; 1:3 without replacement by control patient; "
            "same dbsource required; priority to exact note category and ICU elapsed-time distance <=6h; "
            "maximum elapsed-time distance 12h"
        ),
        "prospective_note_time": "max(CHARTTIME, STORETIME) when STORETIME exists; CHARTTIME fallback otherwise",
        "splits": split_reports,
        "local_output_paths": output_paths,
        "guardrail": (
            "These are post-freeze tuning cohorts. The test split is locked until model architecture, "
            "training objective, hyperparameters, and checkpoint-selection rules are frozen. "
            "The original zero-shot cohorts and artifacts remain unchanged."
        ),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    update_progress(current=8, total=8, phase="done", message="Completed patient-first tuning cohort build", unit="stage")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
