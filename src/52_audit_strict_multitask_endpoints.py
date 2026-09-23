from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from common import find_file, lower_columns, module_path, parse_datetime, read_columns, resolve_root
from runrelay_progress import update_progress


BEDSIDE_CATEGORIES = {
    "Physician", "Consult", "Nursing", "Nursing/other", "Respiratory", "General",
}
WINDOWS_HOURS = [6, 12, 24]

VENT_NOTE_PATTERNS = [
    r"\bintubat\w*\b",
    r"\bendotracheal\b",
    r"\bmechanical ventilat\w*\b",
    r"\bventilator\b",
    r"\bETT\b",
]
RRT_NOTE_PATTERNS = [
    r"\bdialysis\b",
    r"\bhemodialysis\b",
    r"\bhaemodialysis\b",
    r"\bCVVH\w*\b",
    r"\bCRRT\b",
    r"\bhemofiltration\b",
    r"\bhaemofiltration\b",
    r"\brenal replacement\b",
]
DEATH_DIRECT_PATTERNS = [
    r"\bdying\b",
    r"\bdeath\b",
    r"\bdeceased\b",
    r"\bcomfort care\b",
    r"\bcomfort measures\b",
    r"\bCMO\b",
    r"\bwithdraw\w* (?:care|support|treatment)\b",
    r"\bhospice\b",
]
DEATH_BROAD_PATTERNS = DEATH_DIRECT_PATTERNS + [
    r"\bDNR\b",
    r"\bDNI\b",
    r"\bdo not resuscitate\b",
    r"\bdo not intubate\b",
    r"\bgoals? of care\b",
]


def norm_label(x: object) -> str:
    return re.sub(r"\s+", " ", str(x).strip()).lower()


def qstats(x: pd.Series) -> dict:
    v = pd.to_numeric(x, errors="coerce").dropna()
    if v.empty:
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


def load_d_items(root: Path) -> pd.DataFrame:
    f = find_file(module_path(root, "mimiciii"), ["D_ITEMS.csv.gz", "D_ITEMS.csv"])
    if f is None:
        raise FileNotFoundError("D_ITEMS not found")
    d = lower_columns(pd.read_csv(f, low_memory=False))
    keep = [c for c in [
        "itemid", "label", "abbreviation", "dbsource", "linksto", "category"
    ] if c in d.columns]
    d = d[keep].copy()
    d["itemid"] = pd.to_numeric(d["itemid"], errors="coerce")
    d = d.dropna(subset=["itemid"]).copy()
    d["itemid"] = d["itemid"].astype("int64")
    for c in ["label", "dbsource", "linksto", "category"]:
        if c not in d:
            d[c] = ""
        d[c] = d[c].fillna("").astype(str)
    d["label_norm"] = d["label"].map(norm_label)
    d["linksto_norm"] = d["linksto"].str.lower()
    d["category_norm"] = d["category"].map(norm_label)
    return d


def discover_curated_items(d: pd.DataFrame) -> tuple[dict[str, set[int]], dict]:
    # Ventilation primary evidence is deliberately narrow:
    # 1) explicit MetaVision Intubation procedure,
    # 2) explicit/intubation-completion chart events rather than generic ventilator settings.
    vent_proc = d[
        (d["linksto_norm"] == "procedureevents_mv")
        & (d["label_norm"] == "intubation")
    ].copy()

    vent_chart_exact = {
        "intubation date",
        "tube secured (intubation)",
        "tracheal confirmation (intubation)",
        "ett depth (intubation)",
        "ett size (intubation)",
        "number of attempts (intubation)",
        "verification of (intubation)",
    }
    vent_chart = d[
        (d["linksto_norm"] == "chartevents")
        & d["label_norm"].isin(vent_chart_exact)
    ].copy()

    # Support evidence is used only to screen out prevalent ventilation and audit
    # temporal concordance; it is not itself the strict initiation endpoint.
    vent_support_rx = re.compile(
        r"^(ventilator mode|vent mode|tidal volume \(set\)|tidal volume set|"
        r"respiratory rate \(set\)|respiratory rate set|set respiratory rate|"
        r"pressure control.*set|pressure support.*set)$",
        flags=re.IGNORECASE,
    )
    vent_support = d[
        (d["linksto_norm"] == "chartevents")
        & d["label_norm"].str.match(vent_support_rx, na=False)
    ].copy()

    # RRT procedure-only tier: actual named therapies, excluding catheter placement,
    # filter changes, access documentation, history flags, and fluid/output bookkeeping.
    rrt_proc_labels = {
        "hemodialysis",
        "dialysis - crrt",
        "dialysis - cvvhd",
        "peritoneal dialysis",
        "dialysis - cvvhdf",
        "dialysis - scuf",
    }
    rrt_proc = d[
        (d["linksto_norm"] == "procedureevents_mv")
        & d["label_norm"].isin(rrt_proc_labels)
    ].copy()

    # Active-therapy supporting evidence can broaden across CareVue/MetaVision,
    # but is kept separate from the procedure-only definition.
    rrt_chart_labels = {
        "crrt mode",
        "hemodialysis output",
        "dialysis type",
    }
    rrt_chart = d[
        (d["linksto_norm"] == "chartevents")
        & d["label_norm"].isin(rrt_chart_labels)
    ].copy()

    positive_rrt = re.compile(r"(?:hemo)?dialysis|cvvh|crrt", flags=re.IGNORECASE)
    exclude_rrt = re.compile(
        r"catheter|access|site|machine|patient|filter change|tip cultured|"
        r"dressing|x-ray|fluid|calcium|citrate|kcl|flush|indwelling",
        flags=re.IGNORECASE,
    )
    rrt_output = d[
        (d["linksto_norm"] == "outputevents")
        & d["label"].str.contains(positive_rrt, regex=True, na=False)
        & ~d["label"].str.contains(exclude_rrt, regex=True, na=False)
    ].copy()

    groups = {
        "vent_procedure": set(vent_proc["itemid"].astype(int)),
        "vent_explicit_chart": set(vent_chart["itemid"].astype(int)),
        "vent_support": set(vent_support["itemid"].astype(int)),
        "rrt_procedure": set(rrt_proc["itemid"].astype(int)),
        "rrt_active_chart": set(rrt_chart["itemid"].astype(int)),
        "rrt_active_output": set(rrt_output["itemid"].astype(int)),
    }

    meta = {}
    for name, ids in groups.items():
        g = d[d["itemid"].isin(ids)].copy()
        meta[name] = {
            "n_itemids": int(len(ids)),
            "items": g.sort_values(["linksto_norm", "itemid"])[
                ["itemid", "label", "dbsource", "linksto", "category"]
            ].to_dict(orient="records"),
        }
    return groups, meta


def scan_events(root: Path, groups: dict[str, set[int]]) -> pd.DataFrame:
    pieces: list[pd.DataFrame] = []

    chart_map: dict[int, list[str]] = {}
    for evidence in ["vent_explicit_chart", "vent_support", "rrt_active_chart"]:
        for itemid in groups[evidence]:
            chart_map.setdefault(int(itemid), []).append(evidence)
    chart_ids = set(chart_map)

    chart = find_file(module_path(root, "mimiciii"), ["CHARTEVENTS.csv.gz", "CHARTEVENTS.csv"])
    if chart is not None and chart_ids:
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
            c = c.dropna(subset=["hadm_id", "itemid", "event_time"])
            for evidence, ids in [
                ("vent_explicit_chart", groups["vent_explicit_chart"]),
                ("vent_support", groups["vent_support"]),
                ("rrt_active_chart", groups["rrt_active_chart"]),
            ]:
                x = c[c["itemid"].isin(ids)].copy()
                if not x.empty:
                    x["evidence"] = evidence
                    x["source"] = "chartevents"
                    pieces.append(x[[
                        "subject_id", "hadm_id", "icustay_id", "itemid",
                        "event_time", "evidence", "source"
                    ]])

    proc_map: dict[int, list[str]] = {}
    for evidence in ["vent_procedure", "rrt_procedure"]:
        for itemid in groups[evidence]:
            proc_map.setdefault(int(itemid), []).append(evidence)
    proc_ids = set(proc_map)

    proc = find_file(
        module_path(root, "mimiciii"),
        ["PROCEDUREEVENTS_MV.csv.gz", "PROCEDUREEVENTS_MV.csv"],
    )
    if proc is not None and proc_ids:
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
            c = c.dropna(subset=["hadm_id", "itemid", "event_time"])
            for evidence, ids in [
                ("vent_procedure", groups["vent_procedure"]),
                ("rrt_procedure", groups["rrt_procedure"]),
            ]:
                x = c[c["itemid"].isin(ids)].copy()
                if not x.empty:
                    x["evidence"] = evidence
                    x["source"] = "procedureevents_mv"
                    pieces.append(x[[
                        "subject_id", "hadm_id", "icustay_id", "itemid",
                        "event_time", "evidence", "source"
                    ]])

    output_ids = groups["rrt_active_output"]
    output_f = find_file(module_path(root, "mimiciii"), ["OUTPUTEVENTS.csv.gz", "OUTPUTEVENTS.csv"])
    if output_f is not None and output_ids:
        for chunk in read_columns(
            output_f,
            ["subject_id", "hadm_id", "icustay_id", "itemid", "charttime", "iserror"],
            chunksize=500_000,
        ):
            c = lower_columns(chunk)
            c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
            c = c[c["itemid"].isin(output_ids)]
            if c.empty:
                continue
            if "iserror" in c:
                c = c[c["iserror"].fillna(0).astype(str) != "1"]
            for col in ["subject_id", "hadm_id", "icustay_id"]:
                c[col] = pd.to_numeric(c[col], errors="coerce")
            c["event_time"] = parse_datetime(c["charttime"])
            c = c.dropna(subset=["hadm_id", "itemid", "event_time"])
            c["evidence"] = "rrt_active_output"
            c["source"] = "outputevents"
            pieces.append(c[[
                "subject_id", "hadm_id", "icustay_id", "itemid",
                "event_time", "evidence", "source"
            ]])

    if not pieces:
        return pd.DataFrame(columns=[
            "subject_id", "hadm_id", "icustay_id", "itemid",
            "event_time", "evidence", "source"
        ])
    return pd.concat(pieces, ignore_index=True)


def assign_events_to_icu(events: pd.DataFrame, icu: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame()
    merged = events.merge(
        icu[["subject_id", "hadm_id", "icustay_id", "intime", "outtime", "dbsource"]],
        on="hadm_id",
        how="inner",
        suffixes=("_event", "_icu"),
    )
    merged = merged[
        (merged["event_time"] >= merged["intime"])
        & (merged["event_time"] <= merged["outtime"])
    ].copy()
    if merged.empty:
        return merged
    merged["hours_since_icu"] = (
        merged["event_time"] - merged["intime"]
    ).dt.total_seconds() / 3600.0
    merged["subject_id"] = pd.to_numeric(merged["subject_id_icu"], errors="coerce")
    merged["icustay_id"] = pd.to_numeric(merged["icustay_id_icu"], errors="coerce")
    return merged


def build_incident_tier(
    assigned: pd.DataFrame,
    tier_name: str,
    endpoint_evidence: set[str],
    prevalence_evidence: set[str],
    washout_h: float,
) -> tuple[pd.DataFrame, dict]:
    relevant = assigned[assigned["evidence"].isin(endpoint_evidence | prevalence_evidence)].copy()
    if relevant.empty:
        return pd.DataFrame(), {
            "tier": tier_name,
            "incident_unique_subjects": 0,
        }

    early = relevant[
        relevant["evidence"].isin(prevalence_evidence)
        & (relevant["hours_since_icu"] < washout_h)
    ]
    early_stays = set(pd.to_numeric(early["icustay_id"], errors="coerce").dropna().astype(int))

    endpoint = relevant[
        relevant["evidence"].isin(endpoint_evidence)
        & (relevant["hours_since_icu"] >= washout_h)
    ].copy()
    if endpoint.empty:
        return pd.DataFrame(), {
            "tier": tier_name,
            "icu_stays_with_prevalent_evidence_in_washout": int(len(early_stays)),
            "incident_unique_subjects": 0,
        }

    endpoint["icustay_id_int"] = pd.to_numeric(endpoint["icustay_id"], errors="coerce")
    endpoint = endpoint[
        ~endpoint["icustay_id_int"].fillna(-1).astype(int).isin(early_stays)
    ].copy()

    first_stay = (
        endpoint.sort_values("event_time")
        .groupby("icustay_id_int", as_index=False)
        .first()
    )
    first_patient = (
        first_stay.sort_values("event_time")
        .groupby("subject_id", as_index=False)
        .first()
    )
    first_patient["candidate"] = tier_name

    report = {
        "tier": tier_name,
        "endpoint_evidence": sorted(endpoint_evidence),
        "prevalence_screen_evidence": sorted(prevalence_evidence),
        "washout_hours": float(washout_h),
        "icu_stays_with_prevalent_evidence_in_washout": int(len(early_stays)),
        "incident_icu_stays_before_patient_dedup": int(len(first_stay)),
        "incident_unique_subjects": int(len(first_patient)),
        "dbsource_counts": {
            str(k): int(v)
            for k, v in first_patient["dbsource"].value_counts(dropna=False).to_dict().items()
        },
        "hours_from_icu_to_event": qstats(first_patient["hours_since_icu"]),
        "source_counts": {
            str(k): int(v)
            for k, v in first_patient["source"].value_counts().to_dict().items()
        },
    }
    return first_patient[[
        "subject_id", "hadm_id", "icustay_id", "intime", "outtime",
        "dbsource", "event_time", "hours_since_icu", "candidate", "source",
    ]], report


def load_death_incident(root: Path, icu: pd.DataFrame, washout_h: float) -> tuple[pd.DataFrame, dict]:
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
    d = d.dropna(subset=["subject_id", "hadm_id", "event_time"])

    m = d.merge(
        icu[["subject_id", "hadm_id", "icustay_id", "intime", "outtime", "dbsource"]],
        on=["subject_id", "hadm_id"],
        how="inner",
    )
    m = m[
        (m["event_time"] >= m["intime"])
        & (m["event_time"] <= m["outtime"])
    ].copy()
    m["hours_since_icu"] = (
        m["event_time"] - m["intime"]
    ).dt.total_seconds() / 3600.0
    m = m[m["hours_since_icu"] >= washout_h].copy()
    m = (
        m.sort_values("event_time")
        .groupby("subject_id", as_index=False)
        .first()
    )
    m["candidate"] = "icu_death"
    m["source"] = "admissions_deathtime"
    return m[[
        "subject_id", "hadm_id", "icustay_id", "intime", "outtime",
        "dbsource", "event_time", "hours_since_icu", "candidate", "source",
    ]], {
        "tier": "icu_death",
        "washout_hours": float(washout_h),
        "incident_unique_subjects": int(len(m)),
        "dbsource_counts": {
            str(k): int(v)
            for k, v in m["dbsource"].value_counts(dropna=False).to_dict().items()
        },
        "hours_from_icu_to_event": qstats(m["hours_since_icu"]),
    }


def first_evidence_per_stay(assigned: pd.DataFrame, evidence: set[str]) -> pd.DataFrame:
    x = assigned[assigned["evidence"].isin(evidence)].copy()
    if x.empty:
        return pd.DataFrame(columns=["icustay_id", "event_time"])
    return (
        x.sort_values("event_time")
        .groupby("icustay_id", as_index=False)
        .first()[["icustay_id", "event_time"]]
    )


def concordance_report(
    assigned: pd.DataFrame,
    anchor_evidence: set[str],
    comparator_evidence: set[str],
    anchor_name: str,
    comparator_name: str,
) -> dict:
    a = first_evidence_per_stay(assigned, anchor_evidence).rename(
        columns={"event_time": "anchor_time"}
    )
    b = first_evidence_per_stay(assigned, comparator_evidence).rename(
        columns={"event_time": "comparator_time"}
    )
    if a.empty or b.empty:
        return {
            "anchor": anchor_name,
            "comparator": comparator_name,
            "stays_with_both": 0,
        }
    m = a.merge(b, on="icustay_id", how="inner")
    if m.empty:
        return {
            "anchor": anchor_name,
            "comparator": comparator_name,
            "stays_with_both": 0,
        }
    delta = (m["comparator_time"] - m["anchor_time"]).dt.total_seconds() / 3600.0
    return {
        "anchor": anchor_name,
        "comparator": comparator_name,
        "stays_with_both": int(len(m)),
        "comparator_minus_anchor_hours": qstats(delta),
        "absolute_within_1h": int((delta.abs() <= 1).sum()),
        "absolute_within_6h": int((delta.abs() <= 6).sum()),
        "absolute_within_12h": int((delta.abs() <= 12).sum()),
        "within_1h_pct": float(100 * (delta.abs() <= 1).mean()),
        "within_6h_pct": float(100 * (delta.abs() <= 6).mean()),
        "within_12h_pct": float(100 * (delta.abs() <= 12).mean()),
    }


def compile_rx(patterns: list[str]) -> re.Pattern:
    return re.compile("|".join(f"(?:{p})" for p in patterns), flags=re.IGNORECASE)


def scan_notes(root: Path, hadms: set[int]) -> tuple[pd.DataFrame, dict]:
    f = find_file(module_path(root, "mimiciii"), ["NOTEEVENTS.csv.gz", "NOTEEVENTS.csv"])
    if f is None:
        raise FileNotFoundError("NOTEEVENTS not found")

    pieces = []
    source_rows = 0
    eligible = 0
    store = 0
    for chunk in read_columns(
        f,
        ["hadm_id", "charttime", "storetime", "category", "iserror", "text"],
        chunksize=100_000,
    ):
        source_rows += len(chunk)
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
        c["note_time"] = c["chart_time"]
        has_store = c["store_time"].notna()
        c.loc[has_store, "note_time"] = c.loc[
            has_store, ["chart_time", "store_time"]
        ].max(axis=1)
        c["storetime_available"] = has_store
        eligible += len(c)
        store += int(has_store.sum())
        pieces.append(c[[
            "hadm_id", "note_time", "category", "text", "storetime_available"
        ]])
    notes = pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()
    return notes, {
        "source_note_rows_scanned": int(source_rows),
        "eligible_bedside_note_rows_in_candidate_admissions": int(eligible),
        "storetime_available_fraction": float(store / eligible) if eligible else None,
    }


def note_coverage_for_events(
    events: pd.DataFrame,
    notes: pd.DataFrame,
    direct_patterns: list[str],
    broad_patterns: list[str] | None = None,
) -> dict:
    if events.empty or notes.empty:
        return {}
    direct_rx = compile_rx(direct_patterns)
    broad_rx = compile_rx(broad_patterns or direct_patterns)

    m = events.merge(notes, on="hadm_id", how="left")
    m = m[
        (m["note_time"] >= m["intime"])
        & (m["note_time"] < m["event_time"])
    ].copy()
    m["hours_before_event"] = (
        m["event_time"] - m["note_time"]
    ).dt.total_seconds() / 3600.0
    m["direct_language"] = m["text"].fillna("").astype(str).str.contains(
        direct_rx, regex=True, na=False
    )
    m["broad_language"] = m["text"].fillna("").astype(str).str.contains(
        broad_rx, regex=True, na=False
    )

    out = {}
    n_events = int(events["subject_id"].nunique())
    for w in WINDOWS_HOURS:
        g = m[
            (m["hours_before_event"] > 0)
            & (m["hours_before_event"] <= w)
        ].copy()
        any_subjects = int(g["subject_id"].nunique())
        direct_clean = int(g[~g["direct_language"]]["subject_id"].nunique())
        broad_clean = int(g[~g["broad_language"]]["subject_id"].nunique())
        out[str(w)] = {
            "window_hours": int(w),
            "incident_subjects": n_events,
            "subjects_with_any_prospective_note": any_subjects,
            "coverage_any_pct": float(100 * any_subjects / n_events) if n_events else None,
            "subjects_with_at_least_one_direct_language_clean_note": direct_clean,
            "coverage_direct_language_clean_pct": (
                float(100 * direct_clean / n_events) if n_events else None
            ),
            "subjects_with_at_least_one_broad_language_clean_note": broad_clean,
            "coverage_broad_language_clean_pct": (
                float(100 * broad_clean / n_events) if n_events else None
            ),
            "notes_in_window": int(len(g)),
            "direct_language_note_pct": (
                float(100 * g["direct_language"].mean()) if len(g) else None
            ),
            "broad_language_note_pct": (
                float(100 * g["broad_language"].mean()) if len(g) else None
            ),
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Strict endpoint-definition audit for multi-outcome prospective semantic "
            "benchmarking in MIMIC-III. Produces aggregate metadata only."
        )
    )
    ap.add_argument("--root", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--washout-hours", type=float, default=6.0)
    args = ap.parse_args()

    root = resolve_root(args.root)
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    update_progress(current=1, total=6, phase="dictionary", message="Loading ICU stays and curating strict D_ITEMS evidence", unit="stage")
    icu = load_icustays(root)
    d_items = load_d_items(root)
    groups, item_meta = discover_curated_items(d_items)

    update_progress(current=2, total=6, phase="event_scan", message="Scanning curated ventilation and RRT evidence", unit="stage")
    events = scan_events(root, groups)
    assigned = assign_events_to_icu(events, icu)

    update_progress(current=3, total=6, phase="incident_tiers", message="Building conservative incident endpoint tiers", unit="stage")
    vent_proc, vent_proc_report = build_incident_tier(
        assigned,
        "invasive_ventilation_procedure_only",
        {"vent_procedure"},
        {"vent_procedure", "vent_explicit_chart", "vent_support"},
        args.washout_hours,
    )
    vent_explicit, vent_explicit_report = build_incident_tier(
        assigned,
        "invasive_ventilation_explicit_intubation",
        {"vent_procedure", "vent_explicit_chart"},
        {"vent_procedure", "vent_explicit_chart", "vent_support"},
        args.washout_hours,
    )
    rrt_proc, rrt_proc_report = build_incident_tier(
        assigned,
        "rrt_procedure_only",
        {"rrt_procedure"},
        {"rrt_procedure", "rrt_active_chart", "rrt_active_output"},
        args.washout_hours,
    )
    rrt_active, rrt_active_report = build_incident_tier(
        assigned,
        "rrt_active_therapy",
        {"rrt_procedure", "rrt_active_chart", "rrt_active_output"},
        {"rrt_procedure", "rrt_active_chart", "rrt_active_output"},
        args.washout_hours,
    )
    death, death_report = load_death_incident(root, icu, args.washout_hours)

    concordance = {
        "ventilation_explicit_vs_support": concordance_report(
            assigned,
            {"vent_procedure", "vent_explicit_chart"},
            {"vent_support"},
            "explicit_intubation",
            "ventilator_support_charting",
        ),
        "rrt_procedure_vs_active_support": concordance_report(
            assigned,
            {"rrt_procedure"},
            {"rrt_active_chart", "rrt_active_output"},
            "rrt_procedure",
            "rrt_active_support",
        ),
    }

    update_progress(current=4, total=6, phase="notes", message="Scanning prospectively available bedside notes for strict endpoint cohorts", unit="stage")
    all_events = [x for x in [vent_proc, vent_explicit, rrt_proc, rrt_active, death] if not x.empty]
    hadms = set()
    for x in all_events:
        hadms.update(pd.to_numeric(x["hadm_id"], errors="coerce").dropna().astype(int).tolist())
    notes, note_summary = scan_notes(root, hadms) if hadms else (pd.DataFrame(), {})

    update_progress(current=5, total=6, phase="coverage", message="Calculating horizon-specific clean-note coverage", unit="stage")
    coverage = {
        "invasive_ventilation_procedure_only": note_coverage_for_events(
            vent_proc, notes, VENT_NOTE_PATTERNS
        ),
        "invasive_ventilation_explicit_intubation": note_coverage_for_events(
            vent_explicit, notes, VENT_NOTE_PATTERNS
        ),
        "rrt_procedure_only": note_coverage_for_events(
            rrt_proc, notes, RRT_NOTE_PATTERNS
        ),
        "rrt_active_therapy": note_coverage_for_events(
            rrt_active, notes, RRT_NOTE_PATTERNS
        ),
        "icu_death": note_coverage_for_events(
            death, notes, DEATH_DIRECT_PATTERNS, DEATH_BROAD_PATTERNS
        ),
    }

    report = {
        "analysis": "Strict multi-outcome endpoint-definition audit",
        "local_only": True,
        "contains_note_text": False,
        "contains_patient_identifiers": False,
        "model_inference_performed": False,
        "washout_hours_from_icu_admission": float(args.washout_hours),
        "endpoint_tiers": {
            "invasive_ventilation_procedure_only": (
                "Explicit MetaVision Intubation procedure only; prevalent ventilation is screened "
                "with any explicit intubation or ventilator-support evidence during the washout."
            ),
            "invasive_ventilation_explicit_intubation": (
                "Explicit Intubation procedure plus a narrow set of intubation-completion/date chart events; "
                "generic ventilator settings are used only for prevalent-support screening, never as the endpoint."
            ),
            "rrt_procedure_only": (
                "Named RRT procedures only (hemodialysis/CRRT/CVVHD/CVVHDF/SCUF/peritoneal dialysis), "
                "with active RRT chart/output evidence used only to screen prevalent therapy."
            ),
            "rrt_active_therapy": (
                "Procedure tier broadened with a curated set of active-therapy chart/output evidence; "
                "access, catheter, history, filter-change, and fluid bookkeeping items are excluded."
            ),
            "icu_death": "Hospital DEATHTIME occurring during the ICU stay after washout.",
        },
        "curated_dictionary_items": item_meta,
        "incident_counts": {
            "invasive_ventilation_procedure_only": vent_proc_report,
            "invasive_ventilation_explicit_intubation": vent_explicit_report,
            "rrt_procedure_only": rrt_proc_report,
            "rrt_active_therapy": rrt_active_report,
            "icu_death": death_report,
        },
        "cross_evidence_concordance": concordance,
        "prospective_note_summary": note_summary,
        "prospective_note_coverage": coverage,
        "selection_guardrail": (
            "No Open-Jev, Laya, DiffusionGemma-Jev, TF-IDF, physiology model, or outcome prediction "
            "was run. Endpoint tier and horizon selection must be frozen from clinical specificity, "
            "timestamp validity, prevalence control, event counts, and prospective clean-note coverage "
            "before semantic performance is examined."
        ),
        "local_model_policy": (
            "All future credentialed-note semantic inference is local-only. Remote Cloud Run/API inference "
            "is outside the study plan. DiffusionGemma-Jev may be evaluated only through a local Jev-compatible "
            "server bound to localhost."
        ),
        "next_step": (
            "Use this audit to freeze one ventilation tier, one RRT tier, and a death horizon. "
            "Then build matched prospective risk sets and run the same zero-shot local semantic models "
            "(Open-Jev, Laya, and local DiffusionGemma-Jev) without revisiting endpoint definitions."
        ),
    }

    update_progress(current=6, total=6, phase="complete", message="Strict endpoint-definition audit complete", unit="stage")
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
