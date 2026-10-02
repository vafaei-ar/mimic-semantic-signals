from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pandas as pd

from runrelay_progress import update_progress

ANALYSIS = "invasive_ventilation_any_support_sensitivity"
BASE_OUTCOME = "invasive_ventilation"
SOURCE = "metavision"

def load_numbered_module(filename: str, name: str):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {filename}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

structured_mod = load_numbered_module("105_build_enhanced_structured_baseline_v2_1.py", "structured_v2_1")
split_mod = load_numbered_module("106_freeze_enhanced_structured_cv_splits_v2_1.py", "splits_v2_1")
context_mod = load_numbered_module("114_build_preregistration_context_features_v2_1.py", "context_v2_1")
notes_mod = load_numbered_module("115_build_fixed_note_corpora_v2_1.py", "notes_v2_1")

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def bool_series(s: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(s):
        return s.fillna(False).astype(bool)
    numeric = pd.to_numeric(s, errors="coerce")
    if numeric.notna().all():
        return numeric.ne(0)
    return s.fillna("").astype(str).str.strip().str.lower().isin({"true", "1", "yes"})

def load_index(base: Path, expected: dict) -> pd.DataFrame:
    path = base / ANALYSIS / "population_index_local.csv"
    d = pd.read_csv(path, low_memory=False)
    required = {
        "case_id", "subject_id", "hadm_id", "icustay_id", "label", "has_note",
        "landmark_time", "note_time", "category", "note_age_at_landmark_hours",
        "dbsource", "direct_outcome_language_present",
    }
    missing = required - set(d.columns)
    if missing:
        raise RuntimeError(f"Broad ventilation population index missing columns {sorted(missing)}")
    for col in ["subject_id", "hadm_id", "icustay_id", "label"]:
        d[col] = pd.to_numeric(d[col], errors="raise").astype("int64")
    d["case_id"] = d["case_id"].astype(str)
    d["has_note"] = bool_series(d["has_note"])
    d["dbsource"] = d["dbsource"].fillna("unknown").astype(str).str.strip().str.lower()
    d["landmark_time"] = pd.to_datetime(d["landmark_time"], errors="raise")
    d["note_time"] = pd.to_datetime(d["note_time"], errors="coerce")
    if not d["dbsource"].eq(SOURCE).all():
        raise RuntimeError("Broad ventilation sensitivity contains a non-MetaVision row")
    observed = {
        "rows": int(len(d)),
        "unique_patients": int(d["subject_id"].nunique()),
        "cases": int(d["label"].sum()),
        "controls": int(len(d) - d["label"].sum()),
        "note_available_rows": int(d["has_note"].sum()),
    }
    for key, value in observed.items():
        if int(expected[key]) != int(value):
            raise RuntimeError(f"Broad ventilation contract mismatch {key}: {value} != {expected[key]}")
    if d["case_id"].duplicated().any() or d["icustay_id"].duplicated().any():
        raise RuntimeError("Broad ventilation population contains duplicate analysis rows")
    return d.reset_index(drop=True)

def main() -> None:
    ap = argparse.ArgumentParser(description="Prepare/freeze registered H6 broad respiratory-support ventilation sensitivity inputs without predictive performance.")
    ap.add_argument("--root", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--contract", required=True)
    ap.add_argument("--context-freeze", required=True)
    ap.add_argument("--strip-freeze", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    root = structured_mod.resolve_root(args.root)
    base = Path(args.base).expanduser().resolve()
    contract_path = Path(args.contract).expanduser().resolve()
    expected = json.loads(contract_path.read_text(encoding="utf-8"))
    context_freeze_path = Path(args.context_freeze).expanduser().resolve()
    context_freeze = json.loads(context_freeze_path.read_text(encoding="utf-8"))
    strip_freeze_path = Path(args.strip_freeze).expanduser().resolve()
    strip_freeze = json.loads(strip_freeze_path.read_text(encoding="utf-8"))
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    analysis_dir = base / ANALYSIS
    index_path = analysis_dir / "population_index_local.csv"
    idx = load_index(base, expected)

    update_progress(current=1, total=6, phase="broad_endpoint_prepare", message="Building frozen 34-feature structured block for broad endpoint", unit="stage")
    unique = idx[["subject_id", "hadm_id", "icustay_id", "landmark_time"]].drop_duplicates("icustay_id").copy()
    demographics, demographic_report = structured_mod.load_demographics(root, unique)
    char_data, char_report = structured_mod.scan_chartevents(root, unique)
    lab_data, lab_report = structured_mod.scan_labevents(root, unique)
    urine, urine_report = structured_mod.scan_urine(root, unique)
    feat = structured_mod.aggregate_features(unique, demographics, char_data, lab_data, urine)
    feature_cols = [c for c in feat.columns if c != "icustay_id"]
    if len(feature_cols) != 34:
        raise RuntimeError(f"Broad ventilation expected 34 structured features, found {len(feature_cols)}")
    structured = idx[["case_id", "subject_id", "icustay_id", "label", "has_note"]].merge(
        feat, on="icustay_id", how="left", validate="one_to_one"
    )
    structured_path = analysis_dir / "enhanced_structured_features_v2_1_local.csv"
    structured.to_csv(structured_path, index=False)

    update_progress(current=2, total=6, phase="broad_endpoint_prepare", message="Building frozen treatment/documentation/note-context block", unit="stage")
    stays = idx[["subject_id", "hadm_id", "icustay_id", "landmark_time", "dbsource"]].drop_duplicates("icustay_id").copy()
    doc, doc_report = context_mod.build_note_behavior(root, stays)
    doc = doc.drop(columns=context_freeze["documentation_behavior"]["excluded_features"], errors="ignore")
    chart, chart_report = context_mod.build_chartevent_context(root, stays, context_freeze)
    inputs = context_mod.build_inputevent_context(root, stays, context_freeze)
    common = chart.merge(inputs.drop(columns=["dbsource"]), on="icustay_id", how="left", validate="one_to_one")
    common = common.merge(doc, on="icustay_id", how="left", validate="one_to_one")

    d = idx.copy()
    d["category_group"] = d["category"].map(context_mod.collapse_note_category)
    feature_context = [
        "has_note", "note_age_at_landmark_hours", "category_group",
        *context_freeze["documentation_behavior"]["features"],
        "treat_fio2_last_6h", "treat_oxygen_flow_last_6h",
        "treat_high_flow_any_6h", "treat_niv_any_6h",
        "treat_vasoactive_any", "treat_vasoactive_agent_count",
        "treat_sedative_any", "treat_sedative_agent_count",
    ]
    context = d[["case_id", "subject_id", "icustay_id", "has_note", "note_age_at_landmark_hours", "category_group"]].merge(
        common.drop(columns=["dbsource"]), on="icustay_id", how="left", validate="one_to_one"
    )
    missing_context = [c for c in feature_context if c not in context.columns]
    if missing_context:
        raise RuntimeError(f"Broad ventilation missing context features {missing_context}")
    context = context[["case_id", "subject_id", "icustay_id", *feature_context]].copy()
    context_path = analysis_dir / "preregistration_context_features_v2_1_local.csv"
    context.to_csv(context_path, index=False)

    update_progress(current=3, total=6, phase="broad_endpoint_prepare", message="Freezing deterministic patient-grouped five-repeat splits", unit="stage")
    split_frame = split_mod.expected_split_frame(structured, ANALYSIS)
    split_path = analysis_dir / "enhanced_structured_cv_splits_v2_1_local.csv"
    split_status = "created"
    if split_path.exists():
        existing = pd.read_csv(split_path, low_memory=False)
        split_mod.validate_existing(existing, split_frame, ANALYSIS)
        split_status = "reused_identical_existing"
    else:
        split_frame.to_csv(split_path, index=False)
    split_sha = sha256_file(split_path)

    update_progress(current=4, total=6, phase="broad_endpoint_prepare", message="Freezing broad-endpoint note identity and stripped corpus", unit="stage")
    idx_hash_frame = notes_mod.prepare_index_for_frozen_context_hash(idx)
    note_identity_sha = notes_mod.note_identity_hash(idx_hash_frame)
    selected = idx[idx["has_note"]].copy()
    selected_ids = set(selected["case_id"].astype(str))
    source_cases = analysis_dir / "cases.jsonl"
    records = {}
    with source_cases.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            rec = json.loads(line)
            cid = str(rec.get("case_id"))
            if cid in selected_ids:
                if cid in records:
                    raise RuntimeError(f"Duplicate broad ventilation case_id in cases.jsonl: {cid}")
                records[cid] = rec
    if set(records) != selected_ids:
        raise RuntimeError(
            f"Broad ventilation selected-note record mismatch: missing={len(selected_ids-set(records))} extra={len(set(records)-selected_ids)}"
        )

    replacement = str(strip_freeze["replacement"])
    rx = notes_mod.compile_outcome_regex(strip_freeze["patterns"][BASE_OUTCOME])
    full_path = analysis_dir / "fixed_notes_full_v2_1_local.jsonl"
    stripped_path = analysis_dir / "fixed_notes_stripped_v2_1_local.jsonl"
    notes_changed = total_matches = chars_before = chars_after = 0
    with full_path.open("w", encoding="utf-8") as full_handle, stripped_path.open("w", encoding="utf-8") as strip_handle:
        for cid in sorted(selected_ids):
            rec = records[cid]
            text = str(rec["model_state"]["clinical_note"])
            stripped, match_count = notes_mod.strip_text(text, rx, replacement)
            full_rec = copy.deepcopy(rec)
            full_rec.setdefault("metadata", {})["corpus_variant"] = "full_unstripped"
            full_rec["metadata"]["source_system_analysis"] = SOURCE
            full_rec["metadata"]["registered_analysis"] = ANALYSIS
            stripped_rec = copy.deepcopy(rec)
            stripped_rec["model_state"]["clinical_note"] = stripped
            stripped_rec.setdefault("metadata", {})["corpus_variant"] = "language_stripped"
            stripped_rec["metadata"]["source_system_analysis"] = SOURCE
            stripped_rec["metadata"]["registered_analysis"] = ANALYSIS
            stripped_rec["metadata"]["outcome_language_match_count"] = int(match_count)
            full_handle.write(json.dumps(full_rec, ensure_ascii=False) + "\n")
            strip_handle.write(json.dumps(stripped_rec, ensure_ascii=False) + "\n")
            notes_changed += int(match_count > 0)
            total_matches += int(match_count)
            chars_before += len(text)
            chars_after += len(stripped)

    update_progress(current=5, total=6, phase="broad_endpoint_prepare", message="Checking broad-endpoint frozen input counts and hashes", unit="stage")
    if len(selected_ids) != int(expected["note_available_rows"]):
        raise RuntimeError("Broad ventilation stripped corpus count differs from frozen contract")
    case_note_rows = int(selected["label"].eq(1).sum())
    control_note_rows = int(selected["label"].eq(0).sum())
    if case_note_rows != int(expected["case_note_rows"]) or control_note_rows != int(expected["control_note_rows"]):
        raise RuntimeError("Broad ventilation case/control note counts differ from frozen contract")

    report = {
        "analysis": "Registered v2.1 H6 broad respiratory-support ventilation endpoint input preparation",
        "status": "completed",
        "registration_id": "ahxn9",
        "doi": "10.17605/OSF.IO/AHXN9",
        "analysis_name": ANALYSIS,
        "base_outcome": BASE_OUTCOME,
        "source": SOURCE,
        "predictive_performance_computed": False,
        "semantic_inference_run": False,
        "contains_note_text": False,
        "contains_patient_identifiers": False,
        "contains_row_level_data": False,
        "counts": {
            "rows": int(len(idx)),
            "unique_patients": int(idx["subject_id"].nunique()),
            "cases": int(idx["label"].sum()),
            "controls": int(len(idx) - idx["label"].sum()),
            "note_available_rows": int(idx["has_note"].sum()),
            "case_note_rows": case_note_rows,
            "control_note_rows": control_note_rows,
        },
        "structured": {
            "feature_count": int(len(feature_cols)),
            "local_file_sha256": sha256_file(structured_path),
            "demographic_report": demographic_report,
            "chartevent_report": char_report,
            "labevent_report": lab_report,
            "urine_report": urine_report,
        },
        "context": {
            "local_file_sha256": sha256_file(context_path),
            "note_behavior_scan": doc_report,
            "chartevent_cleaning": chart_report,
        },
        "splits": {
            "repeat_seeds": [int(x) for x in split_mod.REPEAT_SEEDS],
            "folds_per_repeat": int(split_mod.FOLDS),
            "group": "source_patient",
            "status": split_status,
            "split_sha256": split_sha,
        },
        "notes": {
            "note_identity_sha256": note_identity_sha,
            "full_local_file_sha256": sha256_file(full_path),
            "stripped_local_file_sha256": sha256_file(stripped_path),
            "notes_changed_by_registered_stripping": int(notes_changed),
            "total_regex_matches": int(total_matches),
            "characters_before": int(chars_before),
            "characters_after": int(chars_after),
            "pattern_count": int(len(strip_freeze["patterns"][BASE_OUTCOME])),
        },
        "hashes": {
            "population_index_sha256": sha256_file(index_path),
            "broad_contract_sha256": sha256_file(contract_path),
            "context_freeze_sha256": sha256_file(context_freeze_path),
            "language_stripping_freeze_sha256": sha256_file(strip_freeze_path),
        },
        "guardrails": [
            "No semantic, lexical, or clinical prediction model was fit or scored.",
            "The broad endpoint cohort was frozen before this task and is not modified here.",
            "Structured/context extraction reuses the registered v2.1 functions and feature definitions.",
            "Patient-grouped splits use the registered five seeds before any broad-endpoint performance is opened.",
            "Note identity is fixed before registered ventilation-language stripping.",
            "Row-level features, note text, split assignments, and corpora remain local.",
        ],
    }
    update_progress(current=6, total=6, phase="done", message="Completed H6 broad ventilation input preparation", unit="stage")
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
