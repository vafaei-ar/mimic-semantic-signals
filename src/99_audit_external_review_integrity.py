from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from runrelay_progress import update_progress


OUTCOMES = ("invasive_ventilation", "renal_replacement_therapy", "icu_death")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def safe_counts(series: pd.Series) -> dict[str, int]:
    vc = series.astype(str).value_counts(dropna=False)
    return {str(k): int(v) for k, v in vc.items()}


def note_language_audit(builder, mimic_root: Path, pop_base: Path) -> dict:
    icu = builder.load_icustays(mimic_root).copy()
    icu["icustay_id"] = pd.to_numeric(icu["icustay_id"], errors="coerce").astype(int)
    notes = builder.load_notes(mimic_root, set(icu["hadm_id"].astype(int)))
    note_icu = builder.assign_notes_to_icu(notes, icu)
    note_icu["icustay_id"] = pd.to_numeric(note_icu["icustay_id"], errors="coerce").astype(int)
    note_icu = note_icu[(note_icu["hours_since_icu"] >= 0) & (note_icu["hours_since_icu"] <= 12)].copy()

    out = {}
    for outcome in OUTCOMES:
        idx = pd.read_csv(pop_base / outcome / "population_index_local.csv", low_memory=False)
        idx["icustay_id"] = pd.to_numeric(idx["icustay_id"], errors="coerce").astype(int)
        idx["label"] = pd.to_numeric(idx["label"], errors="coerce").astype(int)

        rx = builder.compile_rx(builder.OUTCOME_SPECS[outcome]["language_patterns"])
        all_last = (
            note_icu.sort_values(["icustay_id", "note_time"])
            .groupby("icustay_id", as_index=False)
            .last()[["icustay_id", "note_time"]]
            .rename(columns={"note_time": "note_time_before_language_filter"})
        )
        clean = note_icu[
            ~note_icu["text"].fillna("").astype(str).str.contains(rx, regex=True, na=False)
        ].copy()
        clean_last = (
            clean.sort_values(["icustay_id", "note_time"])
            .groupby("icustay_id", as_index=False)
            .last()[["icustay_id", "note_time"]]
            .rename(columns={"note_time": "note_time_after_language_filter"})
        )
        a = idx[["icustay_id", "label", "dbsource"]].merge(all_last, on="icustay_id", how="left")
        a = a.merge(clean_last, on="icustay_id", how="left")
        a["before"] = a["note_time_before_language_filter"].notna()
        a["after"] = a["note_time_after_language_filter"].notna()
        a["lost"] = a["before"] & ~a["after"]
        a["shifted_older"] = (
            a["before"] & a["after"]
            & (pd.to_datetime(a["note_time_after_language_filter"]) < pd.to_datetime(a["note_time_before_language_filter"]))
        )

        by_label = {}
        for label in (0, 1):
            q = a[a["label"] == label]
            by_label[str(label)] = {
                "n": int(len(q)),
                "before_language_filter_note_n": int(q["before"].sum()),
                "after_language_filter_note_n": int(q["after"].sum()),
                "before_language_filter_note_fraction": float(q["before"].mean()) if len(q) else None,
                "after_language_filter_note_fraction": float(q["after"].mean()) if len(q) else None,
                "lost_all_eligible_notes_n": int(q["lost"].sum()),
                "shifted_to_older_note_n": int(q["shifted_older"].sum()),
            }

        db = (
            idx.groupby(["dbsource", "label"])
            .size()
            .rename("n")
            .reset_index()
            .sort_values(["dbsource", "label"])
        )
        by_dbsource = [
            {"dbsource": str(r.dbsource), "label": int(r.label), "n": int(r.n)}
            for r in db.itertuples(index=False)
        ]

        cases = idx[idx["label"] == 1].copy()
        if {"outtime", "horizon_end"}.issubset(cases.columns):
            cases["outtime"] = pd.to_datetime(cases["outtime"], errors="coerce")
            cases["horizon_end"] = pd.to_datetime(cases["horizon_end"], errors="coerce")
            incomplete_after_event = int((cases["outtime"] < cases["horizon_end"]).sum())
        else:
            incomplete_after_event = None

        out[outcome] = {
            "label_by_dbsource": by_dbsource,
            "language_filter_note_availability_by_label": by_label,
            "cases_discharged_before_horizon_end_n": incomplete_after_event,
        }
    return out


def noteevents_hygiene(builder, mimic_root: Path) -> dict:
    f = builder.find_file(builder.module_path(mimic_root, "mimiciii"), ["NOTEEVENTS.csv.gz", "NOTEEVENTS.csv"])
    if f is None:
        raise FileNotFoundError("NOTEEVENTS not found")
    category_counts = Counter()
    whitespace_counts = Counter()
    iserror_counts = Counter()
    current_filter_misses = 0
    numeric_error_rows = 0
    total = 0
    for chunk in pd.read_csv(
        f,
        usecols=lambda c: c.lower() in {"category", "iserror"},
        chunksize=250_000,
        low_memory=False,
    ):
        total += len(chunk)
        cat = chunk["CATEGORY"] if "CATEGORY" in chunk else chunk["category"]
        for val, n in cat.fillna("NA").astype(str).value_counts().items():
            category_counts[str(val)] += int(n)
            if str(val) != str(val).strip():
                whitespace_counts[str(val)] += int(n)

        ierr = chunk["ISERROR"] if "ISERROR" in chunk else chunk["iserror"]
        for val, n in ierr.dropna().astype(str).value_counts().items():
            iserror_counts[str(val)] += int(n)
        num = pd.to_numeric(ierr, errors="coerce").fillna(0)
        numeric_bad = num.ne(0)
        current_kept = ierr.fillna(0).astype(str).ne("1")
        numeric_error_rows += int(numeric_bad.sum())
        current_filter_misses += int((numeric_bad & current_kept).sum())

    keys = ["Physician", "Physician ", "Respiratory", "Respiratory "]
    return {
        "rows_scanned": int(total),
        "selected_exact_category_counts": {k: int(category_counts.get(k, 0)) for k in keys},
        "category_values_with_outer_whitespace": dict(whitespace_counts),
        "non_null_iserror_string_counts": dict(iserror_counts),
        "numeric_nonzero_iserror_rows": int(numeric_error_rows),
        "numeric_nonzero_iserror_rows_missed_by_current_string_rule": int(current_filter_misses),
    }


def scan_selected_note_shorthand(base: Path) -> dict:
    specs = {
        "vasopressor": (
            base / "vasopressor_incremental_v3_corrected" / "cases.jsonl",
            re.compile(r"\b(?:levo|neo|vaso|pitressin)\b", re.I),
        ),
        "invasive_ventilation": (
            base / "multitask_benchmark_v1" / "invasive_ventilation" / "cases.jsonl",
            re.compile(r"\b(?:vent|bipap)\b", re.I),
        ),
        "renal_replacement_therapy": (
            base / "multitask_benchmark_v1" / "renal_replacement_therapy" / "cases.jsonl",
            re.compile(r"\b(?:HD|trialysis)\b", re.I),
        ),
        "icu_death": (
            base / "multitask_benchmark_v1" / "icu_death" / "cases.jsonl",
            re.compile(r"\bpalliative\b", re.I),
        ),
    }
    out = {}
    for name, (path, rx) in specs.items():
        if not path.exists():
            out[name] = {"available": False}
            continue
        n = hits = 0
        by_label = Counter()
        hit_by_label = Counter()
        with path.open("r", encoding="utf-8") as h:
            for line in h:
                if not line.strip():
                    continue
                rec = json.loads(line)
                text = str(rec.get("model_state", {}).get("clinical_note", ""))
                label = str(rec.get("metadata", {}).get("label", "NA"))
                n += 1
                by_label[label] += 1
                if rx.search(text):
                    hits += 1
                    hit_by_label[label] += 1
        out[name] = {
            "available": True,
            "n": int(n),
            "shorthand_hit_n": int(hits),
            "shorthand_hit_fraction": float(hits / n) if n else None,
            "n_by_label": dict(by_label),
            "shorthand_hit_n_by_label": dict(hit_by_label),
        }
    return out


def semantic_file_audit(path: Path, coverage_tokens: int) -> dict:
    if not path.exists():
        return {"available": False}
    n = diff = trunc = 0
    absdiff = []
    for line in path.open("r", encoding="utf-8"):
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("status") != "ok":
            continue
        n += 1
        tok = rec.get("metadata", {}).get("note_tokens")
        if isinstance(tok, (int, float)) and float(tok) > coverage_tokens:
            trunc += 1
        answers = rec.get("response", {}).get("answers", {})
        for a in answers.values():
            if not isinstance(a, dict):
                continue
            stored = a.get("noul")
            vals = a.get("chunk_values")
            if isinstance(stored, (int, float)) and isinstance(vals, list) and vals:
                d = abs(float(stored) - float(np.mean(vals)))
                absdiff.append(d)
                if d > 1e-12:
                    diff += 1
    arr = np.asarray(absdiff, dtype=float)
    return {
        "available": True,
        "successful_notes": int(n),
        "notes_over_max_token_coverage_n": int(trunc),
        "notes_over_max_token_coverage_fraction": float(trunc / n) if n else None,
        "construct_values_compared": int(len(arr)),
        "stored_aggregate_differs_from_chunk_mean_n": int(diff),
        "stored_aggregate_differs_from_chunk_mean_fraction": float(diff / len(arr)) if len(arr) else None,
        "absolute_stored_minus_mean": {
            "median": float(np.quantile(arr, 0.5)) if len(arr) else None,
            "p95": float(np.quantile(arr, 0.95)) if len(arr) else None,
            "max": float(arr.max()) if len(arr) else None,
        },
    }


def semantic_aggregation_audit(local_base: Path) -> dict:
    out = {"multitask": {}, "population_unique_notes": {}}
    for outcome in OUTCOMES:
        d = local_base / "multitask_benchmark_v1" / outcome
        out["multitask"][outcome] = {
            "openjev": semantic_file_audit(d / "open_jev_raw.jsonl", 1480),
            "laya": semantic_file_audit(d / "laya_raw.jsonl", 4100),
        }
    p = local_base / "population_landmark12_v1" / "semantic_unique_notes_v1"
    out["population_unique_notes"] = {
        "openjev": semantic_file_audit(p / "open_jev_raw.jsonl", 1480),
        "laya": semantic_file_audit(p / "laya_raw.jsonl", 4100),
    }
    return out


def eicu_lab_window_audit(external_mod, eicu_root: Path, lookback_h: float = 24.0) -> dict:
    units = external_mod.load_eicu_units(eicu_root)
    events = external_mod.first_eicu_pressors(eicu_root)
    snaps, _ = external_mod.match_risksets(
        units,
        events,
        stay_col="patientunitstayid",
        person_col="person_key",
        site_col="hospitalid",
        horizon_h=6.0,
        controls_per_case=3,
        seed=20260921,
    )
    stays = set(snaps["patientunitstayid"].astype(int))
    anchor = snaps.set_index("patientunitstayid")["anchor_hour"].to_dict()
    aliases = {
        k: {external_mod.norm_text(x) for x in vals}
        for k, vals in external_mod.EICU_LAB_ALIASES.items()
    }
    lab = external_mod.find_one(eicu_root, "lab.csv.gz")
    intended = negative = excluded_only_by_clip = 0
    for chunk in pd.read_csv(
        lab,
        chunksize=500_000,
        usecols=["patientunitstayid", "labresultoffset", "labname", "labresult"],
        low_memory=False,
    ):
        chunk["patientunitstayid"] = pd.to_numeric(chunk["patientunitstayid"], errors="coerce")
        q = chunk[chunk["patientunitstayid"].isin(stays)].copy()
        if q.empty:
            continue
        q["relevant"] = q["labname"].map(
            lambda x: any(external_mod.norm_text(x) in vals for vals in aliases.values())
        )
        q = q[q["relevant"]].copy()
        if q.empty:
            continue
        q["hour"] = pd.to_numeric(q["labresultoffset"], errors="coerce") / 60.0
        q["anchor"] = q["patientunitstayid"].map(anchor)
        q["labresult_num"] = pd.to_numeric(q["labresult"], errors="coerce")
        q = q[q["hour"].notna() & q["anchor"].notna() & q["labresult_num"].notna()]
        within = (q["hour"] <= q["anchor"]) & (q["hour"] >= q["anchor"] - lookback_h)
        intended += int(within.sum())
        neg = within & q["hour"].lt(0)
        negative += int(neg.sum())
        excluded_only_by_clip += int(neg.sum())
    return {
        "selected_snapshots": int(len(snaps)),
        "intended_relevant_lab_rows_within_24h": int(intended),
        "negative_offset_rows_within_intended_24h": int(negative),
        "rows_excluded_only_by_zero_clip": int(excluded_only_by_clip),
        "fraction_of_intended_rows_excluded_by_zero_clip": float(excluded_only_by_clip / intended) if intended else None,
    }


def zigong_regex_audit(zigong_mod, root: Path) -> dict:
    nursing = zigong_mod.find_one(root, "dtNursingChart.csv")
    current = zigong_mod.LEAK_RX
    total = excluded = bronchus = generic_removal = 0
    for chunk in zigong_mod.iter_csv_robust(
        nursing,
        100_000,
        usecols=lambda c: c == "NURSING_DESC",
        low_memory=False,
    ):
        s = chunk["NURSING_DESC"].dropna().astype(str)
        total += int(len(s))
        m = s.str.contains(current, regex=True, na=False)
        excluded += int(m.sum())
        bronchus += int((m & s.str.contains("支气管", regex=False, na=False)).sum())
        airway_specific = s.str.contains(r"插管|气管插管|气切|呼吸机|机械通气|拔管|extubat|intubat|endotracheal|tracheost|ventilat", regex=True, case=False, na=False)
        generic_removal += int((m & s.str.contains("拔除", regex=False, na=False) & ~airway_specific).sum())
    return {
        "nursing_desc_rows_scanned": int(total),
        "current_regex_excluded_rows": int(excluded),
        "current_regex_matches_literal_ETT": bool(current.search("ETT")),
        "excluded_rows_containing_bronchus_term": int(bronchus),
        "excluded_by_generic_removal_without_specific_airway_term": int(generic_removal),
    }


def main():
    ap = argparse.ArgumentParser(description="Aggregate audit of external review integrity findings.")
    ap.add_argument("--mimic-root", required=True)
    ap.add_argument("--local-mimic-base", required=True)
    ap.add_argument("--eicu-root", required=True)
    ap.add_argument("--zigong-root", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    src = Path(__file__).resolve().parent
    builder = load_module(src / "54_build_multitask_benchmark.py", "audit_builder54")
    external_mod = load_module(src / "39_build_external_structured_risksets.py", "audit_external39")
    zigong_mod = load_module(src / "82_build_zigong_ventilation24_cohort.py", "audit_zigong82")

    mimic_root = builder.resolve_root(args.mimic_root)
    local_base = Path(args.local_mimic_base).expanduser().resolve()
    eicu_root = Path(args.eicu_root).expanduser().resolve()
    zigong_root = Path(args.zigong_root).expanduser().resolve()

    report = {
        "analysis": "External-review integrity audit v1",
        "protocol": "docs/external_review_integrity_audit_protocol_v1.md",
        "local_only": True,
        "contains_note_text": False,
        "contains_patient_identifiers": False,
        "contains_row_level_data": False,
    }

    update_progress(current=1, total=6, phase="population", message="Auditing population endpoint/source and language-filter behavior", unit="stage")
    report["population"] = note_language_audit(builder, mimic_root, local_base / "population_landmark12_v1")

    update_progress(current=2, total=6, phase="note_hygiene", message="Auditing MIMIC note category and error-field normalization", unit="stage")
    report["noteevents_hygiene"] = noteevents_hygiene(builder, mimic_root)

    update_progress(current=3, total=6, phase="leakage_shorthand", message="Auditing selected-note shorthand not covered by current screens", unit="stage")
    report["selected_note_shorthand"] = scan_selected_note_shorthand(local_base)

    update_progress(current=4, total=6, phase="semantic_aggregation", message="Auditing semantic aggregation mismatch and chunk coverage", unit="stage")
    report["semantic_aggregation"] = semantic_aggregation_audit(local_base)

    update_progress(current=5, total=6, phase="eicu_lab_window", message="Auditing eICU pre-admission lab-window clipping", unit="stage")
    report["eicu_lab_window"] = eicu_lab_window_audit(external_mod, eicu_root)

    update_progress(current=6, total=6, phase="zigong_regex", message="Auditing Zigong leakage regex breadth and ETT boundary", unit="stage")
    report["zigong_leakage_regex"] = zigong_regex_audit(zigong_mod, zigong_root)

    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
