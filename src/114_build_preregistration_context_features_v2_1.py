from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

from common import find_file, lower_columns, module_path, parse_datetime, read_columns, resolve_root
from runrelay_progress import update_progress


def load_numbered_module(filename: str, name: str):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {filename}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


context_audit = load_numbered_module(
    "109_audit_preregistration_context_v2_1.py",
    "preregistration_context_audit_v2_1",
)

PRIMARY_OUTCOMES = (
    "invasive_ventilation",
    "renal_replacement_therapy",
    "icu_death",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def collapse_note_category(value: object) -> str | float:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return np.nan
    x = str(value).strip().lower()
    if not x or x == "nan":
        return np.nan
    if x in {"nursing", "nursing/other"}:
        return "nursing"
    if x in {"physician", "consult"}:
        return "physician"
    if x == "respiratory":
        return "respiratory"
    return "other"


def flatten_itemids(mapping: dict) -> set[int]:
    out: set[int] = set()
    for value in mapping.values():
        if isinstance(value, dict):
            out |= flatten_itemids(value)
        elif isinstance(value, list):
            for x in value:
                if isinstance(x, (int, np.integer)):
                    out.add(int(x))
    return out


def invert_agent_map(agent_map: dict[str, list[int]]) -> dict[int, str]:
    out: dict[int, str] = {}
    for agent, ids in agent_map.items():
        for itemid in ids:
            itemid = int(itemid)
            if itemid in out:
                raise RuntimeError(f"duplicate medication item mapping: {itemid}")
            out[itemid] = str(agent)
    return out


def load_analysis_frames(local_root: Path, contract: dict) -> dict[str, dict]:
    specs: dict[str, dict] = {}
    primary = contract["confirmatory_outcomes"]
    for outcome in PRIMARY_OUTCOMES:
        d = pd.read_csv(local_root / outcome / "population_index_local.csv", low_memory=False)
        source = str(primary[outcome]["source"]).lower()
        d["dbsource"] = d["dbsource"].fillna("unknown").astype(str).str.strip().str.lower()
        d = d[d["dbsource"].eq(source)].copy()
        specs[outcome] = {
            "outcome": outcome,
            "source": source,
            "frame": d,
            "expected": primary[outcome],
            "filename": "preregistration_context_features_v2_1_local.csv",
        }

    rep = contract["prespecified_replications"]["icu_death_carevue"]
    d = pd.read_csv(local_root / "icu_death" / "population_index_local.csv", low_memory=False)
    d["dbsource"] = d["dbsource"].fillna("unknown").astype(str).str.strip().str.lower()
    d = d[d["dbsource"].eq("carevue")].copy()
    specs["icu_death_carevue"] = {
        "outcome": "icu_death",
        "source": "carevue",
        "frame": d,
        "expected": rep,
        "filename": "preregistration_context_features_v2_1_carevue_local.csv",
    }

    for name, spec in specs.items():
        d = spec["frame"]
        for col in ["subject_id", "hadm_id", "icustay_id", "label"]:
            d[col] = pd.to_numeric(d[col], errors="raise").astype("int64")
        d["landmark_time"] = pd.to_datetime(d["landmark_time"], errors="raise")
        d["note_time"] = pd.to_datetime(d["note_time"], errors="coerce")
        expected = spec["expected"]
        observed = {
            "rows": int(len(d)),
            "unique_patients": int(d["subject_id"].nunique()),
            "cases": int(d["label"].sum()),
            "controls": int(len(d) - d["label"].sum()),
        }
        for key, value in observed.items():
            if int(expected[key]) != int(value):
                raise RuntimeError(
                    f"{name}: analysis-population contract violation for {key}: "
                    f"observed {value}, expected {expected[key]}"
                )
        spec["frame"] = d.reset_index(drop=True)

    return specs


def unique_stays(specs: dict[str, dict]) -> pd.DataFrame:
    frames = []
    for spec in specs.values():
        frames.append(
            spec["frame"][["subject_id", "hadm_id", "icustay_id", "landmark_time", "dbsource"]]
        )
    d = pd.concat(frames, ignore_index=True).drop_duplicates()
    conflicts = d.groupby("icustay_id").agg(
        landmark_n=("landmark_time", "nunique"),
        source_n=("dbsource", "nunique"),
    )
    if (conflicts["landmark_n"] > 1).any() or (conflicts["source_n"] > 1).any():
        raise RuntimeError("Conflicting landmark/source assignments across analysis frames")
    return d.drop_duplicates("icustay_id").reset_index(drop=True)


def build_note_behavior(root: Path, stays: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    # Reuse the corrected metadata implementation from src/109.
    return context_audit.build_note_behavior(root, stays)


def build_chartevent_context(
    root: Path,
    stays: pd.DataFrame,
    freeze: dict,
) -> pd.DataFrame:
    resp = freeze["treatment"]["respiratory"]
    code = freeze["treatment"]["code_status"]
    all_ids = flatten_itemids(resp) | flatten_itemids(code)

    f = find_file(module_path(root, "mimiciii"), ["CHARTEVENTS.csv.gz", "CHARTEVENTS.csv"])
    if f is None:
        raise FileNotFoundError("CHARTEVENTS not found")

    wanted_icu = set(stays["icustay_id"].astype(int))
    parts = []
    for chunk in read_columns(
        f,
        ["icustay_id", "itemid", "charttime", "valuenum", "value", "error"],
        chunksize=500_000,
    ):
        c = lower_columns(chunk)
        c["icustay_id"] = pd.to_numeric(c["icustay_id"], errors="coerce")
        c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
        c = c[c["icustay_id"].isin(wanted_icu) & c["itemid"].isin(all_ids)].copy()
        if c.empty:
            continue
        bad = pd.to_numeric(c.get("error", pd.Series(0, index=c.index)), errors="coerce").fillna(0).ne(0)
        c = c[~bad].copy()
        c["charttime"] = parse_datetime(c["charttime"])
        c["valuenum"] = pd.to_numeric(c["valuenum"], errors="coerce")
        c = c.dropna(subset=["charttime", "itemid", "icustay_id"])
        c["itemid"] = c["itemid"].astype(int)
        c["icustay_id"] = c["icustay_id"].astype("int64")
        parts.append(c[["icustay_id", "itemid", "charttime", "valuenum", "value"]])

    ev = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(
        columns=["icustay_id", "itemid", "charttime", "valuenum", "value"]
    )
    m = ev.merge(
        stays[["icustay_id", "landmark_time", "dbsource"]],
        on="icustay_id",
        how="inner",
        validate="many_to_one",
    )

    # Enforce source-specific item maps before deriving any feature.
    allowed_by_source = {
        source: (
            set(int(x) for x in resp["fio2"][source])
            | set(int(x) for x in resp["oxygen_flow"][source])
            | set(int(x) for x in resp["oxygen_device"][source])
            | set(int(x) for x in resp["niv_items"][source])
            | set(int(x) for x in code[source])
        )
        for source in ("carevue", "metavision")
    }
    keep = np.zeros(len(m), dtype=bool)
    for source, ids in allowed_by_source.items():
        keep |= m["dbsource"].eq(source).to_numpy() & m["itemid"].isin(ids).to_numpy()
    m = m.loc[keep].copy()

    lower = m["landmark_time"] - pd.to_timedelta(
        float(freeze["treatment"]["lookback_hours"]), unit="h"
    )
    pre6 = m[(m["charttime"] >= lower) & (m["charttime"] <= m["landmark_time"])].copy()
    preall = m[m["charttime"] <= m["landmark_time"]].copy()

    out = stays[["icustay_id", "dbsource"]].copy().set_index("icustay_id")

    def latest_numeric(feature_name: str, mapping: dict):
        frames = []
        for source in ("carevue", "metavision"):
            ids = set(int(x) for x in mapping[source])
            q = pre6[pre6["dbsource"].eq(source) & pre6["itemid"].isin(ids)].copy()
            frames.append(q)
        q = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        if q.empty:
            out[feature_name] = np.nan
            return
        q = q.dropna(subset=["valuenum"]).sort_values(["icustay_id", "charttime"])
        latest = q.groupby("icustay_id")["valuenum"].last()
        out[feature_name] = latest

    latest_numeric("treat_fio2_last_6h", resp["fio2"])
    latest_numeric("treat_oxygen_flow_last_6h", resp["oxygen_flow"])

    high_rx = str(resp["high_flow_regex"])
    niv_rx = str(resp["niv_device_regex"])
    high_ids = {
        source: set(int(x) for x in resp["oxygen_device"][source])
        for source in ("carevue", "metavision")
    }
    niv_itemids = {
        source: set(int(x) for x in resp["niv_items"][source])
        for source in ("carevue", "metavision")
    }

    out["treat_high_flow_any_6h"] = 0.0
    out["treat_niv_any_6h"] = 0.0
    for source in ("carevue", "metavision"):
        dq = pre6[
            pre6["dbsource"].eq(source) & pre6["itemid"].isin(high_ids[source])
        ].copy()
        vals = dq["value"].fillna("").astype(str).str.strip().str.lower()
        high_stays = set(
            dq.loc[vals.str.contains(high_rx, regex=True, na=False), "icustay_id"].astype(int)
        )
        niv_string_stays = set(
            dq.loc[vals.str.contains(niv_rx, regex=True, na=False), "icustay_id"].astype(int)
        )
        nq = pre6[
            pre6["dbsource"].eq(source)
            & pre6["itemid"].isin(niv_itemids[source])
        ]
        niv_stays = niv_string_stays | set(nq["icustay_id"].astype(int))

        source_idx = out["dbsource"].eq(source)
        out.loc[source_idx & out.index.isin(high_stays), "treat_high_flow_any_6h"] = 1.0
        out.loc[source_idx & out.index.isin(niv_stays), "treat_niv_any_6h"] = 1.0

    # Death-only code-status features are computed for all stays here and selected
    # only for death output frames.
    out["code_status_available"] = 0.0
    out["code_status_limitation"] = 0.0
    out["code_status_comfort_or_no_cpr"] = 0.0
    out["code_status_other"] = 0.0

    for source in ("carevue", "metavision"):
        ids = set(int(x) for x in code[source])
        q = preall[preall["dbsource"].eq(source) & preall["itemid"].isin(ids)].copy()
        if q.empty:
            continue
        q = q.sort_values(["icustay_id", "charttime"]).groupby("icustay_id", as_index=False).last()
        value = q["value"].fillna("").astype(str).str.strip().str.lower()
        available = value.ne("")
        limitation = value.str.contains(
            r"\bdnr\b|\bdni\b|do not resusc|do not intubat",
            regex=True,
            na=False,
        )
        comfort = value.str.contains(
            r"comfort|cpr not indicat",
            regex=True,
            na=False,
        )
        full = value.str.contains(r"full\s*code", regex=True, na=False)
        other = available & (~limitation) & (~comfort) & (~full)

        for col, mask in [
            ("code_status_available", available),
            ("code_status_limitation", limitation),
            ("code_status_comfort_or_no_cpr", comfort),
            ("code_status_other", other),
        ]:
            ids_true = set(q.loc[mask, "icustay_id"].astype(int))
            out.loc[out["dbsource"].eq(source) & out.index.isin(ids_true), col] = 1.0

    return out.reset_index()


def build_inputevent_context(
    root: Path,
    stays: pd.DataFrame,
    freeze: dict,
) -> pd.DataFrame:
    treat = freeze["treatment"]
    lookback_h = float(treat["lookback_hours"])
    out = stays[["icustay_id", "dbsource"]].copy().set_index("icustay_id")
    for col in [
        "treat_vasoactive_any",
        "treat_vasoactive_agent_count",
        "treat_sedative_any",
        "treat_sedative_agent_count",
    ]:
        out[col] = 0.0

    mv_stays = stays[stays["dbsource"].eq("metavision")][["icustay_id", "landmark_time"]]
    cv_stays = stays[stays["dbsource"].eq("carevue")][["icustay_id", "landmark_time"]]

    mv_agent = {
        **{item: ("vasoactive", agent) for item, agent in invert_agent_map(treat["vasoactive"]["metavision"]).items()},
        **{item: ("sedative", agent) for item, agent in invert_agent_map(treat["sedative_analgesic"]["metavision"]).items()},
    }
    cv_agent = {
        **{item: ("vasoactive", agent) for item, agent in invert_agent_map(treat["vasoactive"]["carevue"]).items()},
        **{item: ("sedative", agent) for item, agent in invert_agent_map(treat["sedative_analgesic"]["carevue"]).items()},
    }

    mv_file = find_file(module_path(root, "mimiciii"), ["INPUTEVENTS_MV.csv.gz", "INPUTEVENTS_MV.csv"])
    if mv_file is None:
        raise FileNotFoundError("INPUTEVENTS_MV not found")
    mv_parts = []
    wanted_mv = set(mv_stays["icustay_id"].astype(int))
    for chunk in read_columns(
        mv_file,
        ["icustay_id", "itemid", "starttime", "endtime", "rate", "statusdescription"],
        chunksize=250_000,
    ):
        c = lower_columns(chunk)
        c["icustay_id"] = pd.to_numeric(c["icustay_id"], errors="coerce")
        c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
        c = c[c["icustay_id"].isin(wanted_mv) & c["itemid"].isin(set(mv_agent))].copy()
        if c.empty:
            continue
        bad = c["statusdescription"].fillna("").astype(str).str.lower().str.contains("rewritten|cancelled")
        c = c[~bad].copy()
        c["starttime"] = parse_datetime(c["starttime"])
        c["endtime"] = parse_datetime(c["endtime"])
        c["rate"] = pd.to_numeric(c["rate"], errors="coerce")
        c = c.dropna(subset=["starttime", "endtime", "itemid", "icustay_id"])
        c["itemid"] = c["itemid"].astype(int)
        c["icustay_id"] = c["icustay_id"].astype("int64")
        c["kind"] = c["itemid"].map(lambda x: mv_agent[x][0])
        c["agent"] = c["itemid"].map(lambda x: mv_agent[x][1])
        mv_parts.append(c[["icustay_id", "starttime", "endtime", "rate", "kind", "agent"]])

    mv = pd.concat(mv_parts, ignore_index=True) if mv_parts else pd.DataFrame()
    if not mv.empty:
        m = mv.merge(mv_stays, on="icustay_id", how="inner")
        active = m[
            (m["starttime"] <= m["landmark_time"])
            & (m["endtime"] > m["landmark_time"])
            & (m["rate"].isna() | m["rate"].gt(0))
        ].copy()
        for kind in ("vasoactive", "sedative"):
            q = active[active["kind"].eq(kind)]
            counts = q.groupby("icustay_id")["agent"].nunique()
            out.loc[counts.index, f"treat_{kind}_agent_count"] = counts.astype(float)
            out.loc[counts.index, f"treat_{kind}_any"] = 1.0

    cv_file = find_file(module_path(root, "mimiciii"), ["INPUTEVENTS_CV.csv.gz", "INPUTEVENTS_CV.csv"])
    if cv_file is None:
        raise FileNotFoundError("INPUTEVENTS_CV not found")
    cv_parts = []
    wanted_cv = set(cv_stays["icustay_id"].astype(int))
    for chunk in read_columns(
        cv_file,
        ["icustay_id", "itemid", "charttime", "rate"],
        chunksize=250_000,
    ):
        c = lower_columns(chunk)
        c["icustay_id"] = pd.to_numeric(c["icustay_id"], errors="coerce")
        c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
        c = c[c["icustay_id"].isin(wanted_cv) & c["itemid"].isin(set(cv_agent))].copy()
        if c.empty:
            continue
        c["charttime"] = parse_datetime(c["charttime"])
        c["rate"] = pd.to_numeric(c["rate"], errors="coerce")
        c = c.dropna(subset=["charttime", "itemid", "icustay_id"])
        c["itemid"] = c["itemid"].astype(int)
        c["icustay_id"] = c["icustay_id"].astype("int64")
        c["kind"] = c["itemid"].map(lambda x: cv_agent[x][0])
        c["agent"] = c["itemid"].map(lambda x: cv_agent[x][1])
        cv_parts.append(c[["icustay_id", "charttime", "rate", "kind", "agent"]])

    cv = pd.concat(cv_parts, ignore_index=True) if cv_parts else pd.DataFrame()
    if not cv.empty:
        m = cv.merge(cv_stays, on="icustay_id", how="inner")
        lower = m["landmark_time"] - pd.to_timedelta(lookback_h, unit="h")
        recent = m[
            (m["charttime"] >= lower)
            & (m["charttime"] <= m["landmark_time"])
            & (m["rate"].isna() | m["rate"].gt(0))
        ].copy()
        for kind in ("vasoactive", "sedative"):
            q = recent[recent["kind"].eq(kind)]
            counts = q.groupby("icustay_id")["agent"].nunique()
            out.loc[counts.index, f"treat_{kind}_agent_count"] = counts.astype(float)
            out.loc[counts.index, f"treat_{kind}_any"] = 1.0

    return out.reset_index()


def summarize_features(df: pd.DataFrame, feature_cols: list[str]) -> dict:
    out = {}
    for col in feature_cols:
        s = df[col]
        if pd.api.types.is_numeric_dtype(s):
            nonmissing = int(s.notna().sum())
            item = {
                "nonmissing_rows": nonmissing,
                "nonmissing_fraction": float(nonmissing / len(df)) if len(df) else None,
            }
            finite = pd.to_numeric(s, errors="coerce").dropna()
            if len(finite):
                item["mean"] = float(finite.mean())
                item["min"] = float(finite.min())
                item["max"] = float(finite.max())
            out[col] = item
        else:
            counts = s.fillna("MISSING").astype(str).value_counts()
            out[col] = {
                "value_counts": {str(k): int(v) for k, v in counts.items()},
            }
    return out


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Materialize frozen preregistration treatment/documentation context features without predictive evaluation."
    )
    ap.add_argument("--root", required=True)
    ap.add_argument("--local-root", required=True)
    ap.add_argument("--analysis-populations", required=True)
    ap.add_argument("--context-freeze", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    root = resolve_root(args.root)
    local_root = Path(args.local_root).expanduser().resolve()
    population_contract = json.loads(
        Path(args.analysis_populations).expanduser().resolve().read_text(encoding="utf-8")
    )
    freeze = json.loads(
        Path(args.context_freeze).expanduser().resolve().read_text(encoding="utf-8")
    )
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    update_progress(current=1, total=5, phase="context_feature_materialization", message="Loading and validating source-specific analysis populations", unit="stage")
    specs = load_analysis_frames(local_root, population_contract)
    stays = unique_stays(specs)

    update_progress(current=2, total=5, phase="context_feature_materialization", message="Regenerating corrected note-behavior metadata", unit="stage")
    doc, doc_report = build_note_behavior(root, stays)
    doc = doc.drop(columns=["doc_last_note_gap_hours"], errors="ignore")

    update_progress(current=3, total=5, phase="context_feature_materialization", message="Extracting source-specific respiratory and code-status context", unit="stage")
    chart = build_chartevent_context(root, stays, freeze)

    update_progress(current=4, total=5, phase="context_feature_materialization", message="Extracting source-specific vasoactive and sedative context", unit="stage")
    inputs = build_inputevent_context(root, stays, freeze)

    common = chart.merge(inputs.drop(columns=["dbsource"]), on="icustay_id", how="left", validate="one_to_one")
    common = common.merge(doc, on="icustay_id", how="left", validate="one_to_one")

    report = {
        "analysis": "v2.1 frozen preregistration context feature materialization",
        "outcome_performance_computed": False,
        "outcome_labels_used_for_feature_selection": False,
        "context_freeze": "config/v2_1_context_feature_freeze.json",
        "analysis_population_contract": "config/v2_1_analysis_population_contract.json",
        "documentation_behavior_regenerated_with_corrected_note_gap_code": True,
        "documentation_behavior_included_features": freeze["documentation_behavior"]["features"],
        "documentation_behavior_excluded_features": freeze["documentation_behavior"]["excluded_features"],
        "note_behavior_scan": doc_report,
        "analyses": {},
    }

    update_progress(current=5, total=5, phase="context_feature_materialization", message="Writing local context feature files and aggregate manifest", unit="stage")
    for name, spec in specs.items():
        d = spec["frame"].copy()
        d["category_group"] = d["category"].map(collapse_note_category)
        base_cols = [
            "case_id", "subject_id", "icustay_id", "has_note",
            "note_age_at_landmark_hours", "category_group",
        ]
        out = d[base_cols].merge(
            common.drop(columns=["dbsource"]),
            on="icustay_id",
            how="left",
            validate="one_to_one",
        )

        feature_cols = [
            "has_note", "note_age_at_landmark_hours", "category_group",
            *freeze["documentation_behavior"]["features"],
            "treat_fio2_last_6h",
            "treat_oxygen_flow_last_6h",
            "treat_high_flow_any_6h",
            "treat_niv_any_6h",
            "treat_vasoactive_any",
            "treat_vasoactive_agent_count",
            "treat_sedative_any",
            "treat_sedative_agent_count",
        ]
        if spec["outcome"] == "icu_death":
            feature_cols += [
                "code_status_available",
                "code_status_limitation",
                "code_status_comfort_or_no_cpr",
                "code_status_other",
            ]

        missing = [c for c in feature_cols if c not in out.columns]
        if missing:
            raise RuntimeError(f"{name}: missing materialized context features {missing}")

        out = out[["case_id", "subject_id", "icustay_id", *feature_cols]].copy()
        local_path = local_root / spec["outcome"] / spec["filename"]
        out.to_csv(local_path, index=False)

        note_hash_frame = d[
            ["case_id", "icustay_id", "has_note", "note_time", "category"]
        ].copy()
        note_hash = context_audit.note_identity_hash(note_hash_frame)

        report["analyses"][name] = {
            "outcome": spec["outcome"],
            "source": spec["source"],
            "rows": int(len(out)),
            "unique_patients": int(out["subject_id"].nunique()),
            "local_feature_file": str(local_path),
            "local_feature_file_sha256": sha256_file(local_path),
            "note_identity_sha256": note_hash,
            "feature_count": int(len(feature_cols)),
            "features": feature_cols,
            "feature_summary": summarize_features(out, feature_cols),
        }

    report["guardrails"] = [
        "No clinical outcome model was fit or scored.",
        "No outcome label was used to select, transform, or drop a context feature.",
        "All treatment item IDs were filtered by the analysis row's source system.",
        "No invasive ventilator/intubation endpoint-defining item is present in the primary ventilation context block.",
        "CareVue medication features represent recent 6-hour exposure; MetaVision features represent active-at-landmark infusions.",
        "Row-level context features remain local; the declared artifact is aggregate only.",
    ]
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
