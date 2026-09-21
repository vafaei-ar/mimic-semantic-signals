from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd

from common import find_file, lower_columns, module_path, parse_datetime, read_columns, resolve_root


# Item 30125 is intentionally excluded pending the explicit dictionary audit in
# src/40_audit_structured_mappings.py.
CANONICAL_VASO_CV = {
    30043, 30044, 30046, 30047, 30051, 30119, 30120,
    30127, 30128, 30307, 30309,
}
CANONICAL_VASO_MV = {221289, 221662, 221749, 221906, 222315, 227692}

VITAL_ITEMIDS = {
    "heart_rate": {211, 220045},
    "map": {52, 456, 6702, 443, 220052, 220181, 225312},
    "resp_rate": {615, 618, 220210, 224690},
    "spo2": {646, 220277},
    "sbp": {51, 442, 455, 6701, 220050, 220179, 225309},
    "dbp": {8368, 8440, 8441, 8555, 220051, 220180, 225310},
}

LAB_ITEMIDS = {
    "lactate": {50813},
    "creatinine": {50912},
    "wbc": {51300, 51301},
}


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


def load_icustays(root: Path) -> pd.DataFrame:
    f = find_file(module_path(root, "mimiciii"), ["ICUSTAYS.csv.gz", "ICUSTAYS.csv"])
    if f is None:
        raise FileNotFoundError("MIMIC-III ICUSTAYS not found.")

    d = lower_columns(
        pd.read_csv(
            f,
            usecols=lambda c: str(c).lower()
            in {
                "subject_id",
                "hadm_id",
                "icustay_id",
                "dbsource",
                "first_careunit",
                "intime",
                "outtime",
            },
            low_memory=False,
        )
    )
    for c in ["subject_id", "hadm_id", "icustay_id"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["intime"] = parse_datetime(d["intime"])
    d["outtime"] = parse_datetime(d["outtime"])
    d = d.dropna(
        subset=["subject_id", "hadm_id", "icustay_id", "intime", "outtime"]
    ).copy()
    d[["subject_id", "hadm_id", "icustay_id"]] = d[
        ["subject_id", "hadm_id", "icustay_id"]
    ].astype("int64")
    d["icu_los_h"] = (d["outtime"] - d["intime"]).dt.total_seconds() / 3600.0
    d["person_key"] = d["subject_id"].astype(str)
    if "dbsource" not in d.columns:
        d["dbsource"] = "unknown"
    if "first_careunit" not in d.columns:
        d["first_careunit"] = "unknown"
    return d


def load_first_pressor_events(
    root: Path,
    icu: pd.DataFrame,
    include_item_30125: bool,
) -> pd.DataFrame:
    cv_ids = set(CANONICAL_VASO_CV)
    if include_item_30125:
        cv_ids.add(30125)

    pieces = []
    mv = find_file(
        module_path(root, "mimiciii"),
        ["INPUTEVENTS_MV.csv.gz", "INPUTEVENTS_MV.csv"],
    )
    if mv is not None:
        for chunk in read_columns(
            mv,
            ["hadm_id", "icustay_id", "itemid", "starttime", "statusdescription"],
            chunksize=300_000,
        ):
            c = lower_columns(chunk)
            c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
            c = c[c["itemid"].isin(CANONICAL_VASO_MV)].copy()
            if c.empty:
                continue
            if "statusdescription" in c:
                bad = c["statusdescription"].fillna("").astype(str).str.lower().str.contains(
                    "rewritten|cancelled"
                )
                c = c[~bad]
            c["hadm_id"] = pd.to_numeric(c["hadm_id"], errors="coerce")
            if "icustay_id" in c:
                c["icustay_id"] = pd.to_numeric(c["icustay_id"], errors="coerce")
            c["event_time"] = parse_datetime(c["starttime"])
            c = c.dropna(subset=["hadm_id", "event_time"])
            c["source"] = "metavision"
            pieces.append(
                c[
                    [
                        x
                        for x in ["hadm_id", "icustay_id", "event_time", "itemid", "source"]
                        if x in c.columns
                    ]
                ]
            )

    cv = find_file(
        module_path(root, "mimiciii"),
        ["INPUTEVENTS_CV.csv.gz", "INPUTEVENTS_CV.csv"],
    )
    if cv is not None:
        for chunk in read_columns(
            cv,
            ["hadm_id", "icustay_id", "itemid", "charttime"],
            chunksize=300_000,
        ):
            c = lower_columns(chunk)
            c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
            c = c[c["itemid"].isin(cv_ids)].copy()
            if c.empty:
                continue
            c["hadm_id"] = pd.to_numeric(c["hadm_id"], errors="coerce")
            if "icustay_id" in c:
                c["icustay_id"] = pd.to_numeric(c["icustay_id"], errors="coerce")
            c["event_time"] = parse_datetime(c["charttime"])
            c = c.dropna(subset=["hadm_id", "event_time"])
            c["source"] = "carevue"
            pieces.append(
                c[
                    [
                        x
                        for x in ["hadm_id", "icustay_id", "event_time", "itemid", "source"]
                        if x in c.columns
                    ]
                ]
            )

    if not pieces:
        raise RuntimeError("No curated MIMIC-III vasopressor events found.")

    events = pd.concat(pieces, ignore_index=True)

    # Assign events to ICU stays using icustay_id where available, otherwise
    # admission/time alignment. Keep only in-ICU events.
    exact = events.dropna(subset=["icustay_id"]).copy() if "icustay_id" in events else pd.DataFrame()
    if not exact.empty:
        exact["icustay_id"] = exact["icustay_id"].astype("int64")
        exact = exact.merge(
            icu[
                ["subject_id", "hadm_id", "icustay_id", "intime", "outtime"]
            ],
            on=["hadm_id", "icustay_id"],
            how="inner",
        )
        exact = exact[
            (exact["event_time"] >= exact["intime"])
            & (exact["event_time"] <= exact["outtime"])
        ].copy()

    missing = events[events.get("icustay_id", pd.Series(index=events.index, dtype=float)).isna()].copy()
    aligned_parts = []
    if not missing.empty:
        m = missing.merge(
            icu[
                ["subject_id", "hadm_id", "icustay_id", "intime", "outtime"]
            ],
            on="hadm_id",
            how="inner",
        )
        m = m[
            (m["event_time"] >= m["intime"])
            & (m["event_time"] <= m["outtime"])
        ].copy()
        aligned_parts.append(m)

    joined = pd.concat(
        [x for x in [exact] + aligned_parts if x is not None and not x.empty],
        ignore_index=True,
    )
    if joined.empty:
        raise RuntimeError("No vasopressor events aligned to MIMIC ICU stays.")

    joined["event_hour"] = (
        joined["event_time"] - joined["intime"]
    ).dt.total_seconds() / 3600.0

    first = (
        joined.sort_values(["icustay_id", "event_time"])
        .groupby("icustay_id", as_index=False)
        .first()
    )
    return first[
        ["icustay_id", "event_hour", "event_time", "itemid", "source"]
    ]


def match_risksets(
    icu: pd.DataFrame,
    events: pd.DataFrame,
    horizon_h: float,
    controls_per_case: int,
    seed: int,
) -> tuple[pd.DataFrame, dict]:
    rng = random.Random(seed)
    d = icu.merge(events, on="icustay_id", how="left")

    cases = d[
        d["event_hour"].notna()
        & (d["event_hour"] >= horizon_h)
        & (d["event_hour"] <= d["icu_los_h"])
    ].copy()
    cases["anchor_hour"] = cases["event_hour"] - horizon_h

    # One eligible case ICU stay per patient.
    cases = (
        cases.sort_values(["person_key", "event_time", "icustay_id"])
        .groupby("person_key", as_index=False)
        .first()
    )
    case_people = set(cases["person_key"].astype(str))

    controls = d[~d["person_key"].astype(str).isin(case_people)].copy()

    selected_cases = []
    selected_controls = []
    used_control_people: set[str] = set()

    for case in cases.sort_values(
        ["dbsource", "first_careunit", "anchor_hour", "icustay_id"]
    ).itertuples(index=False):
        anchor_h = float(case.anchor_hour)
        horizon_end = anchor_h + horizon_h

        avail = controls[
            (~controls["person_key"].astype(str).isin(used_control_people))
            & (controls["dbsource"].astype(str) == str(case.dbsource))
            & (controls["icu_los_h"] >= horizon_end)
            & (
                controls["event_hour"].isna()
                | (controls["event_hour"] > horizon_end)
            )
        ].copy()
        if avail.empty:
            continue

        avail["careunit_priority"] = (
            avail["first_careunit"].astype(str) != str(case.first_careunit)
        ).astype(int)
        avail["jitter"] = [rng.random() for _ in range(len(avail))]
        avail = (
            avail.sort_values(
                ["careunit_priority", "jitter", "icustay_id"]
            )
            .drop_duplicates("person_key")
        )
        take = avail.head(controls_per_case).copy()
        if len(take) < controls_per_case:
            continue

        selected_cases.append(case._asdict())
        take["anchor_hour"] = anchor_h
        selected_controls.append(take)
        used_control_people.update(take["person_key"].astype(str).tolist())

    if not selected_cases:
        raise RuntimeError("No fully matched MIMIC exact-6h risk sets found.")

    case_df = pd.DataFrame(selected_cases)
    control_df = pd.concat(selected_controls, ignore_index=True)

    case_df["label"] = 1
    control_df["label"] = 0
    case_df["match_set"] = np.arange(1, len(case_df) + 1)
    control_df["match_set"] = np.repeat(
        np.arange(1, len(case_df) + 1), controls_per_case
    )

    snapshots = pd.concat([case_df, control_df], ignore_index=True, sort=False)
    snapshots = snapshots.reset_index(drop=True)
    snapshots["snapshot_id"] = [
        f"s{i:06d}" for i in range(1, len(snapshots) + 1)
    ]

    people = sorted(snapshots["person_key"].astype(str).unique())
    pmap = {p: f"p{i:06d}" for i, p in enumerate(people, 1)}
    snapshots["patient_group"] = snapshots["person_key"].astype(str).map(pmap)

    report = {
        "eligible_case_patients": int(cases["person_key"].nunique()),
        "matched_cases": int((snapshots["label"] == 1).sum()),
        "matched_controls": int((snapshots["label"] == 0).sum()),
        "total_snapshots": int(len(snapshots)),
        "unique_patients": int(snapshots["patient_group"].nunique()),
        "controls_per_case": controls_per_case,
        "prediction_horizon_hours": horizon_h,
        "case_anchor_hour": quantiles(
            snapshots.loc[snapshots["label"] == 1, "anchor_hour"]
        ),
        "case_dbsource": (
            snapshots.loc[snapshots["label"] == 1, "dbsource"]
            .astype(str)
            .value_counts()
            .astype(int)
            .to_dict()
        ),
        "case_itemid": (
            snapshots.loc[snapshots["label"] == 1, "itemid"]
            .dropna()
            .astype(int)
            .astype(str)
            .value_counts()
            .astype(int)
            .to_dict()
        ),
    }
    return snapshots, report


def extract_features(
    root: Path,
    snapshots: pd.DataFrame,
    vital_lookback_h: float,
    lab_lookback_h: float,
) -> pd.DataFrame:
    snap = snapshots[
        ["snapshot_id", "hadm_id", "icustay_id", "intime", "anchor_hour"]
    ].copy()
    snap["anchor_time"] = snap["intime"] + pd.to_timedelta(
        snap["anchor_hour"], unit="h"
    )

    stays = set(snap["icustay_id"].astype(int))
    hadms = set(snap["hadm_id"].astype(int))
    stay_map = snap.set_index("icustay_id")["snapshot_id"].to_dict()
    anchor_stay = snap.set_index("icustay_id")["anchor_time"].to_dict()

    all_vital_ids = set().union(*VITAL_ITEMIDS.values())
    chart = find_file(
        module_path(root, "mimiciii"),
        ["CHARTEVENTS.csv.gz", "CHARTEVENTS.csv"],
    )
    vparts = []
    if chart is not None:
        for chunk in read_columns(
            chart,
            ["icustay_id", "itemid", "charttime", "valuenum", "error"],
            chunksize=500_000,
        ):
            c = lower_columns(chunk)
            c["icustay_id"] = pd.to_numeric(c["icustay_id"], errors="coerce")
            c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
            c = c[
                c["icustay_id"].isin(stays)
                & c["itemid"].isin(all_vital_ids)
            ].copy()
            if c.empty:
                continue
            if "error" in c:
                c = c[c["error"].fillna(0).astype(str) != "1"]
            c["charttime"] = parse_datetime(c["charttime"])
            c["valuenum"] = pd.to_numeric(c["valuenum"], errors="coerce")
            c = c.dropna(subset=["icustay_id", "charttime", "valuenum"])
            if not c.empty:
                vparts.append(
                    c[["icustay_id", "itemid", "charttime", "valuenum"]]
                )

    vitals = pd.concat(vparts, ignore_index=True) if vparts else pd.DataFrame()
    out = pd.DataFrame({"snapshot_id": snapshots["snapshot_id"]})

    if not vitals.empty:
        vitals["anchor_time"] = vitals["icustay_id"].map(anchor_stay)
        vitals["snapshot_id"] = vitals["icustay_id"].map(stay_map)
        vitals = vitals[
            (vitals["charttime"] <= vitals["anchor_time"])
            & (
                vitals["charttime"]
                >= vitals["anchor_time"]
                - pd.to_timedelta(vital_lookback_h, unit="h")
            )
        ].copy()

        for feature, ids in VITAL_ITEMIDS.items():
            q = vitals[vitals["itemid"].isin(ids)].sort_values(
                ["snapshot_id", "charttime"]
            )
            if q.empty:
                out[f"{feature}_last"] = np.nan
                out[f"{feature}_delta"] = np.nan
                continue
            g = q.groupby("snapshot_id")["valuenum"]
            last = g.last()
            first = g.first()
            count = g.count()
            delta = (last - first).where(count >= 2, np.nan)
            stats = pd.DataFrame(
                {
                    "snapshot_id": last.index,
                    f"{feature}_last": last.values,
                    f"{feature}_delta": delta.values,
                }
            )
            out = out.merge(stats, on="snapshot_id", how="left")
    else:
        for feature in VITAL_ITEMIDS:
            out[f"{feature}_last"] = np.nan
            out[f"{feature}_delta"] = np.nan

    lab = find_file(
        module_path(root, "mimiciii"),
        ["LABEVENTS.csv.gz", "LABEVENTS.csv"],
    )
    all_lab_ids = set().union(*LAB_ITEMIDS.values())
    lparts = []
    if lab is not None:
        for chunk in read_columns(
            lab,
            ["hadm_id", "itemid", "charttime", "valuenum"],
            chunksize=500_000,
        ):
            c = lower_columns(chunk)
            c["hadm_id"] = pd.to_numeric(c["hadm_id"], errors="coerce")
            c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
            c = c[
                c["hadm_id"].isin(hadms)
                & c["itemid"].isin(all_lab_ids)
            ].copy()
            if c.empty:
                continue
            c["charttime"] = parse_datetime(c["charttime"])
            c["valuenum"] = pd.to_numeric(c["valuenum"], errors="coerce")
            c = c.dropna(subset=["hadm_id", "charttime", "valuenum"])
            if not c.empty:
                lparts.append(
                    c[["hadm_id", "itemid", "charttime", "valuenum"]]
                )

    labs = pd.concat(lparts, ignore_index=True) if lparts else pd.DataFrame()
    if not labs.empty:
        snap_hadm = snap[["snapshot_id", "hadm_id", "anchor_time"]].copy()
        labs = labs.merge(snap_hadm, on="hadm_id", how="inner")
        labs = labs[
            (labs["charttime"] <= labs["anchor_time"])
            & (
                labs["charttime"]
                >= labs["anchor_time"]
                - pd.to_timedelta(lab_lookback_h, unit="h")
            )
        ].copy()

        for feature, ids in LAB_ITEMIDS.items():
            q = labs[labs["itemid"].isin(ids)].sort_values(
                ["snapshot_id", "charttime"]
            )
            if q.empty:
                out[f"{feature}_last"] = np.nan
                out[f"{feature}_delta"] = np.nan
                continue
            g = q.groupby("snapshot_id")["valuenum"]
            last = g.last()
            first = g.first()
            count = g.count()
            delta = (last - first).where(count >= 2, np.nan)
            stats = pd.DataFrame(
                {
                    "snapshot_id": last.index,
                    f"{feature}_last": last.values,
                    f"{feature}_delta": delta.values,
                }
            )
            out = out.merge(stats, on="snapshot_id", how="left")
    else:
        for feature in LAB_ITEMIDS:
            out[f"{feature}_last"] = np.nan
            out[f"{feature}_delta"] = np.nan

    return out


def missingness_report(df: pd.DataFrame) -> dict:
    excluded = {
        "snapshot_id",
        "label",
        "match_set",
        "patient_group",
        "dbsource",
        "first_careunit",
        "anchor_hour",
    }
    feature_cols = [c for c in df.columns if c not in excluded]
    return {
        "overall_fraction_missing": {
            c: float(df[c].isna().mean()) for c in feature_cols
        },
        "by_label_fraction_missing": {
            str(label): {
                c: float(df.loc[df["label"] == label, c].isna().mean())
                for c in feature_cols
            }
            for label in [0, 1]
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Build a local-only exact-6h MIMIC-III structured vasopressor risk-set "
            "cohort for physiology transport modeling."
        )
    )
    ap.add_argument("--root", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--controls-per-case", type=int, default=3)
    ap.add_argument("--prediction-horizon-hours", type=float, default=6.0)
    ap.add_argument("--vital-lookback-hours", type=float, default=6.0)
    ap.add_argument("--lab-lookback-hours", type=float, default=24.0)
    ap.add_argument("--seed", type=int, default=20260921)
    ap.add_argument(
        "--include-item-30125",
        action="store_true",
        help="Include CareVue item 30125 only if the dictionary audit confirms it is a vasopressor.",
    )
    args = ap.parse_args()

    root = resolve_root(args.root)
    outdir = Path(args.output_dir).expanduser().resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    icu = load_icustays(root)
    events = load_first_pressor_events(
        root, icu, include_item_30125=args.include_item_30125
    )
    snapshots, cohort_report = match_risksets(
        icu,
        events,
        horizon_h=float(args.prediction_horizon_hours),
        controls_per_case=args.controls_per_case,
        seed=args.seed,
    )

    features = extract_features(
        root,
        snapshots,
        vital_lookback_h=args.vital_lookback_hours,
        lab_lookback_h=args.lab_lookback_hours,
    )

    safe = snapshots[
        [
            "snapshot_id",
            "label",
            "match_set",
            "patient_group",
            "dbsource",
            "first_careunit",
            "anchor_hour",
        ]
    ].merge(features, on="snapshot_id", how="left")

    feature_path = outdir / "mimic_exact6h_structured_riskset_features.csv"
    safe.to_csv(feature_path, index=False)

    report = {
        "contains_note_text": False,
        "contains_source_patient_identifiers": False,
        "patient_level_feature_file_shared_as_artifact": False,
        "analysis_role": (
            "MIMIC structured development cohort aligned to the exact-6h external "
            "landmark design; separate from the note-anchored semantic cohort"
        ),
        "endpoint": "first canonical vasopressor initiation during ICU stay",
        "item_30125_included": bool(args.include_item_30125),
        "case_definition": (
            f"first canonical vasopressor start at least "
            f"{args.prediction_horizon_hours:g}h after ICU admission; anchor exactly "
            f"{args.prediction_horizon_hours:g}h before first start"
        ),
        "control_definition": (
            f"same-dbsource risk-set control at the same ICU elapsed time, with no "
            f"prior pressor and no first start during the next "
            f"{args.prediction_horizon_hours:g}h; later treatment allowed"
        ),
        "matching": (
            "case patients excluded from controls; controls used once; same dbsource "
            "required; same first care unit prioritized; 3 controls per case by default"
        ),
        "prediction_horizon_hours": args.prediction_horizon_hours,
        "vital_lookback_hours": args.vital_lookback_hours,
        "lab_lookback_hours": args.lab_lookback_hours,
        "trend_definition": (
            "delta = last minus first within lookback; requires at least two "
            "measurements, otherwise missing"
        ),
        "cohort": cohort_report,
        "missingness": missingness_report(safe),
        "local_feature_file": feature_path.name,
        "next_step": (
            "Freeze a common cross-dataset feature set before model fitting; train "
            "the physiology transport model in this MIMIC exact-6h cohort and apply "
            "without refitting to eICU and NWICU."
        ),
    }

    report_path = outdir / "mimic_exact6h_structured_report.json"
    report_path.write_text(
        json.dumps(report, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
