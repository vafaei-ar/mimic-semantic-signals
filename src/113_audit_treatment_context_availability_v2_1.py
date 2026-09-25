from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from common import find_file, lower_columns, module_path, parse_datetime, read_columns, resolve_root
from runrelay_progress import update_progress


OUTCOMES = ("invasive_ventilation", "renal_replacement_therapy", "icu_death")
LOOKBACK_H = 6.0

# Respiratory-support candidates chosen from the model-free D_ITEMS audit.
RESP_IDS = {
    "fio2": {
        "carevue": {189, 190, 191, 727, 2981, 3420, 3422, 7570},
        "metavision": {223835},
    },
    "oxygen_flow": {
        "carevue": {470, 471},
        "metavision": {223834, 227287, 227582},
    },
    "oxygen_device": {
        "carevue": {467, 468},
        "metavision": {226732},
    },
    "niv_evidence": {
        "carevue": {63, 64, 65, 66, 67, 68, 1040, 1457, 1914, 2866, 3111, 5850, 6060, 6875},
        "metavision": {227577, 227578, 227579, 227580, 227581, 227582, 227583},
    },
}
CODE_STATUS_IDS = {"carevue": {128}, "metavision": {223758}}

# Existing curated vasopressor mappings from the repository's MIMIC endpoint work.
VASO_IDS = {
    "carevue": {
        "dopamine": {30043, 30307},
        "epinephrine": {30044, 30119, 30309},
        "norepinephrine": {30047, 30120},
        "phenylephrine": {30127, 30128},
        "vasopressin": {30051},
    },
    "metavision": {
        "epinephrine": {221289},
        "dopamine": {221662},
        "phenylephrine": {221749},
        "norepinephrine": {221906},
        "vasopressin": {222315},
    },
}

# Conservative continuous/infusion-capable sedative/analgesic candidates.
SEDATIVE_IDS = {
    "carevue": {
        "fentanyl": {30118, 30308},
        "midazolam": {30124},
        "propofol": {30131},
        "dexmedetomidine": {30167},
    },
    "metavision": {
        "midazolam": {221668},
        "fentanyl": {221744, 225942},
        "propofol": {222168},
        "dexmedetomidine": {225150},
    },
}

ALL_ITEMIDS = set()
for source_map in RESP_IDS.values():
    for ids in source_map.values():
        ALL_ITEMIDS |= ids
for ids in CODE_STATUS_IDS.values():
    ALL_ITEMIDS |= ids
for source_map in (VASO_IDS, SEDATIVE_IDS):
    for agent_map in source_map.values():
        for ids in agent_map.values():
            ALL_ITEMIDS |= ids


def source_for_item(itemid: int) -> str | None:
    for concept_map in RESP_IDS.values():
        for source, ids in concept_map.items():
            if itemid in ids:
                return source
    for source, ids in CODE_STATUS_IDS.items():
        if itemid in ids:
            return source
    for source_map in (VASO_IDS, SEDATIVE_IDS):
        for source, agent_map in source_map.items():
            if any(itemid in ids for ids in agent_map.values()):
                return source
    return None


def load_indices(local_root: Path) -> dict[str, pd.DataFrame]:
    out = {}
    for outcome in OUTCOMES:
        d = pd.read_csv(local_root / outcome / "population_index_local.csv", low_memory=False)
        for c in ["subject_id", "hadm_id", "icustay_id"]:
            d[c] = pd.to_numeric(d[c], errors="raise").astype("int64")
        d["landmark_time"] = pd.to_datetime(d["landmark_time"], errors="raise")
        d["dbsource"] = d["dbsource"].fillna("unknown").astype(str).str.strip().str.lower()
        out[outcome] = d
    return out


def audit_dictionary(root: Path) -> dict:
    f = find_file(module_path(root, "mimiciii"), ["D_ITEMS.csv.gz", "D_ITEMS.csv"])
    if f is None:
        raise FileNotFoundError("D_ITEMS not found")
    d = lower_columns(pd.read_csv(f, low_memory=False))
    d["itemid"] = pd.to_numeric(d["itemid"], errors="coerce")
    d = d[d["itemid"].isin(ALL_ITEMIDS)].copy()
    d["itemid"] = d["itemid"].astype(int)
    for c in ["label", "dbsource", "linksto", "category", "unitname"]:
        if c not in d:
            d[c] = ""
        d[c] = d[c].fillna("").astype(str)

    found = set(d["itemid"])
    rows = d[["itemid", "label", "dbsource", "linksto", "category", "unitname"]].sort_values("itemid")
    records = []
    for rec in rows.to_dict(orient="records"):
        rec["expected_source"] = source_for_item(int(rec["itemid"]))
        records.append(rec)
    return {
        "expected_itemids": sorted(ALL_ITEMIDS),
        "missing_itemids": sorted(ALL_ITEMIDS - found),
        "items": records,
    }


def chartevent_audit(root: Path, indices: dict[str, pd.DataFrame]) -> dict:
    f = find_file(module_path(root, "mimiciii"), ["CHARTEVENTS.csv.gz", "CHARTEVENTS.csv"])
    if f is None:
        raise FileNotFoundError("CHARTEVENTS not found")

    union = pd.concat(
        [
            d[["icustay_id", "landmark_time", "dbsource"]].assign(outcome=o)
            for o, d in indices.items()
        ],
        ignore_index=True,
    )
    wanted_icu = set(union["icustay_id"].astype(int))
    char_ids = set()
    for concept_map in RESP_IDS.values():
        for ids in concept_map.values():
            char_ids |= ids
    for ids in CODE_STATUS_IDS.values():
        char_ids |= ids

    pieces = []
    for chunk in read_columns(
        f,
        ["icustay_id", "itemid", "charttime", "valuenum", "value", "error"],
        chunksize=500_000,
    ):
        c = lower_columns(chunk)
        c["icustay_id"] = pd.to_numeric(c["icustay_id"], errors="coerce")
        c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
        c = c[c["icustay_id"].isin(wanted_icu) & c["itemid"].isin(char_ids)].copy()
        if c.empty:
            continue
        if "error" in c:
            bad = pd.to_numeric(c["error"], errors="coerce").fillna(0).ne(0)
            c = c[~bad].copy()
        c["charttime"] = parse_datetime(c["charttime"])
        c = c.dropna(subset=["charttime"])
        c["icustay_id"] = c["icustay_id"].astype("int64")
        c["itemid"] = c["itemid"].astype(int)
        pieces.append(c[["icustay_id", "itemid", "charttime", "valuenum", "value"]])

    ev = pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame(
        columns=["icustay_id", "itemid", "charttime", "valuenum", "value"]
    )

    reports = {}
    for outcome, idx in indices.items():
        base = idx[["icustay_id", "landmark_time", "dbsource"]].copy()
        m = ev.merge(base, on="icustay_id", how="inner")
        lower = m["landmark_time"] - pd.to_timedelta(LOOKBACK_H, unit="h")
        pre6 = m[(m["charttime"] >= lower) & (m["charttime"] <= m["landmark_time"])].copy()
        allpre = m[m["charttime"] <= m["landmark_time"]].copy()

        r = {"rows": int(len(idx)), "features": {}, "code_status": {}}
        for concept in ("fio2", "oxygen_flow", "oxygen_device", "niv_evidence"):
            ids = set()
            for source, source_ids in RESP_IDS[concept].items():
                ids |= source_ids
            q = pre6[pre6["itemid"].isin(ids)].copy()
            available = set(q["icustay_id"].astype(int))
            r["features"][concept] = {
                "rows_available": int(idx["icustay_id"].isin(available).sum()),
                "availability_fraction": float(idx["icustay_id"].isin(available).mean()),
                "event_rows": int(len(q)),
                "item_counts": {
                    str(int(k)): int(v)
                    for k, v in q["itemid"].value_counts().sort_index().items()
                },
            }

        # High-flow and NIV strings in the dedicated delivery-device fields.
        device_ids = set().union(*RESP_IDS["oxygen_device"].values())
        dq = pre6[pre6["itemid"].isin(device_ids)].copy()
        vals = dq["value"].fillna("").astype(str).str.strip().str.lower()
        high_flow = vals.str.contains(r"high.?flow|hfnc|vapotherm|optiflow", regex=True, na=False)
        niv = vals.str.contains(r"bipap|bi-pap|cpap|non.?invasive", regex=True, na=False)
        r["features"]["high_flow_device_string"] = {
            "event_rows": int(high_flow.sum()),
            "icu_stays": int(dq.loc[high_flow, "icustay_id"].nunique()),
        }
        r["features"]["niv_device_string"] = {
            "event_rows": int(niv.sum()),
            "icu_stays": int(dq.loc[niv, "icustay_id"].nunique()),
        }

        code_ids = set().union(*CODE_STATUS_IDS.values())
        cq = allpre[allpre["itemid"].isin(code_ids)].sort_values(["icustay_id", "charttime"])
        latest = cq.groupby("icustay_id", as_index=False).last() if not cq.empty else cq
        counts = latest["value"].fillna("MISSING").astype(str).str.strip().value_counts()
        r["code_status"] = {
            "rows_available": int(len(latest)),
            "availability_fraction": float(len(latest) / len(idx)) if len(idx) else None,
            "latest_value_counts": {
                str(k): int(v) for k, v in counts.items() if int(v) >= 5
            },
            "suppressed_rare_total": int(sum(int(v) for v in counts.values if int(v) < 5)),
        }
        reports[outcome] = r

    return reports


def _agent_lookup(mapping: dict[str, set[int]]) -> dict[int, str]:
    out = {}
    for agent, ids in mapping.items():
        for itemid in ids:
            out[int(itemid)] = agent
    return out


def inputevent_audit(root: Path, indices: dict[str, pd.DataFrame]) -> dict:
    union = pd.concat(
        [
            d[["icustay_id", "landmark_time", "dbsource"]].assign(outcome=o)
            for o, d in indices.items()
        ],
        ignore_index=True,
    )
    wanted_icu = set(union["icustay_id"].astype(int))

    mv_lookup = {}
    mv_lookup.update(_agent_lookup(VASO_IDS["metavision"]))
    mv_sed = _agent_lookup(SEDATIVE_IDS["metavision"])
    cv_lookup = {}
    cv_lookup.update(_agent_lookup(VASO_IDS["carevue"]))
    cv_sed = _agent_lookup(SEDATIVE_IDS["carevue"])

    mv_file = find_file(module_path(root, "mimiciii"), ["INPUTEVENTS_MV.csv.gz", "INPUTEVENTS_MV.csv"])
    cv_file = find_file(module_path(root, "mimiciii"), ["INPUTEVENTS_CV.csv.gz", "INPUTEVENTS_CV.csv"])

    mv_rows = []
    if mv_file is not None:
        wanted = set(mv_lookup) | set(mv_sed)
        for chunk in read_columns(
            mv_file,
            ["icustay_id", "itemid", "starttime", "endtime", "rate", "statusdescription"],
            chunksize=250_000,
        ):
            c = lower_columns(chunk)
            c["icustay_id"] = pd.to_numeric(c["icustay_id"], errors="coerce")
            c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
            c = c[c["icustay_id"].isin(wanted_icu) & c["itemid"].isin(wanted)].copy()
            if c.empty:
                continue
            bad = c["statusdescription"].fillna("").astype(str).str.lower().str.contains("rewritten|cancelled")
            c = c[~bad].copy()
            c["starttime"] = parse_datetime(c["starttime"])
            c["endtime"] = parse_datetime(c["endtime"])
            c["rate"] = pd.to_numeric(c["rate"], errors="coerce")
            c = c.dropna(subset=["starttime", "endtime"])
            c["icustay_id"] = c["icustay_id"].astype("int64")
            c["itemid"] = c["itemid"].astype(int)
            c["kind"] = np.where(c["itemid"].isin(set(mv_lookup)), "vasoactive", "sedative")
            c["agent"] = c["itemid"].map({**mv_lookup, **mv_sed})
            mv_rows.append(c[["icustay_id", "itemid", "starttime", "endtime", "rate", "kind", "agent"]])
    mv = pd.concat(mv_rows, ignore_index=True) if mv_rows else pd.DataFrame()

    cv_rows = []
    if cv_file is not None:
        wanted = set(cv_lookup) | set(cv_sed)
        for chunk in read_columns(
            cv_file,
            ["icustay_id", "itemid", "charttime", "rate"],
            chunksize=250_000,
        ):
            c = lower_columns(chunk)
            c["icustay_id"] = pd.to_numeric(c["icustay_id"], errors="coerce")
            c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
            c = c[c["icustay_id"].isin(wanted_icu) & c["itemid"].isin(wanted)].copy()
            if c.empty:
                continue
            c["charttime"] = parse_datetime(c["charttime"])
            c["rate"] = pd.to_numeric(c["rate"], errors="coerce")
            c = c.dropna(subset=["charttime"])
            c["icustay_id"] = c["icustay_id"].astype("int64")
            c["itemid"] = c["itemid"].astype(int)
            c["kind"] = np.where(c["itemid"].isin(set(cv_lookup)), "vasoactive", "sedative")
            c["agent"] = c["itemid"].map({**cv_lookup, **cv_sed})
            cv_rows.append(c[["icustay_id", "itemid", "charttime", "rate", "kind", "agent"]])
    cv = pd.concat(cv_rows, ignore_index=True) if cv_rows else pd.DataFrame()

    reports = {}
    for outcome, idx in indices.items():
        outcome_report = {
            "metavision_active_at_landmark": {},
            "carevue_recent_6h": {},
        }

        mv_idx = idx[idx["dbsource"].eq("metavision")][["icustay_id", "landmark_time"]].copy()
        if not mv.empty and not mv_idx.empty:
            m = mv.merge(mv_idx, on="icustay_id", how="inner")
            active = m[
                (m["starttime"] <= m["landmark_time"])
                & (m["endtime"] > m["landmark_time"])
                & (m["rate"].isna() | m["rate"].gt(0))
            ].copy()
        else:
            active = pd.DataFrame(columns=["icustay_id", "kind", "agent", "itemid", "rate"])

        for kind in ("vasoactive", "sedative"):
            q = active[active["kind"].eq(kind)] if not active.empty else active
            ids = set(q["icustay_id"].astype(int)) if not q.empty else set()
            agents_per = q.groupby("icustay_id")["agent"].nunique() if not q.empty else pd.Series(dtype=float)
            outcome_report["metavision_active_at_landmark"][kind] = {
                "source_rows": int(len(mv_idx)),
                "rows_exposed": int(mv_idx["icustay_id"].isin(ids).sum()),
                "exposure_fraction": float(mv_idx["icustay_id"].isin(ids).mean()) if len(mv_idx) else None,
                "event_rows": int(len(q)),
                "agent_counts": {
                    str(k): int(v) for k, v in q["agent"].value_counts().items()
                } if not q.empty else {},
                "rows_with_multiple_agents": int((agents_per > 1).sum()) if len(agents_per) else 0,
                "rate_nonmissing_fraction": float(q["rate"].notna().mean()) if len(q) else None,
            }

        cv_idx = idx[idx["dbsource"].eq("carevue")][["icustay_id", "landmark_time"]].copy()
        if not cv.empty and not cv_idx.empty:
            c = cv.merge(cv_idx, on="icustay_id", how="inner")
            lower = c["landmark_time"] - pd.to_timedelta(LOOKBACK_H, unit="h")
            recent = c[
                (c["charttime"] >= lower)
                & (c["charttime"] <= c["landmark_time"])
                & (c["rate"].isna() | c["rate"].gt(0))
            ].copy()
        else:
            recent = pd.DataFrame(columns=["icustay_id", "kind", "agent", "itemid", "rate"])

        for kind in ("vasoactive", "sedative"):
            q = recent[recent["kind"].eq(kind)] if not recent.empty else recent
            ids = set(q["icustay_id"].astype(int)) if not q.empty else set()
            agents_per = q.groupby("icustay_id")["agent"].nunique() if not q.empty else pd.Series(dtype=float)
            outcome_report["carevue_recent_6h"][kind] = {
                "source_rows": int(len(cv_idx)),
                "rows_exposed": int(cv_idx["icustay_id"].isin(ids).sum()),
                "exposure_fraction": float(cv_idx["icustay_id"].isin(ids).mean()) if len(cv_idx) else None,
                "event_rows": int(len(q)),
                "agent_counts": {
                    str(k): int(v) for k, v in q["agent"].value_counts().items()
                } if not q.empty else {},
                "rows_with_multiple_agents": int((agents_per > 1).sum()) if len(agents_per) else 0,
                "rate_nonmissing_fraction": float(q["rate"].notna().mean()) if len(q) else None,
            }

        reports[outcome] = outcome_report

    return {
        "outcomes": reports,
        "representation_rule": {
            "metavision": "active infusion at landmark: starttime <= landmark < endtime, non-cancelled/rewritten, positive rate when rate is recorded",
            "carevue": "recent candidate infusion charted within 6h before landmark; duration is not reliably represented, so this is exposure rather than confirmed active-at-landmark state",
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Model-free treatment/support/code-status availability audit for corrected v2.1 cohorts.")
    ap.add_argument("--root", required=True)
    ap.add_argument("--local-root", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    root = resolve_root(args.root)
    local_root = Path(args.local_root).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    update_progress(current=1, total=4, phase="treatment_context", message="Loading corrected cohort indices and validating frozen candidate item dictionaries", unit="stage")
    indices = load_indices(local_root)
    dictionary = audit_dictionary(root)

    update_progress(current=2, total=4, phase="treatment_context", message="Auditing pre-landmark respiratory support and code status", unit="stage")
    chart = chartevent_audit(root, indices)

    update_progress(current=3, total=4, phase="treatment_context", message="Auditing vasoactive and sedative exposure timing", unit="stage")
    inputs = inputevent_audit(root, indices)

    update_progress(current=4, total=4, phase="treatment_context", message="Writing aggregate treatment-context availability audit", unit="stage")
    report = {
        "analysis": "v2.1 preregistration treatment/support/code-status availability audit",
        "outcome_performance_computed": False,
        "outcome_labels_used_for_feature_selection": False,
        "lookback_hours": LOOKBACK_H,
        "dictionary_validation": dictionary,
        "chartevent_availability": chart,
        "inputevent_availability": inputs,
        "candidate_feature_families": [
            "latest FiO2 in prior 6h",
            "latest oxygen flow in prior 6h",
            "oxygen delivery device/support category in prior 6h",
            "high-flow indicator from delivery-device text",
            "non-invasive ventilation indicator",
            "any vasoactive exposure and active-agent count",
            "sedative/analgesic exposure",
            "last code status before landmark for ICU death",
        ],
        "guardrails": [
            "No clinical outcome performance was computed.",
            "No feature was selected or dropped using outcome labels.",
            "No post-landmark treatment information was used.",
            "Invasive ventilator/intubation endpoint-defining item IDs are absent from the candidate predictor map.",
            "CareVue and MetaVision medication timing representations are reported separately rather than silently equated.",
        ],
    }
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
