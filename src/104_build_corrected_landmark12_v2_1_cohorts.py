from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from common import find_file, lower_columns, module_path, parse_datetime, read_columns, resolve_root
from runrelay_progress import update_progress
from semantic_schema import SEMANTIC_CONSTRUCTS


LANDMARK_H = 12.0
HORIZON_H = 12.0

BEDSIDE_CATEGORIES = {
    "Physician",
    "Consult",
    "Nursing",
    "Nursing/other",
    "Respiratory",
    "General",
}

VENT_ENDPOINT_PROCEDURE_IDS = {224385}
VENT_MV_DISQUAL_CHART_IDS = {
    223849,
    224684,
    224688,
    225306,
    225585,
    225588,
    225590,
    225592,
    226431,
    228069,
}
VENT_MV_EXPLICIT_INTUBATION_CHART_IDS = {
    225306,
    225585,
    225588,
    225590,
    225592,
    226431,
    228069,
}
VENT_MV_SUPPORT_CHART_IDS = VENT_MV_DISQUAL_CHART_IDS - VENT_MV_EXPLICIT_INTUBATION_CHART_IDS

RRT_MV_PROCEDURE_IDS = {225441, 225802, 225803, 225805, 225809, 225955}
RRT_MV_ACTIVE_CHART_IDS = {226499, 227290}

LANGUAGE_PATTERNS = {
    "invasive_ventilation": [
        r"\b(?:re[-\s]?)?intubat\w*\b",
        r"\bendotracheal\b",
        r"\bmechanical\s+ventilat\w*\b",
        r"\bventilator\b",
        r"\bETT\b",
    ],
    "renal_replacement_therapy": [
        r"\bdialysis\b",
        r"\bhemodialysis\b",
        r"\bhaemodialysis\b",
        r"\bCVVH\w*\b",
        r"\bCRRT\b",
        r"\bhemofiltration\b",
        r"\bhaemofiltration\b",
        r"\brenal\s+replacement\b",
        r"\btrialysis\b",
    ],
    "icu_death": [
        r"\bdying\b",
        r"\bdeath\b",
        r"\bdeceased\b",
        r"\bcomfort care\b",
        r"\bcomfort measures\b",
        r"\bCMO\b",
        r"\bwithdraw\w*\s+(?:of\s+)?(?:care|support|treatment)\b",
        r"\bhospice\b",
        r"\bDNR\b",
        r"\bDNI\b",
        r"\bdo not resuscitate\b",
        r"\bdo not intubate\b",
        r"\bgoals? of care\b",
        r"\bpalliative\b",
    ],
}


def compile_rx(patterns: list[str]) -> re.Pattern:
    return re.compile("|".join(f"(?:{p})" for p in patterns), flags=re.IGNORECASE)


def stable_case_id(outcome: str, icustay_id: int) -> str:
    raw = f"population_landmark12_v2_1|{outcome}|{int(icustay_id)}"
    return "pl12v21_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def load_icustays(root: Path) -> pd.DataFrame:
    f = find_file(module_path(root, "mimiciii"), ["ICUSTAYS.csv.gz", "ICUSTAYS.csv"])
    if f is None:
        raise FileNotFoundError("ICUSTAYS not found")
    d = lower_columns(
        pd.read_csv(
            f,
            usecols=lambda c: c.lower()
            in {"subject_id", "hadm_id", "icustay_id", "dbsource", "first_careunit", "intime", "outtime"},
            low_memory=False,
        )
    )
    for c in ["subject_id", "hadm_id", "icustay_id"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["intime"] = parse_datetime(d["intime"])
    d["outtime"] = parse_datetime(d["outtime"])
    d["dbsource"] = d["dbsource"].fillna("UNKNOWN").astype(str).str.strip().str.lower()
    d["first_careunit"] = d["first_careunit"].fillna("UNKNOWN").astype(str).str.strip()
    d = d.dropna(subset=["subject_id", "hadm_id", "icustay_id", "intime", "outtime"]).copy()
    d[["subject_id", "hadm_id", "icustay_id"]] = d[
        ["subject_id", "hadm_id", "icustay_id"]
    ].astype("int64")
    return d


def age_years_at_icu(intime, dob) -> float:
    if pd.isna(intime) or pd.isna(dob):
        return float("nan")
    days = (pd.Timestamp(intime).to_pydatetime().date() - pd.Timestamp(dob).to_pydatetime().date()).days
    return days / 365.2425


def adult_eligibility_mask(age_years: pd.Series, first_careunit: pd.Series) -> pd.Series:
    age = pd.to_numeric(age_years, errors="coerce")
    nicu = first_careunit.fillna("UNKNOWN").astype(str).str.strip().str.upper().eq("NICU")
    return age.ge(18) & (~nicu)


def restrict_to_adults(root: Path, icu: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    f = find_file(module_path(root, "mimiciii"), ["PATIENTS.csv.gz", "PATIENTS.csv"])
    if f is None:
        raise FileNotFoundError("PATIENTS not found")
    p = lower_columns(
        pd.read_csv(
            f,
            usecols=lambda c: c.lower() in {"subject_id", "dob"},
            low_memory=False,
        )
    )
    p["subject_id"] = pd.to_numeric(p["subject_id"], errors="coerce")
    p["dob"] = parse_datetime(p["dob"])
    p = p.dropna(subset=["subject_id", "dob"]).copy()
    p["subject_id"] = p["subject_id"].astype("int64")

    q = icu.merge(p[["subject_id", "dob"]], on="subject_id", how="left")
    q["age_at_icu_years_uncapped"] = pd.Series(
        [age_years_at_icu(intime, dob) for intime, dob in zip(q["intime"], q["dob"])],
        index=q.index,
        dtype=float,
    )

    missing_age = q["age_at_icu_years_uncapped"].isna()
    pediatric = q["age_at_icu_years_uncapped"].lt(18)
    nicu = q["first_careunit"].astype(str).str.strip().str.upper().eq("NICU")
    keep = adult_eligibility_mask(q["age_at_icu_years_uncapped"], q["first_careunit"])

    report = {
        "rows_before": int(len(q)),
        "missing_age_excluded": int(missing_age.sum()),
        "age_lt_18_excluded": int(pediatric.fillna(False).sum()),
        "nicu_first_careunit_excluded": int(nicu.sum()),
        "rows_after": int(keep.sum()),
        "unique_patients_after": int(q.loc[keep, "subject_id"].nunique()),
        "rule": "age_at_icu_admission >= 18 years and first_careunit != NICU",
    }
    q = q.loc[keep].drop(columns=["dob"]).copy()
    if (q["age_at_icu_years_uncapped"] < 18).any():
        raise RuntimeError("Adult restriction failed: age < 18 remains")
    if q["first_careunit"].astype(str).str.strip().str.upper().eq("NICU").any():
        raise RuntimeError("Adult restriction failed: NICU stay remains")
    return q, report


def validate_item_sources(root: Path) -> dict:
    f = find_file(module_path(root, "mimiciii"), ["D_ITEMS.csv.gz", "D_ITEMS.csv"])
    if f is None:
        raise FileNotFoundError("D_ITEMS not found")
    d = lower_columns(pd.read_csv(f, low_memory=False))
    d["itemid"] = pd.to_numeric(d["itemid"], errors="coerce")
    d = d.dropna(subset=["itemid"]).copy()
    d["itemid"] = d["itemid"].astype(int)
    for c in ["label", "dbsource", "linksto", "category"]:
        if c not in d:
            d[c] = ""
        d[c] = d[c].fillna("").astype(str)

    groups = {
        "vent_endpoint_procedure": sorted(VENT_ENDPOINT_PROCEDURE_IDS),
        "vent_mv_disqual_chart": sorted(VENT_MV_DISQUAL_CHART_IDS),
        "vent_mv_explicit_intubation_chart": sorted(VENT_MV_EXPLICIT_INTUBATION_CHART_IDS),
        "vent_mv_support_chart": sorted(VENT_MV_SUPPORT_CHART_IDS),
        "rrt_mv_procedure": sorted(RRT_MV_PROCEDURE_IDS),
        "rrt_mv_active_chart": sorted(RRT_MV_ACTIVE_CHART_IDS),
    }
    out = {}
    for name, ids in groups.items():
        q = d[d["itemid"].isin(ids)].copy()
        found = set(q["itemid"].astype(int))
        missing = sorted(set(ids) - found)
        rows = q[["itemid", "label", "dbsource", "linksto", "category"]].sort_values("itemid")
        out[name] = {
            "expected_itemids": ids,
            "missing_itemids": missing,
            "items": rows.to_dict(orient="records"),
        }
        if missing:
            raise RuntimeError(f"{name}: missing configured item ids in D_ITEMS: {missing}")
        bad = q[~q["dbsource"].str.strip().str.lower().eq("metavision")]
        if not bad.empty:
            raise RuntimeError(
                f"{name}: configured v2 MetaVision item has non-MetaVision dbsource: "
                f"{bad[['itemid','dbsource']].to_dict(orient='records')}"
            )
    return out


def numeric_zero_mask(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").fillna(0).eq(0)


def load_notes(root: Path, hadms: set[int]) -> tuple[pd.DataFrame, dict]:
    f = find_file(module_path(root, "mimiciii"), ["NOTEEVENTS.csv.gz", "NOTEEVENTS.csv"])
    if f is None:
        raise FileNotFoundError("NOTEEVENTS not found")

    pieces = []
    raw_category_counts: dict[str, int] = {}
    normalized_category_counts: dict[str, int] = {}
    error_rows_excluded = 0

    for chunk in read_columns(
        f,
        ["hadm_id", "charttime", "storetime", "category", "iserror", "text"],
        chunksize=100_000,
    ):
        c = lower_columns(chunk)
        c["hadm_id"] = pd.to_numeric(c["hadm_id"], errors="coerce")
        c = c[c["hadm_id"].isin(hadms)].copy()
        if c.empty:
            continue

        raw = c["category"].fillna("UNKNOWN").astype(str)
        for k, v in raw.value_counts().items():
            raw_category_counts[str(k)] = raw_category_counts.get(str(k), 0) + int(v)

        if "iserror" in c.columns:
            ok = numeric_zero_mask(c["iserror"])
            error_rows_excluded += int((~ok).sum())
            c = c[ok].copy()

        c["category"] = c["category"].fillna("UNKNOWN").astype(str).str.strip()
        for k, v in c["category"].value_counts().items():
            normalized_category_counts[str(k)] = normalized_category_counts.get(str(k), 0) + int(v)

        c = c[c["category"].isin(BEDSIDE_CATEGORIES)].copy()
        if c.empty:
            continue

        c["chart_time"] = parse_datetime(c["charttime"])
        c["store_time"] = parse_datetime(c["storetime"]) if "storetime" in c.columns else pd.NaT
        c = c.dropna(subset=["hadm_id", "chart_time", "text"]).copy()
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

        pieces.append(
            c[
                [
                    "hadm_id",
                    "note_time",
                    "chart_time",
                    "store_time",
                    "storetime_available",
                    "documentation_delay_hours",
                    "category",
                    "text",
                ]
            ]
        )

    if not pieces:
        raise RuntimeError("No eligible normalized bedside notes found")

    report = {
        "error_rows_excluded_numeric_nonzero": int(error_rows_excluded),
        "raw_selected_category_counts": {
            k: int(v)
            for k, v in raw_category_counts.items()
            if str(k).strip() in BEDSIDE_CATEGORIES
        },
        "normalized_selected_category_counts": {
            k: int(v)
            for k, v in normalized_category_counts.items()
            if k in BEDSIDE_CATEGORIES
        },
    }
    return pd.concat(pieces, ignore_index=True), report


def assign_notes_to_icu(notes: pd.DataFrame, icu: pd.DataFrame) -> pd.DataFrame:
    m = notes.merge(
        icu[["subject_id", "hadm_id", "icustay_id", "dbsource", "intime", "outtime"]],
        on="hadm_id",
        how="inner",
    )
    m = m[(m["note_time"] >= m["intime"]) & (m["note_time"] <= m["outtime"])].copy()
    m["hours_since_icu"] = (m["note_time"] - m["intime"]).dt.total_seconds() / 3600.0
    return m


def scan_chart_events(
    root: Path,
    ids: set[int],
    evidence: str,
) -> pd.DataFrame:
    f = find_file(module_path(root, "mimiciii"), ["CHARTEVENTS.csv.gz", "CHARTEVENTS.csv"])
    if f is None:
        raise FileNotFoundError("CHARTEVENTS not found")
    parts = []
    for chunk in read_columns(
        f,
        ["subject_id", "hadm_id", "icustay_id", "itemid", "charttime", "error"],
        chunksize=750_000,
    ):
        c = lower_columns(chunk)
        c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
        c = c[c["itemid"].isin(ids)].copy()
        if c.empty:
            continue
        if "error" in c.columns:
            c = c[numeric_zero_mask(c["error"])].copy()
        for col in ["subject_id", "hadm_id", "icustay_id"]:
            c[col] = pd.to_numeric(c[col], errors="coerce")
        c["event_time"] = parse_datetime(c["charttime"])
        c = c.dropna(subset=["hadm_id", "event_time", "itemid"]).copy()
        c["evidence"] = evidence
        parts.append(c[["subject_id", "hadm_id", "icustay_id", "event_time", "evidence"]])
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(
        columns=["subject_id", "hadm_id", "icustay_id", "event_time", "evidence"]
    )


def scan_procedure_events(
    root: Path,
    ids: set[int],
    evidence: str,
) -> pd.DataFrame:
    f = find_file(
        module_path(root, "mimiciii"),
        ["PROCEDUREEVENTS_MV.csv.gz", "PROCEDUREEVENTS_MV.csv"],
    )
    if f is None:
        raise FileNotFoundError("PROCEDUREEVENTS_MV not found")
    parts = []
    for chunk in read_columns(
        f,
        ["subject_id", "hadm_id", "icustay_id", "itemid", "starttime", "statusdescription"],
        chunksize=300_000,
    ):
        c = lower_columns(chunk)
        c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
        c = c[c["itemid"].isin(ids)].copy()
        if c.empty:
            continue
        if "statusdescription" in c.columns:
            bad = c["statusdescription"].fillna("").astype(str).str.lower().str.contains(
                "rewritten|cancelled", regex=True
            )
            c = c[~bad].copy()
        for col in ["subject_id", "hadm_id", "icustay_id"]:
            c[col] = pd.to_numeric(c[col], errors="coerce")
        c["event_time"] = parse_datetime(c["starttime"])
        c = c.dropna(subset=["hadm_id", "event_time", "itemid"]).copy()
        c["evidence"] = evidence
        parts.append(c[["subject_id", "hadm_id", "icustay_id", "event_time", "evidence"]])
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(
        columns=["subject_id", "hadm_id", "icustay_id", "event_time", "evidence"]
    )


def assign_events_to_icu(events: pd.DataFrame, icu: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return events.assign(hours_since_icu=pd.Series(dtype=float), dbsource=pd.Series(dtype=str))

    exact = events[events["icustay_id"].notna()].copy()
    exact["icustay_id"] = pd.to_numeric(exact["icustay_id"], errors="coerce")
    exact = exact.dropna(subset=["icustay_id"]).copy()
    exact["icustay_id"] = exact["icustay_id"].astype("int64")
    exact = exact.merge(
        icu[["icustay_id", "hadm_id", "subject_id", "dbsource", "intime", "outtime"]],
        on="icustay_id",
        how="inner",
        suffixes=("_event", "_icu"),
    )
    exact = exact[
        (exact["event_time"] >= exact["intime"])
        & (exact["event_time"] <= exact["outtime"])
    ].copy()
    if not exact.empty:
        exact["hadm_id"] = pd.to_numeric(exact["hadm_id_icu"], errors="coerce")
        exact["subject_id"] = pd.to_numeric(exact["subject_id_icu"], errors="coerce")

    missing = events[events["icustay_id"].isna()].copy()
    if not missing.empty:
        missing = missing.merge(
            icu[["subject_id", "hadm_id", "icustay_id", "dbsource", "intime", "outtime"]],
            on="hadm_id",
            how="inner",
            suffixes=("_event", "_icu"),
        )
        missing = missing[
            (missing["event_time"] >= missing["intime"])
            & (missing["event_time"] <= missing["outtime"])
        ].copy()
        missing["subject_id"] = pd.to_numeric(missing["subject_id_icu"], errors="coerce")
        missing["icustay_id"] = pd.to_numeric(missing["icustay_id_icu"], errors="coerce")

    keep = ["subject_id", "hadm_id", "icustay_id", "dbsource", "intime", "outtime", "event_time", "evidence"]
    frames = []
    if not exact.empty:
        frames.append(exact[keep])
    if not missing.empty:
        frames.append(missing[keep])
    if not frames:
        return pd.DataFrame(columns=keep + ["hours_since_icu"])
    m = pd.concat(frames, ignore_index=True).drop_duplicates(
        ["icustay_id", "event_time", "evidence"]
    )
    m["hours_since_icu"] = (m["event_time"] - m["intime"]).dt.total_seconds() / 3600.0
    return m


def load_deaths(root: Path, icu: pd.DataFrame) -> pd.DataFrame:
    f = find_file(module_path(root, "mimiciii"), ["ADMISSIONS.csv.gz", "ADMISSIONS.csv"])
    if f is None:
        raise FileNotFoundError("ADMISSIONS not found")
    d = lower_columns(
        pd.read_csv(
            f,
            usecols=lambda c: c.lower() in {"subject_id", "hadm_id", "deathtime"},
            low_memory=False,
        )
    )
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
    m["evidence"] = "icu_death"
    return m[
        ["subject_id", "hadm_id", "icustay_id", "dbsource", "intime", "outtime", "event_time", "evidence", "hours_since_icu"]
    ]


def first_time(events: pd.DataFrame, evidence_names: set[str]) -> pd.Series:
    if events.empty:
        return pd.Series(dtype="datetime64[ns]")
    q = events[events["evidence"].isin(evidence_names)].copy()
    if q.empty:
        return pd.Series(dtype="datetime64[ns]")
    return (
        q.sort_values("event_time")
        .groupby("icustay_id", as_index=False)
        .first()
        .set_index("icustay_id")["event_time"]
    )


def build_outcome(
    outcome: str,
    icu: pd.DataFrame,
    note_icu: pd.DataFrame,
    endpoint_times: pd.Series,
    disqualifying_times: pd.Series,
    local_root: Path,
    output_name: str | None = None,
    language_key: str | None = None,
) -> dict:
    if outcome in {"invasive_ventilation", "renal_replacement_therapy"}:
        risk = icu[icu["dbsource"].eq("metavision")].copy()
        source_rule = "metavision_only"
    else:
        risk = icu.copy()
        source_rule = "all_sources"

    risk["landmark_time"] = risk["intime"] + pd.to_timedelta(LANDMARK_H, unit="h")
    risk["horizon_end"] = risk["landmark_time"] + pd.to_timedelta(HORIZON_H, unit="h")
    risk = risk[risk["outtime"] > risk["landmark_time"]].copy()

    risk["first_endpoint_time"] = risk["icustay_id"].map(endpoint_times)
    risk["first_disqualifying_time"] = risk["icustay_id"].map(disqualifying_times)

    if outcome == "icu_death":
        risk = risk[
            risk["first_endpoint_time"].isna()
            | (risk["first_endpoint_time"] > risk["landmark_time"])
        ].copy()
    else:
        risk = risk[
            risk["first_disqualifying_time"].isna()
            | (risk["first_disqualifying_time"] > risk["landmark_time"])
        ].copy()

    risk["is_case"] = (
        risk["first_endpoint_time"].notna()
        & (risk["first_endpoint_time"] > risk["landmark_time"])
        & (risk["first_endpoint_time"] <= risk["horizon_end"])
    )

    if outcome == "icu_death":
        risk["fully_observed_control"] = (
            ~risk["is_case"]
            & (risk["outtime"] >= risk["horizon_end"])
            & (
                risk["first_endpoint_time"].isna()
                | (risk["first_endpoint_time"] > risk["horizon_end"])
            )
        )
    else:
        risk["fully_observed_control"] = (
            ~risk["is_case"]
            & (risk["outtime"] >= risk["horizon_end"])
            & (
                risk["first_disqualifying_time"].isna()
                | (risk["first_disqualifying_time"] > risk["horizon_end"])
            )
        )

    pop = risk[risk["is_case"] | risk["fully_observed_control"]].copy()
    pop["label"] = pop["is_case"].astype(int)
    pop["event_time"] = pop["first_endpoint_time"].where(pop["is_case"])

    candidate = note_icu[
        (note_icu["hours_since_icu"] >= LANDMARK_H - 12.0)
        & (note_icu["hours_since_icu"] <= LANDMARK_H)
    ].copy()
    candidate = candidate[candidate["icustay_id"].isin(set(pop["icustay_id"]))].copy()

    note_cols = [
        "icustay_id",
        "note_time",
        "hours_since_icu",
        "category",
        "storetime_available",
        "documentation_delay_hours",
        "text",
    ]
    last_notes = (
        candidate.sort_values(["icustay_id", "note_time"])
        .groupby("icustay_id", as_index=False)
        .last()[note_cols]
    )

    pop = pop.merge(last_notes, on="icustay_id", how="left")
    pop["has_note"] = pop["note_time"].notna()
    pop["note_age_at_landmark_hours"] = (
        pop["landmark_time"] - pop["note_time"]
    ).dt.total_seconds() / 3600.0
    case_namespace = output_name or outcome
    pop["case_id"] = [stable_case_id(case_namespace, x) for x in pop["icustay_id"]]
    if pop["case_id"].duplicated().any():
        raise RuntimeError(f"{outcome}: duplicate case ids")

    rx = compile_rx(LANGUAGE_PATTERNS[language_key or outcome])
    pop["direct_outcome_language_present"] = False
    note_mask = pop["has_note"]
    pop.loc[note_mask, "direct_outcome_language_present"] = (
        pop.loc[note_mask, "text"].astype(str).str.contains(rx, regex=True, na=False)
    )

    outdir = local_root / (output_name or outcome)
    outdir.mkdir(parents=True, exist_ok=True)

    index_cols = [
        "case_id",
        "subject_id",
        "hadm_id",
        "icustay_id",
        "label",
        "landmark_time",
        "horizon_end",
        "event_time",
        "outtime",
        "dbsource",
        "first_careunit",
        "age_at_icu_years_uncapped",
        "has_note",
        "note_time",
        "hours_since_icu",
        "note_age_at_landmark_hours",
        "category",
        "storetime_available",
        "documentation_delay_hours",
        "direct_outcome_language_present",
    ]
    pop[index_cols].to_csv(outdir / "population_index_local.csv", index=False)

    with (outdir / "cases.jsonl").open("w", encoding="utf-8") as handle:
        for row in pop[pop["has_note"]].itertuples(index=False):
            rec = {
                "case_id": str(row.case_id),
                "synthetic_only": False,
                "local_only": True,
                "model_state": {"clinical_note": str(row.text)},
                "metadata": {
                    "analysis": "population_landmark12_v2_1_corrected",
                    "outcome": outcome,
                    "label": int(row.label),
                    "note_available": True,
                    "note_category": str(row.category),
                    "landmark_hours": LANDMARK_H,
                    "prediction_horizon_hours": HORIZON_H,
                    "hours_since_icu_at_note": round(float(row.hours_since_icu), 3),
                    "note_age_at_landmark_hours": round(float(row.note_age_at_landmark_hours), 3),
                    "note_availability_basis": (
                        "max(charttime, storetime)"
                        if bool(row.storetime_available)
                        else "charttime_fallback"
                    ),
                    "documentation_delay_hours": (
                        round(float(row.documentation_delay_hours), 3)
                        if pd.notna(row.documentation_delay_hours)
                        else None
                    ),
                    "direct_outcome_language_present": bool(row.direct_outcome_language_present),
                    "note_characters": len(str(row.text)),
                },
                "questions": SEMANTIC_CONSTRUCTS,
                "gold": None,
            }
            handle.write(json.dumps(rec, ensure_ascii=False) + "\n")

    n = len(pop)
    cases = int(pop["label"].sum())
    controls = n - cases
    with_note = pop[pop["has_note"]].copy()
    case_rows = pop[pop["label"].eq(1)]
    control_rows = pop[pop["label"].eq(0)]
    cases_before_horizon_discharge = int(
        (case_rows["outtime"] < case_rows["horizon_end"]).sum()
    )

    return {
        "source_rule": source_rule,
        "rows": int(n),
        "unique_patients": int(pop["subject_id"].nunique()),
        "cases": cases,
        "controls": controls,
        "prevalence": float(cases / n) if n else None,
        "note_available_rows": int(len(with_note)),
        "note_coverage": float(pop["has_note"].mean()) if n else None,
        "case_note_coverage": float(case_rows["has_note"].mean()) if len(case_rows) else None,
        "control_note_coverage": float(control_rows["has_note"].mean()) if len(control_rows) else None,
        "selected_note_category_counts": {
            str(k): int(v)
            for k, v in with_note["category"].value_counts(dropna=False).to_dict().items()
        },
        "direct_outcome_language_note_n": int(with_note["direct_outcome_language_present"].sum()),
        "direct_outcome_language_note_fraction": (
            float(with_note["direct_outcome_language_present"].mean()) if len(with_note) else None
        ),
        "case_direct_outcome_language_fraction": (
            float(case_rows.loc[case_rows["has_note"], "direct_outcome_language_present"].mean())
            if int(case_rows["has_note"].sum()) else None
        ),
        "control_direct_outcome_language_fraction": (
            float(control_rows.loc[control_rows["has_note"], "direct_outcome_language_present"].mean())
            if int(control_rows["has_note"].sum()) else None
        ),
        "cases_discharged_before_horizon_end_n": cases_before_horizon_discharge,
        "local_index": str(outdir / "population_index_local.csv"),
        "local_cases": str(outdir / "cases.jsonl"),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Build corrected adult v2.1 12-hour landmark cohorts.")
    ap.add_argument("--root", required=True)
    ap.add_argument("--local-output-root", required=True)
    ap.add_argument("--manifest", required=True)
    args = ap.parse_args()

    root = resolve_root(args.root)
    local_root = Path(args.local_output_root).expanduser().resolve()
    manifest_path = Path(args.manifest).expanduser().resolve()
    local_root.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    update_progress(current=1, total=6, phase="dictionary", message="Validating source-compatible v2.1 endpoint item mappings", unit="stage")
    item_validation = validate_item_sources(root)

    update_progress(current=2, total=6, phase="source", message="Loading ICU stays and corrected endpoint evidence", unit="stage")
    icu = load_icustays(root)
    icu, adult_eligibility = restrict_to_adults(root, icu)

    vent_proc = scan_procedure_events(root, VENT_ENDPOINT_PROCEDURE_IDS, "vent_endpoint_procedure")
    vent_explicit_chart = scan_chart_events(
        root, VENT_MV_EXPLICIT_INTUBATION_CHART_IDS, "vent_explicit_intubation_chart"
    )
    vent_support_chart = scan_chart_events(
        root, VENT_MV_SUPPORT_CHART_IDS, "vent_support_chart"
    )
    vent_events = assign_events_to_icu(
        pd.concat([vent_proc, vent_explicit_chart, vent_support_chart], ignore_index=True),
        icu,
    )

    rrt_proc = scan_procedure_events(root, RRT_MV_PROCEDURE_IDS, "rrt_endpoint_procedure")
    rrt_chart = scan_chart_events(root, RRT_MV_ACTIVE_CHART_IDS, "rrt_endpoint_chart")
    rrt_events = assign_events_to_icu(pd.concat([rrt_proc, rrt_chart], ignore_index=True), icu)

    death_events = load_deaths(root, icu)

    update_progress(current=3, total=6, phase="notes", message="Loading normalized prospective bedside notes without outcome-based deletion", unit="stage")
    notes, note_hygiene = load_notes(root, set(icu["hadm_id"].astype(int)))
    note_icu = assign_notes_to_icu(notes, icu)

    update_progress(current=4, total=6, phase="cohorts", message="Building corrected source-compatible landmark cohorts", unit="stage")

    vent_endpoint = first_time(vent_events, {"vent_endpoint_procedure"})
    vent_explicit_endpoint = first_time(
        vent_events, {"vent_endpoint_procedure", "vent_explicit_intubation_chart"}
    )
    vent_any_support_endpoint = first_time(
        vent_events,
        {"vent_endpoint_procedure", "vent_explicit_intubation_chart", "vent_support_chart"},
    )
    vent_disqual = vent_any_support_endpoint

    rrt_endpoint = first_time(rrt_events, {"rrt_endpoint_procedure", "rrt_endpoint_chart"})
    rrt_disqual = first_time(rrt_events, {"rrt_endpoint_procedure", "rrt_endpoint_chart"})

    death_endpoint = first_time(death_events, {"icu_death"})

    outcomes = {
        "invasive_ventilation": build_outcome(
            "invasive_ventilation", icu, note_icu, vent_endpoint, vent_disqual, local_root
        ),
        "renal_replacement_therapy": build_outcome(
            "renal_replacement_therapy", icu, note_icu, rrt_endpoint, rrt_disqual, local_root
        ),
        "icu_death": build_outcome(
            "icu_death", icu, note_icu, death_endpoint, death_endpoint, local_root
        ),
    }

    sensitivity_outcomes = {
        "invasive_ventilation_explicit_evidence": build_outcome(
            "invasive_ventilation",
            icu,
            note_icu,
            vent_explicit_endpoint,
            vent_explicit_endpoint,
            local_root,
            output_name="invasive_ventilation_explicit_evidence_sensitivity",
            language_key="invasive_ventilation",
        ),
        "invasive_ventilation_any_support": build_outcome(
            "invasive_ventilation",
            icu,
            note_icu,
            vent_any_support_endpoint,
            vent_any_support_endpoint,
            local_root,
            output_name="invasive_ventilation_any_support_sensitivity",
            language_key="invasive_ventilation",
        ),
    }

    update_progress(current=5, total=6, phase="checks", message="Checking v2.1 cohort invariants and note-selection independence", unit="stage")
    for outcome, info in {**outcomes, **sensitivity_outcomes}.items():
        if info["rows"] <= 0 or info["cases"] <= 0 or info["controls"] <= 0:
            raise RuntimeError(f"{outcome}: degenerate corrected cohort")
        if info["note_available_rows"] <= 0:
            raise RuntimeError(f"{outcome}: no notes after corrected hygiene")

    report = {
        "analysis": "Corrected adult 12-hour landmark cohort build v2.1",
        "protocol": "docs/06_POSTREVIEW_V2_1_CORRECTIONS.md",
        "local_only": True,
        "contains_note_text": False,
        "contains_patient_identifiers": False,
        "contains_row_level_data": False,
        "model_inference_performed": False,
        "landmark_hours": LANDMARK_H,
        "prediction_horizon_hours": HORIZON_H,
        "adult_eligibility": adult_eligibility,
        "item_source_validation": item_validation,
        "note_hygiene": note_hygiene,
        "outcomes": outcomes,
        "sensitivity_outcomes": sensitivity_outcomes,
        "guardrails": [
            "No predictive model was fit or scored.",
            "All primary cohorts are restricted to age >=18 at ICU admission and exclude NICU first-careunit stays.",
            "Ventilation and RRT primary risk sets are MetaVision-only.",
            "ICU dbsource is retained only in local cohort indices for provenance and is not a v2 predictor.",
            "Notes are selected before any outcome-language sensitivity; no outcome-language deletion changes note availability.",
            "All v1 local and aggregate outputs remain unchanged.",
        ],
    }

    update_progress(current=6, total=6, phase="done", message="Completed corrected adult v2.1 landmark cohort build", unit="stage")
    manifest_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
