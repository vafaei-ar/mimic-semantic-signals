from __future__ import annotations

from pathlib import Path
import re

import pandas as pd

from common import find_file, lower_columns, module_path, parse_datetime, read_columns


VASO_TERMS = [
    "norepinephrine", "noradrenaline", "epinephrine", "adrenaline",
    "vasopressin", "phenylephrine", "dopamine",
]
INTUBATION_TERMS = ["intubation", "endotracheal intubation"]


def _load_d_items(root: Path) -> pd.DataFrame:
    f = find_file(module_path(root, "mimiciii"), ["D_ITEMS.csv.gz", "D_ITEMS.csv", "d_items.csv.gz", "d_items.csv"])
    if f is None:
        return pd.DataFrame()
    d = lower_columns(pd.read_csv(f, low_memory=False))
    return d


def _itemids_matching(d_items: pd.DataFrame, terms: list[str]) -> set[int]:
    if d_items.empty or "itemid" not in d_items or "label" not in d_items:
        return set()
    pat = "|".join(re.escape(x) for x in terms)
    m = d_items["label"].fillna("").astype(str).str.lower().str.contains(pat, regex=True)
    return set(pd.to_numeric(d_items.loc[m, "itemid"], errors="coerce").dropna().astype("int64").tolist())


def _death_events(root: Path) -> pd.DataFrame:
    f = find_file(module_path(root, "mimiciii"), ["ADMISSIONS.csv.gz", "ADMISSIONS.csv", "admissions.csv.gz", "admissions.csv"])
    if f is None:
        return pd.DataFrame(columns=["subject_id","hadm_id","event_time","event_type"])
    d = lower_columns(pd.read_csv(f, low_memory=False))
    if "deathtime" not in d:
        return pd.DataFrame(columns=["subject_id","hadm_id","event_time","event_type"])
    d["event_time"] = parse_datetime(d["deathtime"])
    d = d[d["event_time"].notna() & d["hadm_id"].notna()].copy()
    d["event_type"] = "in_hospital_death"
    return d[["subject_id","hadm_id","event_time","event_type"]]


def _vasopressor_events(root: Path, itemids: set[int]) -> pd.DataFrame:
    f = find_file(module_path(root, "mimiciii"), ["INPUTEVENTS_MV.csv.gz", "INPUTEVENTS_MV.csv", "inputevents_mv.csv.gz", "inputevents_mv.csv"])
    if f is None or not itemids:
        return pd.DataFrame(columns=["subject_id","hadm_id","event_time","event_type"])
    pieces = []
    reader = read_columns(f, ["subject_id","hadm_id","itemid","starttime","statusdescription"], chunksize=250_000)
    for chunk in reader:
        c = lower_columns(chunk)
        c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
        c = c[c["itemid"].isin(itemids)]
        if "statusdescription" in c:
            c = c[~c["statusdescription"].fillna("").astype(str).str.lower().str.contains("rewritten|cancelled")]
        if c.empty:
            continue
        c["event_time"] = parse_datetime(c["starttime"])
        pieces.append(c[["subject_id","hadm_id","event_time"]])
    if not pieces:
        return pd.DataFrame(columns=["subject_id","hadm_id","event_time","event_type"])
    d = pd.concat(pieces, ignore_index=True).dropna(subset=["hadm_id","event_time"])
    d = d.sort_values("event_time").groupby("hadm_id", as_index=False).first()
    d["event_type"] = "vasopressor_initiation"
    return d[["subject_id","hadm_id","event_time","event_type"]]


def _intubation_events(root: Path, itemids: set[int]) -> pd.DataFrame:
    f = find_file(module_path(root, "mimiciii"), ["PROCEDUREEVENTS_MV.csv.gz", "PROCEDUREEVENTS_MV.csv", "procedureevents_mv.csv.gz", "procedureevents_mv.csv"])
    if f is None or not itemids:
        return pd.DataFrame(columns=["subject_id","hadm_id","event_time","event_type"])
    pieces = []
    reader = read_columns(f, ["subject_id","hadm_id","itemid","starttime"], chunksize=250_000)
    for chunk in reader:
        c = lower_columns(chunk)
        c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
        c = c[c["itemid"].isin(itemids)]
        if c.empty:
            continue
        c["event_time"] = parse_datetime(c["starttime"])
        pieces.append(c[["subject_id","hadm_id","event_time"]])
    if not pieces:
        return pd.DataFrame(columns=["subject_id","hadm_id","event_time","event_type"])
    d = pd.concat(pieces, ignore_index=True).dropna(subset=["hadm_id","event_time"])
    d = d.sort_values("event_time").groupby("hadm_id", as_index=False).first()
    d["event_type"] = "intubation_procedure"
    return d[["subject_id","hadm_id","event_time","event_type"]]


def build_candidate_events(root: Path) -> tuple[pd.DataFrame, dict]:
    d_items = _load_d_items(root)
    vaso_ids = _itemids_matching(d_items, VASO_TERMS)
    intub_ids = _itemids_matching(d_items, INTUBATION_TERMS)

    frames = [
        _death_events(root),
        _vasopressor_events(root, vaso_ids),
        _intubation_events(root, intub_ids),
    ]
    events = pd.concat(frames, ignore_index=True)
    if not events.empty:
        events["subject_id"] = pd.to_numeric(events["subject_id"], errors="coerce")
        events["hadm_id"] = pd.to_numeric(events["hadm_id"], errors="coerce")
        events = events.dropna(subset=["hadm_id","event_time"])
        events["hadm_id"] = events["hadm_id"].astype("int64")

    metadata = {
        "vasopressor_itemids_found": len(vaso_ids),
        "intubation_itemids_found": len(intub_ids),
        "vasopressor_itemids": sorted(vaso_ids),
        "intubation_itemids": sorted(intub_ids),
    }
    return events, metadata
