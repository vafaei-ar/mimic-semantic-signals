from __future__ import annotations

import argparse
import json
import random
import re
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd


AGENT_ORDER = [
    "norepinephrine",
    "phenylephrine",
    "dopamine",
    "epinephrine",
    "vasopressin",
]

AGENT_PATTERNS = {
    "norepinephrine": re.compile(r"norepinephrine|noradrenaline|levophed", re.I),
    "phenylephrine": re.compile(r"phenylephrine|neosynephrine|neo-synephrine", re.I),
    "dopamine": re.compile(r"\bdopamine\b", re.I),
    "epinephrine": re.compile(r"(?<!nor)(?<!deoxy)epinephrine|(?<!nor)adrenaline", re.I),
    "vasopressin": re.compile(r"vasopressin", re.I),
}

NW_VITAL_ALIASES = {
    "heart_rate": ["pulse", "heart rate"],
    "map": [
        "bp mean",
        "mean arterial pressure",
        "arterial bp mean",
        "arterial blood pressure mean",
        "non invasive blood pressure mean",
        "non-invasive blood pressure mean",
    ],
    "resp_rate": ["respiratory rate", "respirations", "respiration rate"],
    "spo2": ["pulse oximetry", "spo2", "o2 saturation", "oxygen saturation"],
    "temperature": ["temperature"],
    "sbp": [
        "bp systolic",
        "systolic blood pressure",
        "arterial blood pressure systolic",
        "non invasive blood pressure systolic",
        "non-invasive blood pressure systolic",
    ],
    "dbp": [
        "bp diastolic",
        "diastolic blood pressure",
        "arterial blood pressure diastolic",
        "non invasive blood pressure diastolic",
        "non-invasive blood pressure diastolic",
    ],
}

NW_LAB_ALIASES = {
    "lactate": ["lactate"],
    "creatinine": ["creatinine"],
    "wbc": ["white blood cells", "wbc"],
}

EICU_VITAL_COLUMNS = {
    "heart_rate": ("vitalPeriodic.csv.gz", "heartrate"),
    "map": ("vitalPeriodic.csv.gz", "systemicmean"),
    "resp_rate": ("vitalPeriodic.csv.gz", "respiration"),
    "spo2": ("vitalPeriodic.csv.gz", "sao2"),
    "temperature": ("vitalPeriodic.csv.gz", "temperature"),
    "sbp": ("vitalPeriodic.csv.gz", "systemicsystolic"),
    "dbp": ("vitalPeriodic.csv.gz", "systemicdiastolic"),
}

EICU_LAB_ALIASES = {
    "lactate": ["lactate"],
    "creatinine": ["creatinine"],
    "wbc": ["wbc x 1000", "wbc"],
}


def norm_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def find_one(root: Path, name: str) -> Path:
    hits = list(root.rglob(name))
    if len(hits) != 1:
        raise RuntimeError(f"Expected exactly one {name} under {root}; found {len(hits)}")
    return hits[0]


def classify_agent(text: str) -> str | None:
    s = str(text)
    for agent in AGENT_ORDER:
        if AGENT_PATTERNS[agent].search(s):
            return agent
    return None


def eicu_name_mask(series: pd.Series) -> pd.Series:
    s = series.astype(str)
    mask = pd.Series(False, index=s.index)
    for rx in AGENT_PATTERNS.values():
        mask |= s.str.contains(rx, regex=True, na=False)
    return mask


def nwicu_curated_agent(text: str) -> str | None:
    s = str(text).upper()

    if "IV SOLN" not in s:
        return None
    if any(
        token in s
        for token in [
            "LIDOCAINE-EPINEPHRINE",
            "BUPIVACAINE-EPINEPHRINE",
            "RACEPINEPHRINE",
            "NASL",
            "RECT",
            "ORAL",
            "OPHT",
            "SYRG",
            "ATIN",
        ]
    ):
        return None

    if "NOREPINEPHRINE" in s:
        return "norepinephrine"
    if "DOPAMINE" in s:
        return "dopamine"
    if "PHENYLEPHRINE" in s or "NEOSYNEPHRINE" in s:
        return "phenylephrine" if re.search(r"\b(?:100|250|500)\s*ML\b", s) else None
    if "EPINEPHRINE" in s:
        return "epinephrine" if re.search(r"\b(?:100|250|500)\s*ML\b", s) else None
    if "VASOPRESSIN" in s:
        return "vasopressin" if re.search(r"\b(?:50|100|250|500)\s*ML\b", s) else None
    return None


def first_eicu_pressors(root: Path) -> pd.DataFrame:
    infusion = find_one(root, "infusionDrug.csv.gz")
    rows = []
    for chunk in pd.read_csv(
        infusion,
        chunksize=250_000,
        usecols=[
            "patientunitstayid",
            "infusionoffset",
            "drugname",
            "drugrate",
            "infusionrate",
        ],
        low_memory=False,
    ):
        chunk["patientunitstayid"] = pd.to_numeric(chunk["patientunitstayid"], errors="coerce")
        chunk["infusionoffset"] = pd.to_numeric(chunk["infusionoffset"], errors="coerce")
        chunk["drugrate_num"] = pd.to_numeric(chunk["drugrate"], errors="coerce")
        chunk["infusionrate_num"] = pd.to_numeric(chunk["infusionrate"], errors="coerce")
        chunk = chunk.dropna(subset=["patientunitstayid", "infusionoffset", "drugname"]).copy()
        if chunk.empty:
            continue
        mask = eicu_name_mask(chunk["drugname"])
        p = chunk.loc[mask].copy()
        if p.empty:
            continue
        p["agent"] = p["drugname"].map(classify_agent)
        p = p[p["agent"].notna()].copy()
        p = p[p["drugrate_num"].gt(0) | p["infusionrate_num"].gt(0)].copy()
        p = p[p["infusionoffset"] >= 0].copy()
        if p.empty:
            continue
        p["patientunitstayid"] = p["patientunitstayid"].astype("int64")
        rows.append(p[["patientunitstayid", "infusionoffset", "agent"]])

    if not rows:
        raise RuntimeError("No curated eICU vasopressor events found.")
    events = pd.concat(rows, ignore_index=True)
    events = events.sort_values("infusionoffset")
    first = events.groupby("patientunitstayid", as_index=False).first()
    first["event_hour"] = first["infusionoffset"] / 60.0
    return first[["patientunitstayid", "event_hour", "agent"]]


def load_eicu_units(root: Path) -> pd.DataFrame:
    patient = pd.read_csv(
        find_one(root, "patient.csv.gz"),
        usecols=[
            "patientunitstayid",
            "patienthealthsystemstayid",
            "hospitalid",
            "unitdischargeoffset",
            "uniquepid",
            "unittype",
        ],
        low_memory=False,
    )
    for col in ["patientunitstayid", "patienthealthsystemstayid", "hospitalid", "unitdischargeoffset"]:
        patient[col] = pd.to_numeric(patient[col], errors="coerce")
    patient = patient.dropna(
        subset=["patientunitstayid", "hospitalid", "unitdischargeoffset", "uniquepid"]
    ).copy()
    patient["patientunitstayid"] = patient["patientunitstayid"].astype("int64")
    patient["hospitalid"] = patient["hospitalid"].astype("int64")
    patient["icu_los_h"] = patient["unitdischargeoffset"] / 60.0
    patient["person_key"] = patient["uniquepid"].astype(str)
    return patient


def first_nwicu_pressors(root: Path, icu: pd.DataFrame) -> pd.DataFrame:
    emar = find_one(root, "emar.csv.gz")
    icu_small = icu[["subject_id", "hadm_id", "stay_id", "intime", "outtime"]].copy()
    rows = []
    broad_rx = re.compile(
        r"norepinephrine|noradrenaline|levophed|phenylephrine|neosynephrine|"
        r"\bdopamine\b|(?<!nor)(?<!deoxy)epinephrine|(?<!nor)adrenaline|vasopressin",
        re.I,
    )

    for chunk in pd.read_csv(
        emar,
        chunksize=200_000,
        usecols=["subject_id", "hadm_id", "charttime", "medication", "event_txt"],
        low_memory=False,
    ):
        chunk["subject_id"] = pd.to_numeric(chunk["subject_id"], errors="coerce")
        chunk["hadm_id"] = pd.to_numeric(chunk["hadm_id"], errors="coerce")
        chunk["charttime"] = pd.to_datetime(chunk["charttime"], errors="coerce")
        chunk = chunk.dropna(subset=["subject_id", "hadm_id", "charttime", "medication"]).copy()
        if chunk.empty:
            continue
        broad = chunk["medication"].astype(str).str.contains(broad_rx, regex=True, na=False)
        p = chunk.loc[broad].copy()
        if p.empty:
            continue
        p["agent"] = p["medication"].map(nwicu_curated_agent)
        p = p[p["agent"].notna()].copy()
        p = p[p["event_txt"].fillna("").astype(str).str.strip().str.lower().eq("confirmed")].copy()
        if p.empty:
            continue
        p["subject_id"] = p["subject_id"].astype("int64")
        p["hadm_id"] = p["hadm_id"].astype("int64")
        m = p.merge(icu_small, on=["subject_id", "hadm_id"], how="inner")
        m = m[(m["charttime"] >= m["intime"]) & (m["charttime"] <= m["outtime"])].copy()
        if m.empty:
            continue
        m["event_hour"] = (m["charttime"] - m["intime"]).dt.total_seconds() / 3600.0
        rows.append(m[["stay_id", "event_hour", "agent", "charttime"]])

    if not rows:
        raise RuntimeError("No curated NWICU vasopressor events found.")
    events = pd.concat(rows, ignore_index=True)
    first = events.sort_values("charttime").groupby("stay_id", as_index=False).first()
    return first[["stay_id", "event_hour", "agent"]]


def load_nwicu_units(root: Path) -> pd.DataFrame:
    icu = pd.read_csv(
        find_one(root, "icustays.csv.gz"),
        usecols=["subject_id", "hadm_id", "stay_id", "first_careunit", "intime", "outtime"],
        parse_dates=["intime", "outtime"],
        low_memory=False,
    )
    for col in ["subject_id", "hadm_id", "stay_id"]:
        icu[col] = pd.to_numeric(icu[col], errors="coerce")
    icu = icu.dropna(subset=["subject_id", "hadm_id", "stay_id", "intime", "outtime"]).copy()
    icu[["subject_id", "hadm_id", "stay_id"]] = icu[
        ["subject_id", "hadm_id", "stay_id"]
    ].astype("int64")
    icu["icu_los_h"] = (icu["outtime"] - icu["intime"]).dt.total_seconds() / 3600.0
    icu["person_key"] = icu["subject_id"].astype(str)
    return icu


def match_risksets(
    units: pd.DataFrame,
    events: pd.DataFrame,
    *,
    stay_col: str,
    person_col: str,
    site_col: str,
    horizon_h: float,
    controls_per_case: int,
    seed: int,
) -> tuple[pd.DataFrame, dict]:
    rng = random.Random(seed)
    d = units.merge(events, on=stay_col, how="left")
    d["event_hour"] = pd.to_numeric(d["event_hour"], errors="coerce")

    case_pool = d[
        d["event_hour"].notna()
        & (d["event_hour"] >= horizon_h)
        & (d["event_hour"] <= d["icu_los_h"])
    ].copy()
    case_pool["anchor_hour"] = case_pool["event_hour"] - horizon_h
    case_pool = (
        case_pool.sort_values([person_col, "event_hour", stay_col])
        .groupby(person_col, as_index=False)
        .first()
    )
    case_people = set(case_pool[person_col].astype(str))

    control_units = d[~d[person_col].astype(str).isin(case_people)].copy()

    selected_cases = []
    selected_controls = []
    used_people: set[str] = set()

    for case in case_pool.sort_values([site_col, "anchor_hour", stay_col]).itertuples(index=False):
        case_dict = case._asdict()
        site_value = case_dict[site_col]
        anchor_h = float(case_dict["anchor_hour"])
        horizon_end = anchor_h + horizon_h

        avail = control_units[
            (control_units[site_col].astype(str) == str(site_value))
            & (~control_units[person_col].astype(str).isin(used_people))
            & (control_units["icu_los_h"] >= horizon_end)
            & (
                control_units["event_hour"].isna()
                | (control_units["event_hour"] > horizon_end)
            )
        ].copy()
        if avail.empty:
            continue

        # Same elapsed-time landmark is assigned to controls; tie-breaking is seeded.
        avail["jitter"] = [rng.random() for _ in range(len(avail))]
        avail = avail.sort_values(["jitter", stay_col]).drop_duplicates(person_col)
        take = avail.head(controls_per_case).copy()
        if len(take) < controls_per_case:
            continue

        selected_cases.append(case_dict)
        take["anchor_hour"] = anchor_h
        selected_controls.append(take)
        used_people.update(take[person_col].astype(str).tolist())

    if not selected_cases:
        raise RuntimeError("No fully matched external risk sets were found.")

    cases = pd.DataFrame(selected_cases)
    controls = pd.concat(selected_controls, ignore_index=True)
    cases["label"] = 1
    controls["label"] = 0

    cases["match_set"] = np.arange(1, len(cases) + 1)
    controls["match_set"] = np.repeat(
        np.arange(1, len(cases) + 1), controls_per_case
    )

    snapshots = pd.concat([cases, controls], ignore_index=True, sort=False)
    snapshots = snapshots.reset_index(drop=True)
    snapshots["snapshot_id"] = [
        f"s{i:06d}" for i in range(1, len(snapshots) + 1)
    ]

    people = sorted(snapshots[person_col].astype(str).unique())
    person_map = {p: f"p{i:06d}" for i, p in enumerate(people, 1)}
    sites = sorted(snapshots[site_col].astype(str).unique())
    site_map = {s: f"site_{i:03d}" for i, s in enumerate(sites, 1)}
    snapshots["patient_group"] = snapshots[person_col].astype(str).map(person_map)
    snapshots["site_group"] = snapshots[site_col].astype(str).map(site_map)

    report = {
        "eligible_case_patients": int(case_pool[person_col].nunique()),
        "matched_cases": int((snapshots["label"] == 1).sum()),
        "matched_controls": int((snapshots["label"] == 0).sum()),
        "total_snapshots": int(len(snapshots)),
        "unique_patients": int(snapshots["patient_group"].nunique()),
        "sites_represented": int(snapshots["site_group"].nunique()),
        "controls_per_case": controls_per_case,
        "prediction_horizon_hours": horizon_h,
        "case_first_agent": (
            snapshots.loc[snapshots["label"] == 1, "agent"]
            .fillna("none")
            .astype(str)
            .value_counts()
            .astype(int)
            .to_dict()
        ),
        "case_anchor_hour": quantiles(
            snapshots.loc[snapshots["label"] == 1, "anchor_hour"]
        ),
    }
    return snapshots, report


def quantiles(values: pd.Series) -> dict:
    x = pd.to_numeric(values, errors="coerce").dropna()
    if x.empty:
        return {"n": 0}
    return {
        "n": int(len(x)),
        "p05": float(x.quantile(0.05)),
        "p25": float(x.quantile(0.25)),
        "median": float(x.median()),
        "p75": float(x.quantile(0.75)),
        "p95": float(x.quantile(0.95)),
    }


def aggregate_rows(
    rows: pd.DataFrame,
    snapshots: pd.DataFrame,
    *,
    stay_col: str,
    time_col: str,
    value_columns: dict[str, str],
    lookback_h: float,
    time_scale_to_hours: float,
) -> pd.DataFrame:
    if rows.empty:
        return pd.DataFrame({"snapshot_id": snapshots["snapshot_id"]})

    snap = snapshots[["snapshot_id", stay_col, "anchor_hour"]].copy()
    snap[stay_col] = pd.to_numeric(snap[stay_col], errors="coerce")
    anchor_map = snap.set_index(stay_col)["anchor_hour"].to_dict()
    id_map = snap.set_index(stay_col)["snapshot_id"].to_dict()

    r = rows.copy()
    r[stay_col] = pd.to_numeric(r[stay_col], errors="coerce")
    r[time_col] = pd.to_numeric(r[time_col], errors="coerce") * time_scale_to_hours
    r = r[r[stay_col].isin(anchor_map)].copy()
    if r.empty:
        return pd.DataFrame({"snapshot_id": snapshots["snapshot_id"]})

    r["anchor_hour"] = r[stay_col].map(anchor_map)
    r["snapshot_id"] = r[stay_col].map(id_map)
    r = r[
        (r[time_col] <= r["anchor_hour"])
        & (r[time_col] >= (r["anchor_hour"] - lookback_h).clip(lower=0))
    ].copy()

    out = pd.DataFrame({"snapshot_id": snapshots["snapshot_id"]})
    for feature, source_col in value_columns.items():
        q = r[[ "snapshot_id", time_col, source_col]].copy()
        q[source_col] = pd.to_numeric(q[source_col], errors="coerce")
        q = q.dropna(subset=[source_col]).sort_values(["snapshot_id", time_col])
        if q.empty:
            out[f"{feature}_last"] = np.nan
            out[f"{feature}_delta"] = np.nan
            continue
        g = q.groupby("snapshot_id")[source_col]
        last = g.last()
        first = g.first()
        count = g.count()
        delta = (last - first).where(count >= 2, np.nan)
        stats = pd.DataFrame({
            "snapshot_id": last.index,
            f"{feature}_last": last.values,
            f"{feature}_delta": delta.values,
        })
        out = out.merge(stats, on="snapshot_id", how="left")
    return out


def eicu_features(
    root: Path,
    snapshots: pd.DataFrame,
    vital_lookback_h: float,
    lab_lookback_h: float,
) -> pd.DataFrame:
    stays = set(snapshots["patientunitstayid"].astype(int))

    vp = find_one(root, "vitalPeriodic.csv.gz")
    vital_parts = []
    usecols = ["patientunitstayid", "observationoffset"] + [
        source for _, source in EICU_VITAL_COLUMNS.values()
    ]
    for chunk in pd.read_csv(vp, chunksize=500_000, usecols=list(dict.fromkeys(usecols)), low_memory=False):
        chunk["patientunitstayid"] = pd.to_numeric(chunk["patientunitstayid"], errors="coerce")
        q = chunk[chunk["patientunitstayid"].isin(stays)].copy()
        if not q.empty:
            vital_parts.append(q)

    vitals = pd.concat(vital_parts, ignore_index=True) if vital_parts else pd.DataFrame()
    value_map = {name: source for name, (_, source) in EICU_VITAL_COLUMNS.items()}
    vf = aggregate_rows(
        vitals,
        snapshots,
        stay_col="patientunitstayid",
        time_col="observationoffset",
        value_columns=value_map,
        lookback_h=vital_lookback_h,
        time_scale_to_hours=1.0 / 60.0,
    )

    # Add non-invasive MAP if systemic MAP is absent.
    va = find_one(root, "vitalAperiodic.csv.gz")
    aparts = []
    aperiodic_header = list(pd.read_csv(va, nrows=0).columns)
    aperiodic_keep = [
        c for c in [
            "patientunitstayid",
            "observationoffset",
            "noninvasivemean",
            "noninvasivesystolic",
            "noninvasivediastolic",
        ]
        if c in aperiodic_header
    ]
    for chunk in pd.read_csv(
        va,
        chunksize=500_000,
        usecols=aperiodic_keep,
        low_memory=False,
    ):
        chunk["patientunitstayid"] = pd.to_numeric(chunk["patientunitstayid"], errors="coerce")
        q = chunk[chunk["patientunitstayid"].isin(stays)].copy()
        if not q.empty:
            aparts.append(q)
    aper = pd.concat(aparts, ignore_index=True) if aparts else pd.DataFrame()
    aperiodic_cols = set(pd.read_csv(va, nrows=0).columns)
    fallback_values = {}
    if "noninvasivemean" in aperiodic_cols:
        fallback_values["map_noninvasive"] = "noninvasivemean"
    if "noninvasivesystolic" in aperiodic_cols:
        fallback_values["sbp_noninvasive"] = "noninvasivesystolic"
    if "noninvasivediastolic" in aperiodic_cols:
        fallback_values["dbp_noninvasive"] = "noninvasivediastolic"

    af = aggregate_rows(
        aper,
        snapshots,
        stay_col="patientunitstayid",
        time_col="observationoffset",
        value_columns=fallback_values,
        lookback_h=vital_lookback_h,
        time_scale_to_hours=1.0 / 60.0,
    )
    vf = vf.merge(af, on="snapshot_id", how="left")
    for base in ["map", "sbp", "dbp"]:
        fallback = f"{base}_noninvasive"
        if f"{base}_last" in vf and f"{fallback}_last" in vf:
            vf[f"{base}_last"] = vf[f"{base}_last"].fillna(vf[f"{fallback}_last"])
            vf[f"{base}_delta"] = vf[f"{base}_delta"].fillna(vf[f"{fallback}_delta"])
            vf = vf.drop(columns=[f"{fallback}_last", f"{fallback}_delta"])

    lab = find_one(root, "lab.csv.gz")
    anchors = snapshots.set_index("patientunitstayid")["anchor_hour"].to_dict()
    id_map = snapshots.set_index("patientunitstayid")["snapshot_id"].to_dict()
    lab_parts = []
    aliases = {
        k: {norm_text(x) for x in vals}
        for k, vals in EICU_LAB_ALIASES.items()
    }
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
        q["feature"] = q["labname"].map(
            lambda x: next((k for k, vals in aliases.items() if norm_text(x) in vals), None)
        )
        q = q[q["feature"].notna()].copy()
        if not q.empty:
            lab_parts.append(q)

    labs = pd.concat(lab_parts, ignore_index=True) if lab_parts else pd.DataFrame()
    out = vf
    if not labs.empty:
        labs["lab_hour"] = pd.to_numeric(labs["labresultoffset"], errors="coerce") / 60.0
        labs["anchor_hour"] = labs["patientunitstayid"].map(anchors)
        labs["snapshot_id"] = labs["patientunitstayid"].map(id_map)
        labs["labresult"] = pd.to_numeric(labs["labresult"], errors="coerce")
        labs = labs[
            labs["labresult"].notna()
            & (labs["lab_hour"] <= labs["anchor_hour"])
            & (labs["lab_hour"] >= (labs["anchor_hour"] - lab_lookback_h).clip(lower=0))
        ].copy()
        for feature in EICU_LAB_ALIASES:
            q = labs[labs["feature"] == feature].sort_values(["snapshot_id", "lab_hour"])
            if q.empty:
                out[f"{feature}_last"] = np.nan
                out[f"{feature}_delta"] = np.nan
                continue
            g = q.groupby("snapshot_id")["labresult"]
            last = g.last()
            first = g.first()
            count = g.count()
            delta = (last - first).where(count >= 2, np.nan)
            stats = pd.DataFrame({
                "snapshot_id": last.index,
                f"{feature}_last": last.values,
                f"{feature}_delta": delta.values,
            })
            out = out.merge(stats, on="snapshot_id", how="left")
    else:
        for feature in EICU_LAB_ALIASES:
            out[f"{feature}_last"] = np.nan
            out[f"{feature}_delta"] = np.nan
    return out


def select_nw_dictionary(
    root: Path,
) -> tuple[dict[str, list[int]], dict[str, list[int]], dict]:
    items = pd.read_csv(find_one(root, "d_items.csv.gz"), low_memory=False)
    labs = pd.read_csv(find_one(root, "d_labitems.csv.gz"), low_memory=False)

    vital_map: dict[str, list[int]] = {}
    chosen_vitals = {}
    for feature, aliases in NW_VITAL_ALIASES.items():
        allowed = {norm_text(x) for x in aliases}
        q = items[items["label"].map(norm_text).isin(allowed)].copy()
        if "linksto" in q:
            q = q[q["linksto"].astype(str).str.lower().eq("chartevents")]
        ids = sorted(pd.to_numeric(q["itemid"], errors="coerce").dropna().astype(int).unique().tolist())
        vital_map[feature] = ids
        chosen_vitals[feature] = q[["itemid", "label"]].drop_duplicates().to_dict("records")

    lab_map: dict[str, list[int]] = {}
    chosen_labs = {}
    for feature, aliases in NW_LAB_ALIASES.items():
        allowed = {norm_text(x) for x in aliases}
        q = labs[labs["label"].map(norm_text).isin(allowed)].copy()
        # Prefer blood when fluid is explicitly available.
        if "fluid" in q.columns:
            blood = q[q["fluid"].astype(str).str.lower().eq("blood")]
            if not blood.empty:
                q = blood
        ids = sorted(pd.to_numeric(q["itemid"], errors="coerce").dropna().astype(int).unique().tolist())
        lab_map[feature] = ids
        chosen_labs[feature] = q[
            [c for c in ["itemid", "label", "fluid"] if c in q.columns]
        ].drop_duplicates().to_dict("records")

    return vital_map, lab_map, {
        "vitals": chosen_vitals,
        "labs": chosen_labs,
    }


def nwicu_features(
    root: Path,
    snapshots: pd.DataFrame,
    vital_lookback_h: float,
    lab_lookback_h: float,
) -> tuple[pd.DataFrame, dict]:
    vital_map, lab_map, dictionary = select_nw_dictionary(root)
    stays = set(snapshots["stay_id"].astype(int))
    hadms = set(snapshots["hadm_id"].astype(int))

    anchor_time_map = snapshots.set_index("stay_id")["anchor_time"].to_dict()
    sid_map = snapshots.set_index("stay_id")["snapshot_id"].to_dict()

    all_vital_ids = set().union(*[set(v) for v in vital_map.values()]) if vital_map else set()
    chart = find_one(root, "chartevents.csv.gz")
    vparts = []
    for chunk in pd.read_csv(
        chart,
        chunksize=500_000,
        usecols=["stay_id", "charttime", "itemid", "valuenum"],
        low_memory=False,
    ):
        chunk["stay_id"] = pd.to_numeric(chunk["stay_id"], errors="coerce")
        chunk["itemid"] = pd.to_numeric(chunk["itemid"], errors="coerce")
        q = chunk[
            chunk["stay_id"].isin(stays) & chunk["itemid"].isin(all_vital_ids)
        ].copy()
        if not q.empty:
            vparts.append(q)

    vitals = pd.concat(vparts, ignore_index=True) if vparts else pd.DataFrame()
    out = pd.DataFrame({"snapshot_id": snapshots["snapshot_id"]})
    if not vitals.empty:
        vitals["charttime"] = pd.to_datetime(vitals["charttime"], errors="coerce")
        vitals["anchor_time"] = vitals["stay_id"].map(anchor_time_map)
        vitals["snapshot_id"] = vitals["stay_id"].map(sid_map)
        vitals["valuenum"] = pd.to_numeric(vitals["valuenum"], errors="coerce")
        vitals = vitals[
            vitals["charttime"].notna()
            & vitals["valuenum"].notna()
            & (vitals["charttime"] <= vitals["anchor_time"])
            & (vitals["charttime"] >= vitals["anchor_time"] - pd.to_timedelta(vital_lookback_h, unit="h"))
        ].copy()
        for feature, ids in vital_map.items():
            q = vitals[vitals["itemid"].isin(ids)].sort_values(["snapshot_id", "charttime"])
            if q.empty:
                out[f"{feature}_last"] = np.nan
                out[f"{feature}_delta"] = np.nan
                continue
            g = q.groupby("snapshot_id")["valuenum"]
            last = g.last()
            first = g.first()
            count = g.count()
            delta = (last - first).where(count >= 2, np.nan)
            stats = pd.DataFrame({
                "snapshot_id": last.index,
                f"{feature}_last": last.values,
                f"{feature}_delta": delta.values,
            })
            out = out.merge(stats, on="snapshot_id", how="left")
    else:
        for feature in vital_map:
            out[f"{feature}_last"] = np.nan
            out[f"{feature}_delta"] = np.nan

    all_lab_ids = set().union(*[set(v) for v in lab_map.values()]) if lab_map else set()
    lab = find_one(root, "labevents.csv.gz")
    lparts = []
    for chunk in pd.read_csv(
        lab,
        chunksize=500_000,
        usecols=["hadm_id", "charttime", "itemid", "valuenum"],
        low_memory=False,
    ):
        chunk["hadm_id"] = pd.to_numeric(chunk["hadm_id"], errors="coerce")
        chunk["itemid"] = pd.to_numeric(chunk["itemid"], errors="coerce")
        q = chunk[
            chunk["hadm_id"].isin(hadms) & chunk["itemid"].isin(all_lab_ids)
        ].copy()
        if not q.empty:
            lparts.append(q)

    labs = pd.concat(lparts, ignore_index=True) if lparts else pd.DataFrame()
    if not labs.empty:
        snap_hadm = snapshots[["snapshot_id", "hadm_id", "anchor_time"]].copy()
        labs = labs.merge(snap_hadm, on="hadm_id", how="inner")
        labs["charttime"] = pd.to_datetime(labs["charttime"], errors="coerce")
        labs["valuenum"] = pd.to_numeric(labs["valuenum"], errors="coerce")
        labs = labs[
            labs["charttime"].notna()
            & labs["valuenum"].notna()
            & (labs["charttime"] <= labs["anchor_time"])
            & (labs["charttime"] >= labs["anchor_time"] - pd.to_timedelta(lab_lookback_h, unit="h"))
        ].copy()
        for feature, ids in lab_map.items():
            q = labs[labs["itemid"].isin(ids)].sort_values(["snapshot_id", "charttime"])
            if q.empty:
                out[f"{feature}_last"] = np.nan
                out[f"{feature}_delta"] = np.nan
                continue
            g = q.groupby("snapshot_id")["valuenum"]
            last = g.last()
            first = g.first()
            count = g.count()
            delta = (last - first).where(count >= 2, np.nan)
            stats = pd.DataFrame({
                "snapshot_id": last.index,
                f"{feature}_last": last.values,
                f"{feature}_delta": delta.values,
            })
            out = out.merge(stats, on="snapshot_id", how="left")
    else:
        for feature in lab_map:
            out[f"{feature}_last"] = np.nan
            out[f"{feature}_delta"] = np.nan

    return out, dictionary


def safe_feature_export(
    snapshots: pd.DataFrame,
    features: pd.DataFrame,
    *,
    site_extra: str | None = None,
) -> pd.DataFrame:
    base_cols = [
        "snapshot_id",
        "label",
        "match_set",
        "patient_group",
        "site_group",
        "anchor_hour",
    ]
    if site_extra and site_extra in snapshots:
        # Do not export raw site labels/ids; site_group is enough.
        pass
    out = snapshots[base_cols].merge(features, on="snapshot_id", how="left")
    return out


def missingness_report(df: pd.DataFrame) -> dict:
    feature_cols = [
        c for c in df.columns
        if c not in {
            "snapshot_id",
            "label",
            "match_set",
            "patient_group",
            "site_group",
            "anchor_hour",
        }
    ]
    overall = {
        c: float(df[c].isna().mean())
        for c in feature_cols
    }
    by_label = {}
    for label in [0, 1]:
        q = df[df["label"] == label]
        by_label[str(label)] = {
            c: float(q[c].isna().mean()) if len(q) else None
            for c in feature_cols
        }
    return {
        "overall_fraction_missing": overall,
        "by_label_fraction_missing": by_label,
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Build local-only six-hour structured vasopressor risk-set cohorts in "
            "eICU and NWICU. Only the aggregate report is intended for sharing."
        )
    )
    ap.add_argument("--eicu-root", required=True)
    ap.add_argument("--nwicu-root", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--controls-per-case", type=int, default=3)
    ap.add_argument("--prediction-horizon-hours", type=float, default=6.0)
    ap.add_argument("--vital-lookback-hours", type=float, default=6.0)
    ap.add_argument("--lab-lookback-hours", type=float, default=24.0)
    ap.add_argument("--seed", type=int, default=20260921)
    args = ap.parse_args()

    eicu_root = Path(args.eicu_root).expanduser().resolve()
    nwicu_root = Path(args.nwicu_root).expanduser().resolve()
    outdir = Path(args.output_dir).expanduser().resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    horizon = float(args.prediction_horizon_hours)

    # eICU
    e_units = load_eicu_units(eicu_root)
    e_events = first_eicu_pressors(eicu_root)
    e_snap, e_report = match_risksets(
        e_units,
        e_events,
        stay_col="patientunitstayid",
        person_col="person_key",
        site_col="hospitalid",
        horizon_h=horizon,
        controls_per_case=args.controls_per_case,
        seed=args.seed,
    )
    e_features = eicu_features(
        eicu_root,
        e_snap,
        args.vital_lookback_hours,
        args.lab_lookback_hours,
    )
    e_safe = safe_feature_export(e_snap, e_features)
    e_path = outdir / "eicu_structured_riskset_features.csv"
    e_safe.to_csv(e_path, index=False)
    e_report["missingness"] = missingness_report(e_safe)
    e_report["local_feature_file"] = e_path.name

    # NWICU
    n_units = load_nwicu_units(nwicu_root)
    n_events = first_nwicu_pressors(nwicu_root, n_units)
    n_snap, n_report = match_risksets(
        n_units,
        n_events,
        stay_col="stay_id",
        person_col="person_key",
        site_col="first_careunit",
        horizon_h=horizon,
        controls_per_case=args.controls_per_case,
        seed=args.seed + 1,
    )
    n_snap["anchor_time"] = (
        n_snap["intime"]
        + pd.to_timedelta(n_snap["anchor_hour"], unit="h")
    )
    n_features, n_dictionary = nwicu_features(
        nwicu_root,
        n_snap,
        args.vital_lookback_hours,
        args.lab_lookback_hours,
    )
    n_safe = safe_feature_export(n_snap, n_features)
    n_path = outdir / "nwicu_structured_riskset_features.csv"
    n_safe.to_csv(n_path, index=False)
    n_report["missingness"] = missingness_report(n_safe)
    n_report["selected_item_dictionary"] = n_dictionary
    n_report["local_feature_file"] = n_path.name

    report = {
        "contains_note_text": False,
        "contains_source_patient_identifiers": False,
        "patient_level_feature_files_shared_as_artifacts": False,
        "analysis_role": (
            "external structured validation of the six-hour vasopressor endpoint "
            "and physiology comparator; these datasets do not validate the narrative "
            "semantic signal itself"
        ),
        "endpoint": (
            "first curated continuous vasopressor administration/positive-rate infusion"
        ),
        "case_definition": (
            f"first curated vasopressor start at least {horizon:g}h after ICU admission; "
            f"anchor fixed exactly {horizon:g}h before the start"
        ),
        "control_definition": (
            f"same-site/care-unit risk-set control at the matched ICU elapsed time, "
            f"with no prior vasopressor and no first start during the next {horizon:g}h; "
            "ICU stay remains observable through the prediction horizon"
        ),
        "matching": (
            "3 controls per case by default; case patients excluded from controls; "
            "controls used once; exact matched ICU elapsed-time landmark; same hospital "
            "for eICU and same first care unit for NWICU"
        ),
        "prediction_horizon_hours": horizon,
        "vital_lookback_hours": args.vital_lookback_hours,
        "lab_lookback_hours": args.lab_lookback_hours,
        "trend_definition": "delta = last minus first within lookback; requires at least two measurements, otherwise missing",
        "eicu": e_report,
        "nwicu": n_report,
        "next_decision": (
            "Proceed to frozen cross-dataset physiology modeling only if cohort sizes "
            "are adequate and core-feature missingness is not pathologically different "
            "between cases and controls. Preserve MIMIC as development; do not retune "
            "semantic constructs on these structured-only external cohorts."
        ),
    }

    report_path = outdir / "external_structured_riskset_report.json"
    report_path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
