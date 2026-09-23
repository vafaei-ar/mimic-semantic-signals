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

CANDIDATE_SPECS = {
    "invasive_ventilation": {
        "item_label_pattern": (
            r"intubat|endotracheal|mechanical ventilation|ventilator mode|vent mode|"
            r"tidal volume.*set|respiratory rate.*set|set respiratory rate|"
            r"pressure control.*set|pressure support.*set"
        ),
        "note_language_patterns": [
            r"\bintubat\w*\b",
            r"\bendotracheal\b",
            r"\bmechanical ventilat\w*\b",
            r"\bventilator\b",
            r"\bETT\b",
        ],
    },
    "renal_replacement_therapy": {
        "item_label_pattern": (
            r"dialysis|hemodialysis|haemodialysis|CVVH|CVVHD|CVVHDF|CRRT|"
            r"hemofiltration|haemofiltration|renal replacement"
        ),
        "note_language_patterns": [
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
        "item_label_pattern": None,
        "note_language_patterns": [
            r"\bdying\b",
            r"\bdeath\b",
            r"\bcomfort care\b",
            r"\bcomfort measures\b",
            r"\bCMO\b",
            r"\bDNR\b",
            r"\bdo not resuscitate\b",
            r"\bwithdraw\w* care\b",
            r"\bhospice\b",
        ],
    },
}

WINDOWS_HOURS = [6, 12, 24]


def qstats(x: pd.Series) -> dict:
    v = pd.to_numeric(x, errors="coerce").dropna()
    if v.empty:
        return {
            "n": 0, "min": None, "p05": None, "p25": None, "median": None,
            "p75": None, "p95": None, "max": None,
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
    d = d.dropna(subset=["itemid"])
    d["itemid"] = d["itemid"].astype("int64")
    for c in ["label", "dbsource", "linksto", "category"]:
        if c not in d:
            d[c] = ""
        d[c] = d[c].fillna("").astype(str)
    return d


def discover_items(d_items: pd.DataFrame) -> tuple[dict[str, dict[str, set[int]]], list[dict]]:
    discovered: dict[str, dict[str, set[int]]] = {}
    rows: list[dict] = []
    for candidate, spec in CANDIDATE_SPECS.items():
        pat = spec["item_label_pattern"]
        if pat is None:
            discovered[candidate] = {"chartevents": set(), "procedureevents_mv": set()}
            continue
        mask = d_items["label"].str.contains(pat, case=False, regex=True, na=False)
        m = d_items.loc[mask].copy()
        by_link: dict[str, set[int]] = {}
        for link, g in m.groupby(m["linksto"].str.lower()):
            by_link[str(link)] = set(g["itemid"].astype(int).tolist())
        discovered[candidate] = {
            "chartevents": by_link.get("chartevents", set()),
            "procedureevents_mv": by_link.get("procedureevents_mv", set()),
        }
        for row in m.itertuples(index=False):
            rows.append({
                "candidate": candidate,
                "itemid": int(row.itemid),
                "label": str(row.label),
                "dbsource": str(row.dbsource),
                "linksto": str(row.linksto),
                "category": str(row.category),
            })
    return discovered, rows


def scan_item_events(root: Path, discovered: dict[str, dict[str, set[int]]]) -> pd.DataFrame:
    item_to_candidate: dict[int, set[str]] = {}
    for candidate, links in discovered.items():
        for ids in links.values():
            for itemid in ids:
                item_to_candidate.setdefault(int(itemid), set()).add(candidate)

    pieces: list[pd.DataFrame] = []

    chart_ids = {
        itemid
        for candidate in discovered.values()
        for itemid in candidate.get("chartevents", set())
    }
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
            c = c.dropna(subset=["hadm_id", "event_time", "itemid"])
            if c.empty:
                continue
            for candidate in ["invasive_ventilation", "renal_replacement_therapy"]:
                ids = discovered[candidate]["chartevents"]
                x = c[c["itemid"].isin(ids)].copy()
                if not x.empty:
                    x["candidate"] = candidate
                    x["source"] = "chartevents"
                    pieces.append(x[[
                        "subject_id", "hadm_id", "icustay_id", "itemid",
                        "event_time", "candidate", "source"
                    ]])

    proc_ids = {
        itemid
        for candidate in discovered.values()
        for itemid in candidate.get("procedureevents_mv", set())
    }
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
            c = c.dropna(subset=["hadm_id", "event_time", "itemid"])
            if c.empty:
                continue
            for candidate in ["invasive_ventilation", "renal_replacement_therapy"]:
                ids = discovered[candidate]["procedureevents_mv"]
                x = c[c["itemid"].isin(ids)].copy()
                if not x.empty:
                    x["candidate"] = candidate
                    x["source"] = "procedureevents_mv"
                    pieces.append(x[[
                        "subject_id", "hadm_id", "icustay_id", "itemid",
                        "event_time", "candidate", "source"
                    ]])

    if not pieces:
        return pd.DataFrame(columns=[
            "subject_id", "hadm_id", "icustay_id", "itemid",
            "event_time", "candidate", "source"
        ])
    return pd.concat(pieces, ignore_index=True)


def load_death_events(root: Path) -> pd.DataFrame:
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
    d["candidate"] = "icu_death"
    d["source"] = "admissions_deathtime"
    d["icustay_id"] = np.nan
    d["itemid"] = np.nan
    return d[[
        "subject_id", "hadm_id", "icustay_id", "itemid",
        "event_time", "candidate", "source"
    ]]


def map_first_incident_events(events: pd.DataFrame, icu: pd.DataFrame, washout_h: float) -> tuple[pd.DataFrame, dict]:
    rows = []
    summary = {}
    for candidate in CANDIDATE_SPECS:
        e = events[events["candidate"] == candidate].copy()
        if e.empty:
            summary[candidate] = {
                "raw_event_rows": 0,
                "icu_stays_with_any_evidence": 0,
                "icu_stays_with_evidence_during_first_washout": 0,
                "incident_eligible_icu_stays": 0,
                "incident_eligible_unique_subjects": 0,
            }
            continue

        e["hadm_id"] = pd.to_numeric(e["hadm_id"], errors="coerce")
        merged = e.merge(
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
            summary[candidate] = {
                "raw_event_rows": int(len(e)),
                "icu_stays_with_any_evidence": 0,
                "icu_stays_with_evidence_during_first_washout": 0,
                "incident_eligible_icu_stays": 0,
                "incident_eligible_unique_subjects": 0,
            }
            continue

        merged["hours_since_icu"] = (
            merged["event_time"] - merged["intime"]
        ).dt.total_seconds() / 3600.0

        first = (
            merged.sort_values("event_time")
            .groupby(["icustay_id_icu"], as_index=False)
            .first()
        )
        early = first["hours_since_icu"] < washout_h
        incident = first[~early].copy()
        incident["candidate"] = candidate

        # One benchmark case per patient: earliest qualifying ICU event.
        incident = (
            incident.sort_values("event_time")
            .groupby("subject_id_icu", as_index=False)
            .first()
        )
        incident = incident.rename(columns={
            "subject_id_icu": "subject_id",
            "icustay_id_icu": "icustay_id",
        })
        rows.append(incident[[
            "subject_id", "hadm_id", "icustay_id", "intime", "outtime",
            "dbsource", "event_time", "hours_since_icu", "candidate", "source"
        ]])

        summary[candidate] = {
            "raw_event_rows": int(len(e)),
            "icu_stays_with_any_evidence": int(first["icustay_id_icu"].nunique()),
            "icu_stays_with_evidence_during_first_washout": int(early.sum()),
            "incident_eligible_icu_stays_before_patient_dedup": int((~early).sum()),
            "incident_eligible_unique_subjects": int(len(incident)),
            "hours_from_icu_to_first_incident_event": qstats(incident["hours_since_icu"]),
            "source_counts_after_patient_dedup": {
                str(k): int(v)
                for k, v in incident["source"].value_counts().to_dict().items()
            },
        }

    all_incident = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    return all_incident, summary


def compile_note_regex(patterns: list[str]) -> re.Pattern:
    return re.compile("|".join(f"(?:{p})" for p in patterns), flags=re.IGNORECASE)


def scan_notes(root: Path, hadm_filter: set[int]) -> tuple[pd.DataFrame, dict]:
    f = find_file(module_path(root, "mimiciii"), ["NOTEEVENTS.csv.gz", "NOTEEVENTS.csv"])
    if f is None:
        raise FileNotFoundError("NOTEEVENTS not found")

    pieces = []
    source_rows = 0
    eligible_rows = 0
    store_available = 0
    for chunk in read_columns(
        f,
        ["hadm_id", "charttime", "storetime", "category", "iserror", "text"],
        chunksize=100_000,
    ):
        source_rows += len(chunk)
        c = lower_columns(chunk)
        c["hadm_id"] = pd.to_numeric(c["hadm_id"], errors="coerce")
        c = c[c["hadm_id"].isin(hadm_filter)]
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
        eligible_rows += len(c)
        store_available += int(c["storetime_available"].sum())
        pieces.append(c[[
            "hadm_id", "note_time", "category", "text", "storetime_available"
        ]])

    notes = pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()
    return notes, {
        "source_note_rows_scanned": int(source_rows),
        "eligible_bedside_note_rows_in_candidate_admissions": int(eligible_rows),
        "storetime_available_fraction": (
            float(store_available / eligible_rows) if eligible_rows else None
        ),
    }


def note_coverage(incident: pd.DataFrame, notes: pd.DataFrame) -> dict:
    out = {}
    if incident.empty or notes.empty:
        return out

    for candidate, events in incident.groupby("candidate"):
        rx = compile_note_regex(CANDIDATE_SPECS[candidate]["note_language_patterns"])
        merged = events.merge(notes, on="hadm_id", how="left")
        merged = merged[
            (merged["note_time"] >= merged["intime"])
            & (merged["note_time"] < merged["event_time"])
        ].copy()
        merged["hours_before_event"] = (
            merged["event_time"] - merged["note_time"]
        ).dt.total_seconds() / 3600.0
        merged["explicit_or_endpoint_adjacent_language"] = (
            merged["text"].fillna("").astype(str).str.contains(rx, regex=True, na=False)
        )

        rows = {}
        n_events = int(events["subject_id"].nunique())
        for w in WINDOWS_HOURS:
            g = merged[
                (merged["hours_before_event"] > 0)
                & (merged["hours_before_event"] <= w)
            ].copy()
            subjects_any = int(g["subject_id"].nunique())
            clean = g[~g["explicit_or_endpoint_adjacent_language"]].copy()
            subjects_clean = int(clean["subject_id"].nunique())
            rows[str(w)] = {
                "window_hours": int(w),
                "incident_subjects": n_events,
                "subjects_with_any_prospective_note": subjects_any,
                "coverage_any_pct": float(100 * subjects_any / n_events) if n_events else None,
                "subjects_with_at_least_one_language_clean_note": subjects_clean,
                "coverage_language_clean_pct": (
                    float(100 * subjects_clean / n_events) if n_events else None
                ),
                "notes_in_window": int(len(g)),
                "notes_with_endpoint_adjacent_language": int(
                    g["explicit_or_endpoint_adjacent_language"].sum()
                ),
                "endpoint_adjacent_language_note_pct": (
                    float(100 * g["explicit_or_endpoint_adjacent_language"].mean())
                    if len(g) else None
                ),
            }
        out[candidate] = rows
    return out


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Aggregate feasibility audit for additional prospective MIMIC-III outcomes "
            "before freezing a multi-outcome semantic benchmark."
        )
    )
    ap.add_argument("--root", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--washout-hours", type=float, default=6.0)
    args = ap.parse_args()

    root = resolve_root(args.root)
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    update_progress(current=1, total=5, phase="endpoint_discovery", message="Loading ICU stays and D_ITEMS", unit="stage")
    icu = load_icustays(root)
    d_items = load_d_items(root)
    discovered, dictionary_rows = discover_items(d_items)

    update_progress(current=2, total=5, phase="event_scan", message="Scanning candidate procedure/chart events", unit="stage")
    item_events = scan_item_events(root, discovered)
    death_events = load_death_events(root)
    events = pd.concat([item_events, death_events], ignore_index=True, sort=False)

    update_progress(current=3, total=5, phase="incident_mapping", message="Mapping first incident events to ICU stays", unit="stage")
    incident, event_summary = map_first_incident_events(events, icu, args.washout_hours)

    hadms = set(pd.to_numeric(incident.get("hadm_id", pd.Series(dtype=float)), errors="coerce").dropna().astype(int))
    update_progress(current=4, total=5, phase="note_scan", message="Scanning prospectively available bedside notes", unit="stage")
    notes, note_summary = scan_notes(root, hadms) if hadms else (pd.DataFrame(), {})

    coverage = note_coverage(incident, notes)

    # Safe dictionary metadata only; no patient-level rows are exported.
    dictionary_summary = {}
    if dictionary_rows:
        dd = pd.DataFrame(dictionary_rows)
        for candidate, g in dd.groupby("candidate"):
            dictionary_summary[candidate] = {
                "matched_itemids": int(g["itemid"].nunique()),
                "by_linksto": {
                    str(k): int(v) for k, v in g.groupby("linksto")["itemid"].nunique().to_dict().items()
                },
                "items": g.sort_values(["linksto", "itemid"])[
                    ["itemid", "label", "dbsource", "linksto", "category"]
                ].to_dict(orient="records"),
            }

    feasibility_flags = {}
    for candidate in CANDIDATE_SPECS:
        c = coverage.get(candidate, {})
        feasibility_flags[candidate] = {
            "clean_note_subjects_6h": c.get("6", {}).get("subjects_with_at_least_one_language_clean_note", 0),
            "clean_note_subjects_12h": c.get("12", {}).get("subjects_with_at_least_one_language_clean_note", 0),
            "clean_note_subjects_24h": c.get("24", {}).get("subjects_with_at_least_one_language_clean_note", 0),
            "screening_interpretation": (
                "Feasibility only. Horizon selection must be frozen before semantic inference "
                "and should be based on clinical meaning plus event/note coverage, not model performance."
            ),
        }

    report = {
        "analysis": "MIMIC-III multi-outcome semantic benchmark feasibility audit",
        "local_only": True,
        "contains_note_text": False,
        "contains_patient_identifiers": False,
        "washout_hours_from_icu_admission_for_incident_treatment_endpoints": float(args.washout_hours),
        "candidate_outcomes": {
            "invasive_ventilation": (
                "Candidate first invasive-ventilation/intubation evidence after ICU washout; "
                "dictionary mapping is intentionally audited before final endpoint freeze."
            ),
            "renal_replacement_therapy": (
                "Candidate first dialysis/CRRT/RRT evidence after ICU washout; "
                "dictionary mapping is intentionally audited before final endpoint freeze."
            ),
            "icu_death": (
                "Death timestamp occurring during the ICU stay; included as a non-treatment hard outcome."
            ),
        },
        "dictionary_discovery": dictionary_summary,
        "event_feasibility": event_summary,
        "prospective_note_summary": note_summary,
        "prospective_note_coverage": coverage,
        "feasibility_flags": feasibility_flags,
        "selection_guardrail": (
            "This job does not run Open-Jev, Laya, TF-IDF, or any outcome prediction model. "
            "Candidate outcomes and horizons should be selected/frozen from clinical validity, "
            "timestamp validity, event counts, and prospective note coverage before semantic performance is examined."
        ),
        "next_step": (
            "Manually audit the returned dictionary mappings and event/coverage counts. "
            "Then freeze a small cross-domain endpoint panel and only afterward build matched risk-set cohorts "
            "and run zero-shot semantic models."
        ),
    }

    update_progress(current=5, total=5, phase="complete", message="Multi-outcome endpoint feasibility audit complete", unit="stage")
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
