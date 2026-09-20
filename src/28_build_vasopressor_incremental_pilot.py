from __future__ import annotations

import argparse
import json
import math
import random
import re
from pathlib import Path

import numpy as np
import pandas as pd

from common import find_file, lower_columns, module_path, parse_datetime, read_columns, resolve_root
from semantic_schema import SEMANTIC_CONSTRUCTS


CANONICAL_VASO_CV = {
    30043, 30044, 30046, 30047, 30051, 30119, 30120,
    30125, 30127, 30128, 30307, 30309,
}
CANONICAL_VASO_MV = {221289, 221662, 221749, 221906, 222315, 227692}

BEDSIDE_CATEGORIES = {
    "Physician", "Consult", "Nursing", "Nursing/other", "Respiratory", "General",
}

PRESSOR_PATTERNS = [
    re.compile(p, flags=re.IGNORECASE)
    for p in [
        r"\bvasopressor(?:s)?\b",
        r"\bpressor(?:s)?\b",
        r"\bnorepinephrine\b",
        r"\blevophed\b",
        r"\bphenylephrine\b",
        r"\bneo[- ]?synephrine\b",
        r"\bvasopressin\b",
        r"\bdopamine\b",
        r"\bepinephrine\b",
        r"\badrenaline\b",
        r"\bvasoactive\b",
    ]
]

VITAL_ITEMIDS = {
    "heart_rate": {211, 220045},
    "map": {52, 456, 6702, 443, 220052, 220181, 225312},
    "resp_rate": {615, 618, 220210, 224690},
    "spo2": {646, 220277},
}

LAB_ITEMIDS = {
    "lactate": {50813},
    "creatinine": {50912},
    "wbc": {51301},
}


def has_explicit_pressor_term(text: str) -> bool:
    return any(p.search(text) for p in PRESSOR_PATTERNS)


def first_vasopressor_events(root: Path) -> pd.DataFrame:
    pieces = []

    mv = find_file(module_path(root, "mimiciii"), ["INPUTEVENTS_MV.csv.gz", "INPUTEVENTS_MV.csv"])
    if mv is not None:
        for chunk in read_columns(
            mv,
            ["hadm_id", "itemid", "starttime", "statusdescription"],
            chunksize=250_000,
        ):
            c = lower_columns(chunk)
            c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
            c = c[c["itemid"].isin(CANONICAL_VASO_MV)]
            if c.empty:
                continue
            if "statusdescription" in c:
                bad = c["statusdescription"].fillna("").astype(str).str.lower().str.contains(
                    "rewritten|cancelled"
                )
                c = c[~bad]
            c["hadm_id"] = pd.to_numeric(c["hadm_id"], errors="coerce")
            c["event_time"] = parse_datetime(c["starttime"])
            c = c.dropna(subset=["hadm_id", "event_time"])
            pieces.append(c[["hadm_id", "event_time"]])

    cv = find_file(module_path(root, "mimiciii"), ["INPUTEVENTS_CV.csv.gz", "INPUTEVENTS_CV.csv"])
    if cv is not None:
        for chunk in read_columns(
            cv,
            ["hadm_id", "itemid", "charttime"],
            chunksize=250_000,
        ):
            c = lower_columns(chunk)
            c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
            c = c[c["itemid"].isin(CANONICAL_VASO_CV)]
            if c.empty:
                continue
            c["hadm_id"] = pd.to_numeric(c["hadm_id"], errors="coerce")
            c["event_time"] = parse_datetime(c["charttime"])
            c = c.dropna(subset=["hadm_id", "event_time"])
            pieces.append(c[["hadm_id", "event_time"]])

    if not pieces:
        raise RuntimeError("No canonical vasopressor events found.")

    d = pd.concat(pieces, ignore_index=True)
    d["hadm_id"] = d["hadm_id"].astype("int64")
    return d.sort_values("event_time").groupby("hadm_id", as_index=False).first()


def load_icustays(root: Path) -> pd.DataFrame:
    f = find_file(module_path(root, "mimiciii"), ["ICUSTAYS.csv.gz", "ICUSTAYS.csv"])
    if f is None:
        raise FileNotFoundError("ICUSTAYS not found.")
    d = lower_columns(pd.read_csv(
        f,
        usecols=lambda c: c.lower() in {"hadm_id", "icustay_id", "dbsource", "intime", "outtime"},
        low_memory=False,
    ))
    d["hadm_id"] = pd.to_numeric(d["hadm_id"], errors="coerce")
    d["icustay_id"] = pd.to_numeric(d["icustay_id"], errors="coerce")
    d["intime"] = parse_datetime(d["intime"])
    d["outtime"] = parse_datetime(d["outtime"])
    return d.dropna(subset=["hadm_id", "icustay_id", "intime", "outtime"]).copy()


def load_bedside_notes(root: Path, hadm_filter: set[int] | None = None) -> pd.DataFrame:
    f = find_file(module_path(root, "mimiciii"), ["NOTEEVENTS.csv.gz", "NOTEEVENTS.csv"])
    if f is None:
        raise FileNotFoundError("NOTEEVENTS not found.")

    pieces = []
    for chunk in read_columns(
        f,
        ["hadm_id", "charttime", "category", "iserror", "text"],
        chunksize=100_000,
    ):
        c = lower_columns(chunk)
        c["hadm_id"] = pd.to_numeric(c["hadm_id"], errors="coerce")
        c = c.dropna(subset=["hadm_id"])
        c["hadm_id"] = c["hadm_id"].astype("int64")
        if hadm_filter is not None:
            c = c[c["hadm_id"].isin(hadm_filter)]
        if c.empty:
            continue
        if "iserror" in c:
            c = c[c["iserror"].fillna(0).astype(str) != "1"]
        c["category"] = c["category"].fillna("UNKNOWN").astype(str)
        c = c[c["category"].isin(BEDSIDE_CATEGORIES)]
        if c.empty:
            continue
        c["note_time"] = parse_datetime(c["charttime"])
        c = c.dropna(subset=["note_time", "text"])
        c = c[~c["text"].astype(str).map(has_explicit_pressor_term)]
        if not c.empty:
            pieces.append(c[["hadm_id", "note_time", "category", "text"]])

    if not pieces:
        raise RuntimeError("No eligible bedside notes found.")
    return pd.concat(pieces, ignore_index=True)


def assign_icu(notes: pd.DataFrame, icu: pd.DataFrame) -> pd.DataFrame:
    merged = notes.merge(icu, on="hadm_id", how="inner")
    merged = merged[
        (merged["note_time"] >= merged["intime"])
        & (merged["note_time"] <= merged["outtime"])
    ].copy()
    merged["hours_since_icu"] = (
        merged["note_time"] - merged["intime"]
    ).dt.total_seconds() / 3600.0
    merged["elapsed_bin_6h"] = (merged["hours_since_icu"] // 6).astype(int)
    return merged


def extract_physio(
    root: Path,
    snapshots: pd.DataFrame,
    vital_lookback_h: float,
    lab_lookback_h: float,
) -> pd.DataFrame:
    snaps = snapshots[
        ["case_id", "hadm_id", "icustay_id", "note_time"]
    ].copy()

    vital_rows = []
    chart_file = find_file(module_path(root, "mimiciii"), ["CHARTEVENTS.csv.gz", "CHARTEVENTS.csv"])
    all_vital_ids = set().union(*VITAL_ITEMIDS.values())
    if chart_file is not None:
        relevant_hadm = set(snaps["hadm_id"].astype(int))
        for chunk in read_columns(
            chart_file,
            ["hadm_id", "icustay_id", "itemid", "charttime", "valuenum", "error"],
            chunksize=500_000,
        ):
            c = lower_columns(chunk)
            c["hadm_id"] = pd.to_numeric(c["hadm_id"], errors="coerce")
            c = c[c["hadm_id"].isin(relevant_hadm)]
            if c.empty:
                continue
            c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
            c = c[c["itemid"].isin(all_vital_ids)]
            if "error" in c:
                c = c[c["error"].fillna(0).astype(str) != "1"]
            c["charttime"] = parse_datetime(c["charttime"])
            c["valuenum"] = pd.to_numeric(c["valuenum"], errors="coerce")
            c = c.dropna(subset=["hadm_id", "charttime", "valuenum"])
            if not c.empty:
                vital_rows.append(c[["hadm_id", "icustay_id", "itemid", "charttime", "valuenum"]])

    vitals = pd.concat(vital_rows, ignore_index=True) if vital_rows else pd.DataFrame()

    lab_rows = []
    lab_file = find_file(module_path(root, "mimiciii"), ["LABEVENTS.csv.gz", "LABEVENTS.csv"])
    all_lab_ids = set().union(*LAB_ITEMIDS.values())
    if lab_file is not None:
        relevant_hadm = set(snaps["hadm_id"].astype(int))
        for chunk in read_columns(
            lab_file,
            ["hadm_id", "itemid", "charttime", "valuenum"],
            chunksize=500_000,
        ):
            c = lower_columns(chunk)
            c["hadm_id"] = pd.to_numeric(c["hadm_id"], errors="coerce")
            c = c[c["hadm_id"].isin(relevant_hadm)]
            if c.empty:
                continue
            c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
            c = c[c["itemid"].isin(all_lab_ids)]
            c["charttime"] = parse_datetime(c["charttime"])
            c["valuenum"] = pd.to_numeric(c["valuenum"], errors="coerce")
            c = c.dropna(subset=["hadm_id", "charttime", "valuenum"])
            if not c.empty:
                lab_rows.append(c[["hadm_id", "itemid", "charttime", "valuenum"]])

    labs = pd.concat(lab_rows, ignore_index=True) if lab_rows else pd.DataFrame()

    rows = []
    for s in snaps.itertuples(index=False):
        row = {"case_id": s.case_id}
        if not vitals.empty:
            vg = vitals[
                (vitals["hadm_id"] == s.hadm_id)
                & (vitals["charttime"] <= s.note_time)
                & (vitals["charttime"] >= s.note_time - pd.to_timedelta(vital_lookback_h, unit="h"))
            ].copy()
            for name, ids in VITAL_ITEMIDS.items():
                x = vg[vg["itemid"].isin(ids)].sort_values("charttime")
                if x.empty:
                    row[f"{name}_last"] = np.nan
                    row[f"{name}_delta"] = np.nan
                else:
                    row[f"{name}_last"] = float(x.iloc[-1]["valuenum"])
                    row[f"{name}_delta"] = (
                        float(x.iloc[-1]["valuenum"] - x.iloc[0]["valuenum"])
                        if len(x) >= 2 else np.nan
                    )
        else:
            for name in VITAL_ITEMIDS:
                row[f"{name}_last"] = np.nan
                row[f"{name}_delta"] = np.nan

        if not labs.empty:
            lg = labs[
                (labs["hadm_id"] == s.hadm_id)
                & (labs["charttime"] <= s.note_time)
                & (labs["charttime"] >= s.note_time - pd.to_timedelta(lab_lookback_h, unit="h"))
            ].copy()
            for name, ids in LAB_ITEMIDS.items():
                x = lg[lg["itemid"].isin(ids)].sort_values("charttime")
                row[f"{name}_last"] = float(x.iloc[-1]["valuenum"]) if not x.empty else np.nan
        else:
            for name in LAB_ITEMIDS:
                row[f"{name}_last"] = np.nan

        rows.append(row)

    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Build a local-only vasopressor case/control snapshot dataset for testing "
            "incremental semantic information beyond structured physiology."
        )
    )
    ap.add_argument("--root", required=True)
    ap.add_argument("--cases-output", required=True)
    ap.add_argument("--features-output", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--controls-per-case", type=int, default=3)
    ap.add_argument("--seed", type=int, default=20260920)
    ap.add_argument("--vital-lookback-hours", type=float, default=6.0)
    ap.add_argument("--lab-lookback-hours", type=float, default=24.0)
    args = ap.parse_args()

    root = resolve_root(args.root)
    rng = random.Random(args.seed)

    events = first_vasopressor_events(root)
    event_hadms = set(events["hadm_id"].astype(int))
    icu = load_icustays(root)

    # Load all bedside notes once; explicit pressor-term notes are removed for both groups.
    notes = load_bedside_notes(root)
    note_icu = assign_icu(notes, icu)

    # Cases: closest eligible note in the 0-6h window before first vasopressor.
    case_pool = note_icu.merge(events, on="hadm_id", how="inner")
    case_pool["hours_before_event"] = (
        case_pool["event_time"] - case_pool["note_time"]
    ).dt.total_seconds() / 3600.0
    case_pool = case_pool[
        (case_pool["hours_before_event"] > 0)
        & (case_pool["hours_before_event"] <= 6)
        & (case_pool["event_time"] >= case_pool["intime"])
        & (case_pool["event_time"] <= case_pool["outtime"])
    ].copy()
    case_pool = (
        case_pool.sort_values("hours_before_event")
        .groupby("hadm_id", as_index=False)
        .first()
    )

    # Controls: ICU admissions with no canonical vasopressor during the admission.
    control_pool = note_icu[~note_icu["hadm_id"].isin(event_hadms)].copy()
    control_pool = (
        control_pool.sort_values("note_time")
        .groupby(["hadm_id", "elapsed_bin_6h", "category"], as_index=False)
        .first()
    )

    used_control_hadms: set[int] = set()
    selected_controls = []
    matched_cases = []

    for case in case_pool.sort_values(["dbsource", "category", "hours_since_icu", "hadm_id"]).itertuples(index=False):
        available = control_pool[~control_pool["hadm_id"].isin(used_control_hadms)].copy()
        if available.empty:
            break

        available["elapsed_distance"] = (available["hours_since_icu"] - case.hours_since_icu).abs()
        priority = pd.Series(3, index=available.index, dtype=int)
        same_db = available["dbsource"].astype(str) == str(case.dbsource)
        same_cat = available["category"].astype(str) == str(case.category)
        close6 = available["elapsed_distance"] <= 6
        close12 = available["elapsed_distance"] <= 12
        priority.loc[same_db & same_cat & close6] = 0
        priority.loc[same_db & same_cat & close12 & (priority > 0)] = 1
        priority.loc[same_db & close6 & (priority > 1)] = 2
        available["match_priority"] = priority
        available = available[same_db & (available["elapsed_distance"] <= 12)].copy()
        if available.empty:
            continue

        # Deterministic tie-breaking with seeded random jitter.
        available["jitter"] = [rng.random() for _ in range(len(available))]
        available = available.sort_values(
            ["match_priority", "elapsed_distance", "jitter", "hadm_id"]
        )
        take = available.drop_duplicates("hadm_id").head(args.controls_per_case)
        if len(take) < args.controls_per_case:
            continue

        matched_cases.append(case)
        selected_controls.append(take)
        used_control_hadms.update(take["hadm_id"].astype(int).tolist())

    if not matched_cases:
        raise RuntimeError("No fully matched vasopressor cases were found.")

    case_df = pd.DataFrame([x._asdict() for x in matched_cases])
    control_df = pd.concat(selected_controls, ignore_index=True)

    case_df["label"] = 1
    control_df["label"] = 0
    case_df["match_set"] = np.arange(1, len(case_df) + 1)
    control_df["match_set"] = np.repeat(
        np.arange(1, len(case_df) + 1),
        args.controls_per_case,
    )

    snapshots = pd.concat([case_df, control_df], ignore_index=True, sort=False)
    snapshots = snapshots.reset_index(drop=True)
    snapshots["case_id"] = [
        f"vasopilot_{'case' if y == 1 else 'control'}_{i:05d}"
        for i, y in enumerate(snapshots["label"].astype(int), start=1)
    ]

    phys = extract_physio(
        root,
        snapshots,
        vital_lookback_h=args.vital_lookback_hours,
        lab_lookback_h=args.lab_lookback_hours,
    )

    feature_cols = [
        "case_id", "label", "match_set", "category", "dbsource", "hours_since_icu"
    ]
    safe = snapshots[feature_cols].merge(phys, on="case_id", how="left")

    features_path = Path(args.features_output).expanduser().resolve()
    features_path.parent.mkdir(parents=True, exist_ok=True)
    safe.to_csv(features_path, index=False)

    # Local credentialed note cases for semantic inference. No source IDs exported.
    cases_path = Path(args.cases_output).expanduser().resolve()
    cases_path.parent.mkdir(parents=True, exist_ok=True)
    with cases_path.open("w", encoding="utf-8") as f:
        for row in snapshots.itertuples(index=False):
            rec = {
                "case_id": row.case_id,
                "synthetic_only": False,
                "local_only": True,
                "model_state": {"clinical_note": str(row.text)},
                "metadata": {
                    "analysis": "vasopressor_case_control_incremental",
                    "label": int(row.label),
                    "match_set": int(row.match_set),
                    "note_category": str(row.category),
                    "dbsource": str(row.dbsource),
                    "hours_since_icu": round(float(row.hours_since_icu), 3),
                    "note_characters": len(str(row.text)),
                },
                "questions": SEMANTIC_CONSTRUCTS,
                "gold": None,
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    manifest = {
        "local_only": True,
        "contains_credentialed_note_text_in_cases_output": True,
        "contains_source_patient_identifiers_in_exported_features": False,
        "endpoint": "first canonical vasopressor initiation",
        "case_definition": (
            "closest bedside note 0-6h before first vasopressor; explicit pressor terms excluded"
        ),
        "control_definition": (
            "matched ICU admission with no canonical vasopressor during admission; explicit pressor terms excluded"
        ),
        "matching": (
            "without replacement; same dbsource required; priority to same note category and ICU elapsed time within 6h, maximum 12h"
        ),
        "controls_per_case": args.controls_per_case,
        "matched_cases": int(len(case_df)),
        "matched_controls": int(len(control_df)),
        "total_snapshots": int(len(snapshots)),
        "vital_lookback_hours": args.vital_lookback_hours,
        "lab_lookback_hours": args.lab_lookback_hours,
        "structured_features": [
            c for c in safe.columns
            if c not in {"case_id", "label", "match_set", "category", "dbsource"}
        ],
        "warning": (
            "Pilot case-control analysis. Controls are admissions with no vasopressor during the admission, "
            "not a full time-varying risk-set sample. Use this to test incremental signal before scaling."
        ),
    }
    manifest_path = Path(args.manifest).expanduser().resolve()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
