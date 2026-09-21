from __future__ import annotations

import argparse
import json
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


def qstats(values: pd.Series) -> dict:
    x = pd.to_numeric(values, errors="coerce").dropna()
    if x.empty:
        return {
            "n": 0,
            "min": None,
            "p05": None,
            "p25": None,
            "median": None,
            "p75": None,
            "p95": None,
            "max": None,
        }
    return {
        "n": int(len(x)),
        "min": float(x.min()),
        "p05": float(x.quantile(0.05)),
        "p25": float(x.quantile(0.25)),
        "median": float(x.median()),
        "p75": float(x.quantile(0.75)),
        "p95": float(x.quantile(0.95)),
        "max": float(x.max()),
    }


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
    """
    Conservative continuous-pressor formulation filter.

    The raw eMAR substring audit includes local anesthetic combinations,
    nasal/ophthalmic/rectal phenylephrine, epinephrine syringes, and other
    non-pressor uses. Keep only IV solution formulations that plausibly
    represent continuous vasoactive support.
    """
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
        # Prefer premixed/bag formulations over concentrated vial-like products.
        if re.search(r"\b(?:100|250|500)\s*ML\b", s):
            return "phenylephrine"
        return None

    if "EPINEPHRINE" in s:
        if re.search(r"\b(?:100|250|500)\s*ML\b", s):
            return "epinephrine"
        return None

    if "VASOPRESSIN" in s:
        if re.search(r"\b(?:50|100|250|500)\s*ML\b", s):
            return "vasopressin"
        return None

    return None


def audit_eicu(root: Path) -> dict:
    patient_path = find_one(root, "patient.csv.gz")
    infusion_path = find_one(root, "infusionDrug.csv.gz")

    patient = pd.read_csv(
        patient_path,
        usecols=[
            "patientunitstayid",
            "patienthealthsystemstayid",
            "hospitalid",
            "unitdischargeoffset",
        ],
        low_memory=False,
    )
    patient["patientunitstayid"] = pd.to_numeric(
        patient["patientunitstayid"], errors="coerce"
    )
    patient["unitdischargeoffset"] = pd.to_numeric(
        patient["unitdischargeoffset"], errors="coerce"
    )
    patient = patient.dropna(subset=["patientunitstayid"]).copy()
    patient["patientunitstayid"] = patient["patientunitstayid"].astype("int64")

    discharge_map = patient.set_index("patientunitstayid")["unitdischargeoffset"].to_dict()

    total_name_rows = 0
    positive_rate_rows = 0
    in_icu_positive_rows = 0
    negative_offset_rows = 0
    after_discharge_rows = 0
    agent_rows = Counter()
    drug_values = Counter()
    starts: list[dict] = []

    for chunk in pd.read_csv(
        infusion_path,
        chunksize=200_000,
        usecols=[
            "patientunitstayid",
            "infusionoffset",
            "drugname",
            "drugrate",
            "infusionrate",
        ],
        low_memory=False,
    ):
        chunk["patientunitstayid"] = pd.to_numeric(
            chunk["patientunitstayid"], errors="coerce"
        )
        chunk["infusionoffset"] = pd.to_numeric(
            chunk["infusionoffset"], errors="coerce"
        )
        chunk["drugrate_num"] = pd.to_numeric(chunk["drugrate"], errors="coerce")
        chunk["infusionrate_num"] = pd.to_numeric(
            chunk["infusionrate"], errors="coerce"
        )
        chunk = chunk.dropna(
            subset=["patientunitstayid", "infusionoffset", "drugname"]
        ).copy()
        if chunk.empty:
            continue
        chunk["patientunitstayid"] = chunk["patientunitstayid"].astype("int64")

        mask = eicu_name_mask(chunk["drugname"])
        p = chunk.loc[mask].copy()
        if p.empty:
            continue
        total_name_rows += int(len(p))

        p["agent"] = p["drugname"].map(classify_agent)
        p = p[p["agent"].notna()].copy()
        if p.empty:
            continue

        for v, n in p["drugname"].astype(str).value_counts().items():
            drug_values[v] += int(n)

        positive = (
            p["drugrate_num"].gt(0)
            | p["infusionrate_num"].gt(0)
        )
        positive_rate_rows += int(positive.sum())
        p = p.loc[positive].copy()
        if p.empty:
            continue

        negative_offset_rows += int((p["infusionoffset"] < 0).sum())
        p = p[p["infusionoffset"] >= 0].copy()
        if p.empty:
            continue

        p["unitdischargeoffset"] = p["patientunitstayid"].map(discharge_map)
        after = (
            p["unitdischargeoffset"].notna()
            & (p["infusionoffset"] > p["unitdischargeoffset"])
        )
        after_discharge_rows += int(after.sum())
        p = p[~after].copy()
        in_icu_positive_rows += int(len(p))

        for agent, n in p["agent"].value_counts().items():
            agent_rows[str(agent)] += int(n)

        starts.extend(
            p[["patientunitstayid", "infusionoffset", "agent"]]
            .rename(columns={"infusionoffset": "event_offset_min"})
            .to_dict("records")
        )

    starts_df = pd.DataFrame(starts)
    if starts_df.empty:
        first = pd.DataFrame(
            columns=["patientunitstayid", "event_offset_min", "agent"]
        )
    else:
        first = (
            starts_df.sort_values("event_offset_min")
            .groupby("patientunitstayid", as_index=False)
            .first()
        )
    first["hours_since_icu"] = pd.to_numeric(
        first["event_offset_min"], errors="coerce"
    ) / 60.0

    first_agent = (
        first["agent"].value_counts().astype(int).to_dict()
        if not first.empty
        else {}
    )

    return {
        "cohort": {
            "icu_stays": int(patient["patientunitstayid"].nunique()),
            "health_system_stays": int(
                patient["patienthealthsystemstayid"].nunique()
            ),
            "hospitals": int(patient["hospitalid"].nunique()),
        },
        "endpoint_definition": (
            "first in-ICU positive-rate row in infusionDrug for norepinephrine, "
            "phenylephrine, dopamine, epinephrine, or vasopressin; negative offsets "
            "and rows after ICU discharge excluded"
        ),
        "audit": {
            "pressor_name_rows": int(total_name_rows),
            "positive_rate_rows": int(positive_rate_rows),
            "positive_rate_rows_in_icu": int(in_icu_positive_rows),
            "negative_offset_positive_rows": int(negative_offset_rows),
            "after_discharge_positive_rows": int(after_discharge_rows),
            "agent_rows_in_icu": dict(agent_rows),
            "top_drugname_values": [
                {"value": value, "rows": count}
                for value, count in drug_values.most_common(50)
            ],
        },
        "first_start": {
            "unique_icu_stays": int(first["patientunitstayid"].nunique()),
            "percent_of_icu_stays": (
                float(first["patientunitstayid"].nunique())
                / float(patient["patientunitstayid"].nunique())
                * 100.0
                if len(patient)
                else None
            ),
            "hours_since_icu": qstats(first["hours_since_icu"]),
            "first_agent": first_agent,
            "after_6h": int((first["hours_since_icu"] >= 6).sum()),
            "after_12h": int((first["hours_since_icu"] >= 12).sum()),
            "after_24h": int((first["hours_since_icu"] >= 24).sum()),
        },
    }


def audit_nwicu(root: Path) -> dict:
    icu_path = find_one(root, "icustays.csv.gz")
    emar_path = find_one(root, "emar.csv.gz")

    icu = pd.read_csv(
        icu_path,
        usecols=["subject_id", "hadm_id", "stay_id", "intime", "outtime"],
        parse_dates=["intime", "outtime"],
        low_memory=False,
    )
    for col in ["subject_id", "hadm_id", "stay_id"]:
        icu[col] = pd.to_numeric(icu[col], errors="coerce")
    icu = icu.dropna(
        subset=["subject_id", "hadm_id", "stay_id", "intime", "outtime"]
    ).copy()
    icu[["subject_id", "hadm_id", "stay_id"]] = icu[
        ["subject_id", "hadm_id", "stay_id"]
    ].astype("int64")

    icu_small = icu[
        ["subject_id", "hadm_id", "stay_id", "intime", "outtime"]
    ].copy()

    raw_name_rows = 0
    curated_rows = 0
    event_counts = Counter()
    curated_med_values = Counter()
    confirmed_rows = 0
    applied_rows = 0
    not_given_rows = 0
    aligned_rows = 0
    agent_rows = Counter()
    starts: list[dict] = []

    broad_rx = re.compile(
        r"norepinephrine|noradrenaline|levophed|phenylephrine|neosynephrine|"
        r"\bdopamine\b|(?<!nor)(?<!deoxy)epinephrine|(?<!nor)adrenaline|"
        r"vasopressin",
        re.I,
    )

    for chunk in pd.read_csv(
        emar_path,
        chunksize=150_000,
        usecols=[
            "subject_id",
            "hadm_id",
            "charttime",
            "medication",
            "event_txt",
        ],
        low_memory=False,
    ):
        chunk["subject_id"] = pd.to_numeric(chunk["subject_id"], errors="coerce")
        chunk["hadm_id"] = pd.to_numeric(chunk["hadm_id"], errors="coerce")
        chunk["charttime"] = pd.to_datetime(chunk["charttime"], errors="coerce")
        chunk = chunk.dropna(
            subset=["subject_id", "hadm_id", "charttime", "medication"]
        ).copy()
        if chunk.empty:
            continue
        chunk["subject_id"] = chunk["subject_id"].astype("int64")
        chunk["hadm_id"] = chunk["hadm_id"].astype("int64")

        broad = chunk["medication"].astype(str).str.contains(
            broad_rx, regex=True, na=False
        )
        raw_name_rows += int(broad.sum())

        p = chunk.loc[broad].copy()
        if p.empty:
            continue

        p["agent"] = p["medication"].map(nwicu_curated_agent)
        p = p[p["agent"].notna()].copy()
        if p.empty:
            continue
        curated_rows += int(len(p))

        for event, n in p["event_txt"].fillna("<missing>").astype(str).value_counts().items():
            event_counts[event] += int(n)
        for med, n in p["medication"].astype(str).value_counts().items():
            curated_med_values[med] += int(n)

        event_norm = p["event_txt"].fillna("").astype(str).str.strip().str.lower()
        confirmed = event_norm.eq("confirmed")
        applied = event_norm.eq("applied")
        not_given = event_norm.eq("not given")
        confirmed_rows += int(confirmed.sum())
        applied_rows += int(applied.sum())
        not_given_rows += int(not_given.sum())

        # Primary endpoint is deliberately high-specificity: confirmed only.
        p = p.loc[confirmed].copy()
        if p.empty:
            continue

        merged = p.merge(
            icu_small,
            on=["subject_id", "hadm_id"],
            how="inner",
        )
        if merged.empty:
            continue

        in_icu = (
            (merged["charttime"] >= merged["intime"])
            & (merged["charttime"] <= merged["outtime"])
        )
        merged = merged.loc[in_icu].copy()
        if merged.empty:
            continue
        aligned_rows += int(len(merged))

        merged["hours_since_icu"] = (
            merged["charttime"] - merged["intime"]
        ).dt.total_seconds() / 3600.0

        for agent, n in merged["agent"].value_counts().items():
            agent_rows[str(agent)] += int(n)

        starts.extend(
            merged[
                ["subject_id", "hadm_id", "stay_id", "charttime", "hours_since_icu", "agent"]
            ].to_dict("records")
        )

    starts_df = pd.DataFrame(starts)
    if starts_df.empty:
        first = pd.DataFrame(
            columns=[
                "subject_id",
                "hadm_id",
                "stay_id",
                "charttime",
                "hours_since_icu",
                "agent",
            ]
        )
    else:
        first = (
            starts_df.sort_values("charttime")
            .groupby("stay_id", as_index=False)
            .first()
        )

    return {
        "cohort": {
            "subjects": int(icu["subject_id"].nunique()),
            "admissions": int(icu["hadm_id"].nunique()),
            "icu_stays": int(icu["stay_id"].nunique()),
        },
        "endpoint_definition": (
            "first eMAR event during an ICU stay with event_txt='Confirmed' and a "
            "conservative continuous IV vasopressor formulation; bolus syringes, local "
            "anesthetic combinations, nasal/rectal/oral/ophthalmic products, and "
            "Not Given events excluded"
        ),
        "audit": {
            "raw_name_match_rows": int(raw_name_rows),
            "curated_continuous_iv_rows": int(curated_rows),
            "curated_event_txt_counts": dict(event_counts),
            "confirmed_curated_rows": int(confirmed_rows),
            "applied_curated_rows": int(applied_rows),
            "not_given_curated_rows": int(not_given_rows),
            "confirmed_rows_aligned_to_icu": int(aligned_rows),
            "agent_rows_aligned_to_icu": dict(agent_rows),
            "curated_medication_values": [
                {"value": value, "rows": count}
                for value, count in curated_med_values.most_common(50)
            ],
        },
        "first_start": {
            "unique_icu_stays": int(first["stay_id"].nunique()),
            "unique_subjects": int(first["subject_id"].nunique()),
            "percent_of_icu_stays": (
                float(first["stay_id"].nunique())
                / float(icu["stay_id"].nunique())
                * 100.0
                if len(icu)
                else None
            ),
            "hours_since_icu": qstats(first["hours_since_icu"]),
            "first_agent": (
                first["agent"].value_counts().astype(int).to_dict()
                if not first.empty
                else {}
            ),
            "after_6h": int((first["hours_since_icu"] >= 6).sum()),
            "after_12h": int((first["hours_since_icu"] >= 12).sum()),
            "after_24h": int((first["hours_since_icu"] >= 24).sum()),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Curate and audit vasopressor initiation endpoints in eICU and NWICU. "
            "Outputs aggregate metadata only."
        )
    )
    ap.add_argument("--eicu-root", required=True)
    ap.add_argument("--nwicu-root", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    eicu_root = Path(args.eicu_root).expanduser().resolve()
    nwicu_root = Path(args.nwicu_root).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "contains_note_text": False,
        "contains_patient_identifiers": False,
        "raw_patient_level_data_written": False,
        "purpose": (
            "endpoint curation before external structured validation; no outcome model "
            "training or tuning is performed"
        ),
        "eicu": audit_eicu(eicu_root),
        "nwicu": audit_nwicu(nwicu_root),
    }

    output.write_text(
        json.dumps(report, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
