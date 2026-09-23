from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path

import numpy as np
import pandas as pd

from common import find_file, lower_columns, module_path, parse_datetime, read_columns, resolve_root
from runrelay_progress import update_progress
from semantic_schema import SEMANTIC_CONSTRUCTS


BEDSIDE_CATEGORIES = {
    "Physician", "Consult", "Nursing", "Nursing/other", "Respiratory", "General",
}

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

VENT_PROCEDURE_IDS = {224385}
VENT_EXPLICIT_CHART_IDS = {418, 225306, 225585, 225588, 225590, 225592, 226431, 228069}
VENT_SUPPORT_IDS = {619, 683, 720, 223849, 224684, 224688}

RRT_PROCEDURE_IDS = {225441, 225802, 225803, 225805, 225809, 225955}
RRT_ACTIVE_CHART_IDS = {152, 226499, 227290}
RRT_STRICT_OUTPUT_IDS = {40386, 40624, 40690, 40745, 40881, 40910, 41527, 42524, 44843, 46394}

OUTCOME_SPECS = {
    "invasive_ventilation": {
        "horizon_hours": 12.0,
        "language_patterns": [
            r"\bintubat\w*\b",
            r"\bendotracheal\b",
            r"\bmechanical ventilat\w*\b",
            r"\bventilator\b",
            r"\bETT\b",
        ],
    },
    "renal_replacement_therapy": {
        "horizon_hours": 12.0,
        "language_patterns": [
            r"\bdialysis\b",
            r"\bhemodialysis\b",
            r"\bhaemodialysis\b",
            r"\bCVVH\w*\b",
            r"\bCRRT\b",
            r"\bhemofiltration\b",
            r"\bhaemofiltration\b",
            r"\brenal replacement\b",
        ],
    },
    "icu_death": {
        "horizon_hours": 12.0,
        "language_patterns": [
            r"\bdying\b",
            r"\bdeath\b",
            r"\bdeceased\b",
            r"\bcomfort care\b",
            r"\bcomfort measures\b",
            r"\bCMO\b",
            r"\bwithdraw\w* (?:care|support|treatment)\b",
            r"\bhospice\b",
            r"\bDNR\b",
            r"\bDNI\b",
            r"\bdo not resuscitate\b",
            r"\bdo not intubate\b",
            r"\bgoals? of care\b",
        ],
    },
}


def compile_rx(patterns: list[str]) -> re.Pattern:
    return re.compile("|".join(f"(?:{p})" for p in patterns), flags=re.IGNORECASE)


def qstats(x: pd.Series) -> dict:
    v = pd.to_numeric(x, errors="coerce").dropna()
    if v.empty:
        return {"n": 0}
    return {
        "n": int(len(v)),
        "min": float(v.min()),
        "p05": float(v.quantile(0.05)),
        "p25": float(v.quantile(0.25)),
        "median": float(v.median()),
        "p75": float(v.quantile(0.75)),
        "p95": float(v.quantile(0.95)),
        "max": float(v.max()),
    }


def load_icustays(root: Path) -> pd.DataFrame:
    f = find_file(module_path(root, "mimiciii"), ["ICUSTAYS.csv.gz", "ICUSTAYS.csv"])
    if f is None:
        raise FileNotFoundError("ICUSTAYS not found")
    d = lower_columns(pd.read_csv(
        f,
        usecols=lambda c: c.lower() in {
            "subject_id", "hadm_id", "icustay_id", "dbsource", "intime", "outtime"
        },
        low_memory=False,
    ))
    for c in ["subject_id", "hadm_id", "icustay_id"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["intime"] = parse_datetime(d["intime"])
    d["outtime"] = parse_datetime(d["outtime"])
    return d.dropna(subset=["subject_id", "hadm_id", "icustay_id", "intime", "outtime"]).copy()


def load_notes(root: Path, hadms: set[int]) -> pd.DataFrame:
    f = find_file(module_path(root, "mimiciii"), ["NOTEEVENTS.csv.gz", "NOTEEVENTS.csv"])
    if f is None:
        raise FileNotFoundError("NOTEEVENTS not found")

    pieces = []
    for chunk in read_columns(
        f,
        ["hadm_id", "charttime", "storetime", "category", "iserror", "text"],
        chunksize=100_000,
    ):
        c = lower_columns(chunk)
        c["hadm_id"] = pd.to_numeric(c["hadm_id"], errors="coerce")
        c = c[c["hadm_id"].isin(hadms)]
        if c.empty:
            continue
        if "iserror" in c:
            c = c[c["iserror"].fillna(0).astype(str) != "1"]
        c["category"] = c["category"].fillna("UNKNOWN").astype(str)
        c = c[c["category"].isin(BEDSIDE_CATEGORIES)]
        if c.empty:
            continue
        c["chart_time"] = parse_datetime(c["charttime"])
        c["store_time"] = parse_datetime(c["storetime"]) if "storetime" in c else pd.NaT
        c = c.dropna(subset=["hadm_id", "chart_time", "text"])
        c = c[c["text"].astype(str).str.strip().ne("")].copy()
        if c.empty:
            continue
        c["storetime_available"] = c["store_time"].notna()
        c["note_time"] = c["chart_time"]
        has_store = c["store_time"].notna()
        c.loc[has_store, "note_time"] = c.loc[
            has_store, ["chart_time", "store_time"]
        ].max(axis=1)
        c["documentation_delay_hours"] = (
            c["note_time"] - c["chart_time"]
        ).dt.total_seconds() / 3600.0
        pieces.append(c[[
            "hadm_id", "note_time", "chart_time", "store_time",
            "storetime_available", "documentation_delay_hours",
            "category", "text"
        ]])

    if not pieces:
        raise RuntimeError("No eligible bedside notes found")
    return pd.concat(pieces, ignore_index=True)


def assign_notes_to_icu(notes: pd.DataFrame, icu: pd.DataFrame) -> pd.DataFrame:
    m = notes.merge(icu, on="hadm_id", how="inner")
    m = m[(m["note_time"] >= m["intime"]) & (m["note_time"] <= m["outtime"])].copy()
    m["hours_since_icu"] = (m["note_time"] - m["intime"]).dt.total_seconds() / 3600.0
    m["elapsed_bin_6h"] = (m["hours_since_icu"] // 6).astype(int)
    return m


def scan_event_evidence(root: Path) -> pd.DataFrame:
    pieces = []

    chart_ids = VENT_EXPLICIT_CHART_IDS | VENT_SUPPORT_IDS | RRT_ACTIVE_CHART_IDS
    chart = find_file(module_path(root, "mimiciii"), ["CHARTEVENTS.csv.gz", "CHARTEVENTS.csv"])
    if chart is not None:
        for chunk in read_columns(
            chart,
            ["subject_id", "hadm_id", "icustay_id", "itemid", "charttime", "error"],
            chunksize=750_000,
        ):
            c = lower_columns(chunk)
            c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
            c = c[c["itemid"].isin(chart_ids)]
            if c.empty:
                continue
            if "error" in c:
                c = c[c["error"].fillna(0).astype(str) != "1"]
            for col in ["subject_id", "hadm_id", "icustay_id"]:
                c[col] = pd.to_numeric(c[col], errors="coerce")
            c["event_time"] = parse_datetime(c["charttime"])
            c = c.dropna(subset=["hadm_id", "event_time", "itemid"])
            for name, ids in [
                ("vent_explicit_chart", VENT_EXPLICIT_CHART_IDS),
                ("vent_support", VENT_SUPPORT_IDS),
                ("rrt_active_chart", RRT_ACTIVE_CHART_IDS),
            ]:
                x = c[c["itemid"].isin(ids)].copy()
                if not x.empty:
                    x["evidence"] = name
                    pieces.append(x[[
                        "subject_id", "hadm_id", "icustay_id", "event_time", "evidence"
                    ]])

    proc_ids = VENT_PROCEDURE_IDS | RRT_PROCEDURE_IDS
    proc = find_file(module_path(root, "mimiciii"), ["PROCEDUREEVENTS_MV.csv.gz", "PROCEDUREEVENTS_MV.csv"])
    if proc is not None:
        for chunk in read_columns(
            proc,
            ["subject_id", "hadm_id", "icustay_id", "itemid", "starttime", "statusdescription"],
            chunksize=300_000,
        ):
            c = lower_columns(chunk)
            c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
            c = c[c["itemid"].isin(proc_ids)]
            if c.empty:
                continue
            if "statusdescription" in c:
                bad = c["statusdescription"].fillna("").astype(str).str.lower().str.contains(
                    "rewritten|cancelled"
                )
                c = c[~bad]
            for col in ["subject_id", "hadm_id", "icustay_id"]:
                c[col] = pd.to_numeric(c[col], errors="coerce")
            c["event_time"] = parse_datetime(c["starttime"])
            c = c.dropna(subset=["hadm_id", "event_time", "itemid"])
            for name, ids in [
                ("vent_procedure", VENT_PROCEDURE_IDS),
                ("rrt_procedure", RRT_PROCEDURE_IDS),
            ]:
                x = c[c["itemid"].isin(ids)].copy()
                if not x.empty:
                    x["evidence"] = name
                    pieces.append(x[[
                        "subject_id", "hadm_id", "icustay_id", "event_time", "evidence"
                    ]])

    out = find_file(module_path(root, "mimiciii"), ["OUTPUTEVENTS.csv.gz", "OUTPUTEVENTS.csv"])
    if out is not None:
        for chunk in read_columns(
            out,
            ["subject_id", "hadm_id", "icustay_id", "itemid", "charttime", "iserror"],
            chunksize=500_000,
        ):
            c = lower_columns(chunk)
            c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
            c = c[c["itemid"].isin(RRT_STRICT_OUTPUT_IDS)]
            if c.empty:
                continue
            if "iserror" in c:
                c = c[c["iserror"].fillna(0).astype(str) != "1"]
            for col in ["subject_id", "hadm_id", "icustay_id"]:
                c[col] = pd.to_numeric(c[col], errors="coerce")
            c["event_time"] = parse_datetime(c["charttime"])
            c = c.dropna(subset=["hadm_id", "event_time"])
            c["evidence"] = "rrt_strict_output"
            pieces.append(c[[
                "subject_id", "hadm_id", "icustay_id", "event_time", "evidence"
            ]])

    if not pieces:
        raise RuntimeError("No endpoint evidence found")
    return pd.concat(pieces, ignore_index=True)


def assign_evidence_to_icu(events: pd.DataFrame, icu: pd.DataFrame) -> pd.DataFrame:
    m = events.merge(
        icu[["subject_id", "hadm_id", "icustay_id", "dbsource", "intime", "outtime"]],
        on="hadm_id",
        how="inner",
        suffixes=("_event", "_icu"),
    )
    m = m[(m["event_time"] >= m["intime"]) & (m["event_time"] <= m["outtime"])].copy()
    m["subject_id"] = pd.to_numeric(m["subject_id_icu"], errors="coerce")
    m["icustay_id"] = pd.to_numeric(m["icustay_id_icu"], errors="coerce")
    m["hours_since_icu"] = (m["event_time"] - m["intime"]).dt.total_seconds() / 3600.0
    return m


def build_incident_event_table(
    assigned: pd.DataFrame,
    endpoint_evidence: set[str],
    disqualifying_evidence: set[str],
    washout_h: float,
) -> tuple[pd.DataFrame, pd.Series, set[int]]:
    relevant = assigned[assigned["evidence"].isin(disqualifying_evidence)].copy()

    early = relevant[relevant["hours_since_icu"] < washout_h]
    prevalent_stays = set(pd.to_numeric(early["icustay_id"], errors="coerce").dropna().astype(int))

    endpoint = assigned[
        assigned["evidence"].isin(endpoint_evidence)
        & (assigned["hours_since_icu"] >= washout_h)
    ].copy()
    endpoint = endpoint[
        ~endpoint["icustay_id"].fillna(-1).astype(int).isin(prevalent_stays)
    ].copy()

    endpoint = (
        endpoint.sort_values("event_time")
        .groupby("icustay_id", as_index=False)
        .first()
    )
    endpoint = (
        endpoint.sort_values("event_time")
        .groupby("subject_id", as_index=False)
        .first()
    )

    first_disqual = (
        relevant.sort_values("event_time")
        .groupby("hadm_id", as_index=False)
        .first()
        .set_index("hadm_id")["event_time"]
    )
    return endpoint[[
        "subject_id", "hadm_id", "icustay_id", "dbsource", "intime", "outtime", "event_time"
    ]], first_disqual, prevalent_stays


def load_death_table(root: Path, icu: pd.DataFrame, washout_h: float) -> tuple[pd.DataFrame, pd.Series]:
    f = find_file(module_path(root, "mimiciii"), ["ADMISSIONS.csv.gz", "ADMISSIONS.csv"])
    if f is None:
        raise FileNotFoundError("ADMISSIONS not found")
    d = lower_columns(pd.read_csv(
        f,
        usecols=lambda c: c.lower() in {"subject_id", "hadm_id", "deathtime"},
        low_memory=False,
    ))
    d["subject_id"] = pd.to_numeric(d["subject_id"], errors="coerce")
    d["hadm_id"] = pd.to_numeric(d["hadm_id"], errors="coerce")
    d["event_time"] = parse_datetime(d["deathtime"])
    d = d.dropna(subset=["subject_id", "hadm_id", "event_time"]).copy()

    m = d.merge(
        icu[["subject_id", "hadm_id", "icustay_id", "dbsource", "intime", "outtime"]],
        on=["subject_id", "hadm_id"],
        how="inner",
    )
    m = m[(m["event_time"] >= m["intime"]) & (m["event_time"] <= m["outtime"])].copy()
    m["hours_since_icu"] = (m["event_time"] - m["intime"]).dt.total_seconds() / 3600.0
    m = m[m["hours_since_icu"] >= washout_h].copy()
    m = m.sort_values("event_time").groupby("subject_id", as_index=False).first()
    event_map = d.sort_values("event_time").groupby("hadm_id", as_index=False).first().set_index("hadm_id")["event_time"]
    return m[[
        "subject_id", "hadm_id", "icustay_id", "dbsource", "intime", "outtime", "event_time"
    ]], event_map


def match_outcome(
    outcome: str,
    note_icu: pd.DataFrame,
    case_events: pd.DataFrame,
    disqualifying_map: pd.Series,
    prevalent_stays: set[int],
    horizon: float,
    controls_per_case: int,
    rng: random.Random,
) -> pd.DataFrame:
    spec = OUTCOME_SPECS[outcome]
    rx = compile_rx(spec["language_patterns"])

    notes = note_icu[
        ~note_icu["text"].fillna("").astype(str).str.contains(rx, regex=True, na=False)
    ].copy()
    if prevalent_stays:
        notes = notes[
            ~notes["icustay_id"].fillna(-1).astype(int).isin(prevalent_stays)
        ].copy()

    case_pool = notes.merge(
        case_events[["subject_id", "hadm_id", "icustay_id", "event_time"]],
        on=["subject_id", "hadm_id", "icustay_id"],
        how="inner",
    )
    case_pool["hours_before_event"] = (
        case_pool["event_time"] - case_pool["note_time"]
    ).dt.total_seconds() / 3600.0
    case_pool = case_pool[
        (case_pool["hours_before_event"] > 0)
        & (case_pool["hours_before_event"] <= horizon)
    ].copy()
    case_pool = (
        case_pool.sort_values(["subject_id", "event_time", "hours_before_event"])
        .groupby("subject_id", as_index=False)
        .first()
    )
    case_subjects = set(case_pool["subject_id"].astype(int))

    control_pool = notes[
        ~notes["subject_id"].astype(int).isin(case_subjects)
    ].copy()
    control_pool["first_disqualifying_time"] = control_pool["hadm_id"].map(disqualifying_map)
    control_pool["horizon_end"] = control_pool["note_time"] + pd.to_timedelta(horizon, unit="h")
    control_pool = control_pool[
        (
            control_pool["first_disqualifying_time"].isna()
            | (control_pool["first_disqualifying_time"] > control_pool["horizon_end"])
        )
        & (control_pool["outtime"] >= control_pool["horizon_end"])
    ].copy()
    control_pool = (
        control_pool.sort_values("note_time")
        .groupby(["subject_id", "hadm_id", "elapsed_bin_6h", "category"], as_index=False)
        .first()
    )

    used_controls: set[int] = set()
    matched_cases = []
    selected_controls = []

    for case in case_pool.sort_values(
        ["dbsource", "category", "hours_since_icu", "subject_id"]
    ).itertuples(index=False):
        available = control_pool[
            ~control_pool["subject_id"].astype(int).isin(used_controls)
        ].copy()
        if available.empty:
            break
        available["elapsed_distance"] = (
            available["hours_since_icu"] - case.hours_since_icu
        ).abs()
        same_db = available["dbsource"].astype(str) == str(case.dbsource)
        same_cat = available["category"].astype(str) == str(case.category)
        priority = pd.Series(3, index=available.index, dtype=int)
        priority.loc[same_db & same_cat & (available["elapsed_distance"] <= 6)] = 0
        priority.loc[
            same_db & same_cat & (available["elapsed_distance"] <= 12) & (priority > 0)
        ] = 1
        priority.loc[
            same_db & (available["elapsed_distance"] <= 6) & (priority > 1)
        ] = 2
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
        used_controls.update(take["subject_id"].astype(int).tolist())

    if not matched_cases:
        raise RuntimeError(f"No fully matched cases for {outcome}")

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
    snapshots["outcome"] = outcome
    snapshots["case_id"] = [
        f"{outcome}_{'case' if y == 1 else 'control'}_{i:05d}"
        for i, y in enumerate(snapshots["label"].astype(int), start=1)
    ]
    subject_values = sorted(snapshots["subject_id"].astype(int).unique().tolist())
    smap = {sid: f"{outcome}_p{i:05d}" for i, sid in enumerate(subject_values, start=1)}
    snapshots["patient_group"] = snapshots["subject_id"].astype(int).map(smap)

    check = snapshots.groupby("match_set")["label"].agg(["size", "sum"])
    expected = controls_per_case + 1
    bad = check[(check["size"] != expected) | (check["sum"] != 1)]
    if not bad.empty:
        raise RuntimeError(f"Invalid matched sets for {outcome}: {len(bad)}")

    return snapshots


def extract_physio(root: Path, snapshots: pd.DataFrame, vital_h: float, lab_h: float) -> pd.DataFrame:
    snaps = snapshots[["case_id", "hadm_id", "icustay_id", "note_time"]].copy()
    hadms = set(snaps["hadm_id"].astype(int))

    vital_rows = []
    chart = find_file(module_path(root, "mimiciii"), ["CHARTEVENTS.csv.gz", "CHARTEVENTS.csv"])
    all_vital_ids = set().union(*VITAL_ITEMIDS.values())
    if chart is not None:
        for chunk in read_columns(
            chart,
            ["hadm_id", "icustay_id", "itemid", "charttime", "valuenum", "error"],
            chunksize=500_000,
        ):
            c = lower_columns(chunk)
            c["hadm_id"] = pd.to_numeric(c["hadm_id"], errors="coerce")
            c = c[c["hadm_id"].isin(hadms)]
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
    lab = find_file(module_path(root, "mimiciii"), ["LABEVENTS.csv.gz", "LABEVENTS.csv"])
    all_lab_ids = set().union(*LAB_ITEMIDS.values())
    if lab is not None:
        for chunk in read_columns(
            lab,
            ["hadm_id", "itemid", "charttime", "valuenum"],
            chunksize=500_000,
        ):
            c = lower_columns(chunk)
            c["hadm_id"] = pd.to_numeric(c["hadm_id"], errors="coerce")
            c = c[c["hadm_id"].isin(hadms)]
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
    total = len(snaps)
    for j, s in enumerate(snaps.itertuples(index=False), start=1):
        row = {"case_id": s.case_id}
        if not vitals.empty:
            vg = vitals[
                (vitals["hadm_id"] == s.hadm_id)
                & (pd.to_numeric(vitals["icustay_id"], errors="coerce") == int(s.icustay_id))
                & (vitals["charttime"] <= s.note_time)
                & (vitals["charttime"] >= s.note_time - pd.to_timedelta(vital_h, unit="h"))
            ]
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
                & (labs["charttime"] >= s.note_time - pd.to_timedelta(lab_h, unit="h"))
            ]
            for name, ids in LAB_ITEMIDS.items():
                x = lg[lg["itemid"].isin(ids)].sort_values("charttime")
                row[f"{name}_last"] = float(x.iloc[-1]["valuenum"]) if not x.empty else np.nan
        else:
            for name in LAB_ITEMIDS:
                row[f"{name}_last"] = np.nan
        rows.append(row)
        if j % 500 == 0 or j == total:
            update_progress(
                current=j,
                total=total,
                phase="structured_features",
                message=f"Extracted contemporaneous structured features for {j}/{total} snapshots",
                unit="snapshot",
            )
    return pd.DataFrame(rows)


def write_local_outputs(base: Path, snapshots: pd.DataFrame, features: pd.DataFrame) -> dict:
    outcome = str(snapshots["outcome"].iloc[0])
    outdir = base / outcome
    outdir.mkdir(parents=True, exist_ok=True)

    index_cols = [
        "case_id", "label", "match_set", "patient_group",
        "subject_id", "hadm_id", "icustay_id",
        "note_time", "event_time", "category", "dbsource",
        "hours_since_icu", "hours_before_event",
        "storetime_available", "documentation_delay_hours",
    ]
    idx = snapshots[[c for c in index_cols if c in snapshots.columns]].copy()
    idx.to_csv(outdir / "snapshot_index_local.csv", index=False)

    safe_cols = [
        "case_id", "label", "match_set", "patient_group",
        "category", "dbsource", "hours_since_icu",
    ]
    safe = snapshots[safe_cols].merge(features, on="case_id", how="left")
    safe.to_csv(outdir / "structured_features.csv", index=False)

    with (outdir / "cases.jsonl").open("w", encoding="utf-8") as f:
        for row in snapshots.itertuples(index=False):
            rec = {
                "case_id": row.case_id,
                "synthetic_only": False,
                "local_only": True,
                "model_state": {"clinical_note": str(row.text)},
                "metadata": {
                    "analysis": "frozen_multitask_semantic_benchmark_v1",
                    "outcome": outcome,
                    "label": int(row.label),
                    "match_set": int(row.match_set),
                    "patient_group": str(row.patient_group),
                    "note_category": str(row.category),
                    "dbsource": str(row.dbsource),
                    "hours_since_icu": round(float(row.hours_since_icu), 3),
                    "prediction_horizon_hours": float(OUTCOME_SPECS[outcome]["horizon_hours"]),
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
                "questions": SEMANTIC_CONSTRUCTS,
                "gold": None,
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    return {
        "cases_path": str(outdir / "cases.jsonl"),
        "features_path": str(outdir / "structured_features.csv"),
        "local_index_path": str(outdir / "snapshot_index_local.csv"),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Build frozen v1 multi-outcome MIMIC semantic benchmark cohorts.")
    ap.add_argument("--root", required=True)
    ap.add_argument("--local-output-root", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--controls-per-case", type=int, default=3)
    ap.add_argument("--seed", type=int, default=20260922)
    ap.add_argument("--washout-hours", type=float, default=6.0)
    ap.add_argument("--vital-lookback-hours", type=float, default=6.0)
    ap.add_argument("--lab-lookback-hours", type=float, default=24.0)
    args = ap.parse_args()

    root = resolve_root(args.root)
    local_root = Path(args.local_output_root).expanduser().resolve()
    manifest_path = Path(args.manifest).expanduser().resolve()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)

    update_progress(current=1, total=6, phase="events", message="Loading ICU stays and fixed endpoint evidence", unit="stage")
    icu = load_icustays(root)
    evidence = scan_event_evidence(root)
    assigned = assign_evidence_to_icu(evidence, icu)

    vent_events, vent_map, vent_prevalent = build_incident_event_table(
        assigned,
        {"vent_procedure"},
        {"vent_procedure", "vent_explicit_chart", "vent_support"},
        args.washout_hours,
    )
    rrt_events, rrt_map, rrt_prevalent = build_incident_event_table(
        assigned,
        {"rrt_procedure", "rrt_active_chart"},
        {"rrt_procedure", "rrt_active_chart", "rrt_strict_output"},
        args.washout_hours,
    )
    death_events, death_map = load_death_table(root, icu, args.washout_hours)

    update_progress(current=2, total=6, phase="notes", message="Loading prospectively available bedside notes once", unit="stage")
    notes = load_notes(root, set(icu["hadm_id"].astype(int)))
    note_icu = assign_notes_to_icu(notes, icu)

    update_progress(current=3, total=6, phase="matching", message="Building frozen 1:3 matched risk-set cohorts", unit="stage")
    cohorts = {
        "invasive_ventilation": match_outcome(
            "invasive_ventilation", note_icu, vent_events, vent_map, vent_prevalent,
            12.0, args.controls_per_case, rng,
        ),
        "renal_replacement_therapy": match_outcome(
            "renal_replacement_therapy", note_icu, rrt_events, rrt_map, rrt_prevalent,
            12.0, args.controls_per_case, rng,
        ),
        "icu_death": match_outcome(
            "icu_death", note_icu, death_events, death_map, set(),
            12.0, args.controls_per_case, rng,
        ),
    }

    all_snaps = pd.concat(list(cohorts.values()), ignore_index=True, sort=False)

    update_progress(current=4, total=6, phase="structured_scan", message="Scanning contemporaneous structured physiology", unit="stage")
    phys = extract_physio(root, all_snaps, args.vital_lookback_hours, args.lab_lookback_hours)

    update_progress(current=5, total=6, phase="local_outputs", message="Writing local-only cases, indices, and structured features", unit="stage")
    output_paths = {}
    outcome_reports = {}
    for outcome, s in cohorts.items():
        p = phys[phys["case_id"].isin(set(s["case_id"]))].copy()
        output_paths[outcome] = write_local_outputs(local_root, s, p)
        case = s[s["label"] == 1].copy()
        ctrl = s[s["label"] == 0].copy()
        exact_cat = (
            s.groupby("match_set")["category"].nunique().eq(1).mean()
        )
        delay = pd.to_numeric(s["documentation_delay_hours"], errors="coerce")
        outcome_reports[outcome] = {
            "prediction_horizon_hours": 12.0,
            "matched_cases": int(len(case)),
            "matched_controls": int(len(ctrl)),
            "total_snapshots": int(len(s)),
            "unique_patients": int(s["patient_group"].nunique()),
            "case_note_lead_time_hours": qstats(case["hours_before_event"]),
            "selected_note_hours_since_icu": qstats(s["hours_since_icu"]),
            "storetime_available_fraction": float(s["storetime_available"].astype(bool).mean()),
            "documentation_delay_hours": qstats(delay),
            "complete_sets_exact_note_category_fraction": float(exact_cat),
            "dbsource_counts": {
                str(k): int(v) for k, v in s["dbsource"].value_counts().to_dict().items()
            },
            "note_category_counts": {
                str(k): int(v) for k, v in s["category"].value_counts().to_dict().items()
            },
            "blank_notes": int(s["text"].astype(str).str.strip().eq("").sum()),
        }

    manifest = {
        "analysis": "Frozen multi-outcome semantic benchmark cohort build v1",
        "protocol": "docs/multitask_benchmark_protocol_v1.md",
        "local_only": True,
        "contains_credentialed_note_text_in_declared_artifact": False,
        "contains_source_patient_identifiers_in_declared_artifact": False,
        "model_inference_performed": False,
        "semantic_performance_seen_before_freeze": False,
        "controls_per_case": int(args.controls_per_case),
        "washout_hours": float(args.washout_hours),
        "matching": (
            "1:3 without replacement by control patient; same dbsource required; priority to exact note "
            "category and ICU elapsed-time distance <=6h; maximum elapsed-time distance 12h"
        ),
        "prospective_note_time": (
            "max(CHARTTIME, STORETIME) when STORETIME exists; CHARTTIME fallback otherwise"
        ),
        "outcomes": outcome_reports,
        "local_output_paths": output_paths,
        "structured_features": list(VITAL_ITEMIDS.keys()) + list(LAB_ITEMIDS.keys()),
        "endpoint_definitions": {
            "invasive_ventilation": (
                "first MetaVision Intubation procedure after 6h ICU washout; explicit intubation/ventilator "
                "support evidence screens prevalent disease and future control contamination"
            ),
            "renal_replacement_therapy": (
                "first named RRT procedure or active RRT charting after 6h washout; strict exact CareVue "
                "dialysis output labels are exclusion/prevalence evidence only, never endpoint timestamps"
            ),
            "icu_death": (
                "ADMISSIONS.DEATHTIME during ICU stay after 6h washout"
            ),
        },
        "language_exclusion": {
            k: OUTCOME_SPECS[k]["language_patterns"] for k in OUTCOME_SPECS
        },
        "guardrail": (
            "These endpoint definitions, 12h horizons, note-language exclusions, and matching rules were "
            "frozen before any semantic-model or TF-IDF performance was observed for the new outcomes."
        ),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    update_progress(current=6, total=6, phase="complete", message="Frozen multi-outcome cohorts built", unit="stage")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
