from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

from common import find_file, lower_columns, module_path, parse_datetime, read_columns, resolve_root
from runrelay_progress import update_progress


RRT_PROCEDURE_LABELS = {
    "hemodialysis",
    "dialysis - crrt",
    "dialysis - cvvhd",
    "peritoneal dialysis",
    "dialysis - cvvhdf",
    "dialysis - scuf",
}
RRT_ACTIVE_CHART_LABELS = {
    "dialysis type",
    "crrt mode",
    "hemodialysis output",
}
RRT_STRICT_OUTPUT_LABELS = {
    "hemodialysis",
    "dialysis",
    "peritoneal dialysis",
    "hemo dialysis",
}


def norm(x: object) -> str:
    return re.sub(r"\s+", " ", str(x).strip()).lower()


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


def load_icu(root: Path) -> pd.DataFrame:
    f = find_file(module_path(root, "mimiciii"), ["ICUSTAYS.csv.gz", "ICUSTAYS.csv"])
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


def load_items(root: Path) -> pd.DataFrame:
    f = find_file(module_path(root, "mimiciii"), ["D_ITEMS.csv.gz", "D_ITEMS.csv"])
    d = lower_columns(pd.read_csv(f, low_memory=False))
    d["itemid"] = pd.to_numeric(d["itemid"], errors="coerce")
    d = d.dropna(subset=["itemid"]).copy()
    d["itemid"] = d["itemid"].astype(int)
    for c in ["label", "linksto", "dbsource", "category"]:
        if c not in d:
            d[c] = ""
        d[c] = d[c].fillna("").astype(str)
    d["label_norm"] = d["label"].map(norm)
    d["linksto_norm"] = d["linksto"].str.lower()
    return d


def discover(d: pd.DataFrame) -> tuple[dict[str, set[int]], dict]:
    groups = {
        "procedure": set(d[
            (d["linksto_norm"] == "procedureevents_mv")
            & d["label_norm"].isin(RRT_PROCEDURE_LABELS)
        ]["itemid"].astype(int)),
        "active_chart": set(d[
            (d["linksto_norm"] == "chartevents")
            & d["label_norm"].isin(RRT_ACTIVE_CHART_LABELS)
        ]["itemid"].astype(int)),
        "strict_output": set(d[
            (d["linksto_norm"] == "outputevents")
            & d["label_norm"].isin(RRT_STRICT_OUTPUT_LABELS)
        ]["itemid"].astype(int)),
    }
    meta = {}
    for name, ids in groups.items():
        g = d[d["itemid"].isin(ids)].copy()
        meta[name] = {
            "n_itemids": len(ids),
            "items": g.sort_values(["linksto_norm", "itemid"])[
                ["itemid", "label", "dbsource", "linksto", "category"]
            ].to_dict(orient="records"),
        }
    return groups, meta


def scan(root: Path, groups: dict[str, set[int]]) -> pd.DataFrame:
    pieces = []

    chart = find_file(module_path(root, "mimiciii"), ["CHARTEVENTS.csv.gz", "CHARTEVENTS.csv"])
    ids = groups["active_chart"]
    if chart is not None and ids:
        for chunk in read_columns(
            chart,
            ["subject_id", "hadm_id", "icustay_id", "itemid", "charttime", "error"],
            chunksize=750_000,
        ):
            c = lower_columns(chunk)
            c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
            c = c[c["itemid"].isin(ids)]
            if c.empty:
                continue
            if "error" in c:
                c = c[c["error"].fillna(0).astype(str) != "1"]
            for col in ["subject_id", "hadm_id", "icustay_id"]:
                c[col] = pd.to_numeric(c[col], errors="coerce")
            c["event_time"] = parse_datetime(c["charttime"])
            c = c.dropna(subset=["hadm_id", "event_time"])
            c["evidence"] = "active_chart"
            pieces.append(c[["subject_id", "hadm_id", "icustay_id", "itemid", "event_time", "evidence"]])

    proc = find_file(module_path(root, "mimiciii"), ["PROCEDUREEVENTS_MV.csv.gz", "PROCEDUREEVENTS_MV.csv"])
    ids = groups["procedure"]
    if proc is not None and ids:
        for chunk in read_columns(
            proc,
            ["subject_id", "hadm_id", "icustay_id", "itemid", "starttime", "statusdescription"],
            chunksize=300_000,
        ):
            c = lower_columns(chunk)
            c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
            c = c[c["itemid"].isin(ids)]
            if c.empty:
                continue
            if "statusdescription" in c:
                bad = c["statusdescription"].fillna("").astype(str).str.lower().str.contains("rewritten|cancelled")
                c = c[~bad]
            for col in ["subject_id", "hadm_id", "icustay_id"]:
                c[col] = pd.to_numeric(c[col], errors="coerce")
            c["event_time"] = parse_datetime(c["starttime"])
            c = c.dropna(subset=["hadm_id", "event_time"])
            c["evidence"] = "procedure"
            pieces.append(c[["subject_id", "hadm_id", "icustay_id", "itemid", "event_time", "evidence"]])

    out = find_file(module_path(root, "mimiciii"), ["OUTPUTEVENTS.csv.gz", "OUTPUTEVENTS.csv"])
    ids = groups["strict_output"]
    if out is not None and ids:
        for chunk in read_columns(
            out,
            ["subject_id", "hadm_id", "icustay_id", "itemid", "charttime", "iserror"],
            chunksize=500_000,
        ):
            c = lower_columns(chunk)
            c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
            c = c[c["itemid"].isin(ids)]
            if c.empty:
                continue
            if "iserror" in c:
                c = c[c["iserror"].fillna(0).astype(str) != "1"]
            for col in ["subject_id", "hadm_id", "icustay_id"]:
                c[col] = pd.to_numeric(c[col], errors="coerce")
            c["event_time"] = parse_datetime(c["charttime"])
            c = c.dropna(subset=["hadm_id", "event_time"])
            c["evidence"] = "strict_output"
            pieces.append(c[["subject_id", "hadm_id", "icustay_id", "itemid", "event_time", "evidence"]])

    return pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()


def assign(events: pd.DataFrame, icu: pd.DataFrame) -> pd.DataFrame:
    m = events.merge(
        icu[["subject_id", "hadm_id", "icustay_id", "intime", "outtime", "dbsource"]],
        on="hadm_id",
        how="inner",
        suffixes=("_event", "_icu"),
    )
    m = m[(m["event_time"] >= m["intime"]) & (m["event_time"] <= m["outtime"])].copy()
    m["subject_id"] = pd.to_numeric(m["subject_id_icu"], errors="coerce")
    m["icustay_id"] = pd.to_numeric(m["icustay_id_icu"], errors="coerce")
    m["hours_since_icu"] = (m["event_time"] - m["intime"]).dt.total_seconds() / 3600
    return m


def tier(m: pd.DataFrame, name: str, endpoint: set[str], prevalence: set[str], washout: float) -> tuple[pd.DataFrame, dict]:
    early = m[m["evidence"].isin(prevalence) & (m["hours_since_icu"] < washout)]
    early_stays = set(early["icustay_id"].dropna().astype(int))

    x = m[m["evidence"].isin(endpoint) & (m["hours_since_icu"] >= washout)].copy()
    x = x[~x["icustay_id"].fillna(-1).astype(int).isin(early_stays)]
    x = x.sort_values("event_time").groupby("icustay_id", as_index=False).first()
    x = x.sort_values("event_time").groupby("subject_id", as_index=False).first()
    return x, {
        "tier": name,
        "endpoint_evidence": sorted(endpoint),
        "prevalence_evidence": sorted(prevalence),
        "prevalent_stays_excluded": len(early_stays),
        "incident_unique_subjects": len(x),
        "dbsource_counts": {str(k): int(v) for k, v in x["dbsource"].value_counts(dropna=False).to_dict().items()},
        "source_evidence_counts": {str(k): int(v) for k, v in x["evidence"].value_counts().to_dict().items()},
        "hours_from_icu_to_event": qstats(x["hours_since_icu"]),
    }


def concordance(m: pd.DataFrame, a: set[str], b: set[str]) -> dict:
    aa = m[m["evidence"].isin(a)].sort_values("event_time").groupby("icustay_id", as_index=False).first()[["icustay_id", "event_time"]]
    bb = m[m["evidence"].isin(b)].sort_values("event_time").groupby("icustay_id", as_index=False).first()[["icustay_id", "event_time"]]
    z = aa.merge(bb, on="icustay_id", suffixes=("_a", "_b"))
    if z.empty:
        return {"stays_with_both": 0}
    d = (z["event_time_b"] - z["event_time_a"]).dt.total_seconds() / 3600
    return {
        "stays_with_both": len(z),
        "b_minus_a_hours": qstats(d),
        "within_6h_pct": float(100 * (d.abs() <= 6).mean()),
        "within_12h_pct": float(100 * (d.abs() <= 12).mean()),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--washout-hours", type=float, default=6.0)
    args = ap.parse_args()

    root = resolve_root(args.root)
    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    update_progress(current=1, total=4, phase="dictionary", message="Curating strict RRT evidence tiers", unit="stage")
    icu = load_icu(root)
    items = load_items(root)
    groups, meta = discover(items)

    update_progress(current=2, total=4, phase="scan", message="Scanning strict RRT evidence", unit="stage")
    events = scan(root, groups)
    m = assign(events, icu)

    update_progress(current=3, total=4, phase="tiers", message="Comparing conservative RRT initiation tiers", unit="stage")
    p, rp = tier(
        m, "procedure_only",
        {"procedure"},
        {"procedure", "active_chart", "strict_output"},
        args.washout_hours,
    )
    pc, rpc = tier(
        m, "procedure_plus_active_chart",
        {"procedure", "active_chart"},
        {"procedure", "active_chart", "strict_output"},
        args.washout_hours,
    )
    pcs, rpcs = tier(
        m, "procedure_plus_active_chart_plus_strict_output",
        {"procedure", "active_chart", "strict_output"},
        {"procedure", "active_chart", "strict_output"},
        args.washout_hours,
    )

    report = {
        "analysis": "RRT endpoint refinement audit",
        "local_only": True,
        "contains_patient_identifiers": False,
        "model_inference_performed": False,
        "washout_hours": args.washout_hours,
        "curated_items": meta,
        "tiers": {
            "procedure_only": rp,
            "procedure_plus_active_chart": rpc,
            "procedure_plus_active_chart_plus_strict_output": rpcs,
        },
        "concordance": {
            "procedure_vs_active_chart": concordance(m, {"procedure"}, {"active_chart"}),
            "procedure_vs_strict_output": concordance(m, {"procedure"}, {"strict_output"}),
            "active_chart_vs_strict_output": concordance(m, {"active_chart"}, {"strict_output"}),
        },
        "guardrail": (
            "This audit exists only to select a clinically defensible RRT initiation definition before "
            "semantic prediction is examined. Output labels containing off/out/removed/removal/net/fluid/flush "
            "are excluded from the strict-output tier."
        ),
    }

    update_progress(current=4, total=4, phase="complete", message="RRT endpoint refinement complete", unit="stage")
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
