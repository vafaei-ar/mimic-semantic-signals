from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

from common import find_file, lower_columns, module_path, parse_datetime, read_columns
from registration_gate import require_osf_registration
from runrelay_progress import update_progress


OUTCOMES = ("invasive_ventilation", "renal_replacement_therapy", "icu_death")
CHAR_FEATURES = (
    "heart_rate_last", "heart_rate_delta",
    "sbp_last", "sbp_delta",
    "dbp_last", "dbp_delta",
    "map_last", "map_delta",
    "resp_rate_last", "resp_rate_delta",
    "spo2_last", "spo2_delta",
    "temperature_c_last", "temperature_c_delta",
    "gcs_eye_last", "gcs_verbal_last", "gcs_motor_last",
)


def load_numbered_module(filename: str, name: str):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {filename}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


base_mod = load_numbered_module("105_build_enhanced_structured_baseline_v2_1.py", "structured_v2_1")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_chartevents_storetime(root: Path, unique: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    f = find_file(module_path(root, "mimiciii"), ["CHARTEVENTS.csv.gz", "CHARTEVENTS.csv"])
    if f is None:
        raise FileNotFoundError("CHARTEVENTS not found")

    vital_map = base_mod.build_item_map(base_mod.VITAL_IDS)
    gcs_map = base_mod.build_item_map(base_mod.GCS_IDS)
    all_ids = set(vital_map) | base_mod.TEMP_C_IDS | base_mod.TEMP_F_IDS | set(gcs_map)
    stays = set(unique["icustay_id"].tolist())
    lookup = unique[["icustay_id", "landmark_time"]]

    rows = []
    counters = {
        "candidate_rows": 0,
        "in_window_rows_before_storetime_filter": 0,
        "missing_storetime_rows_excluded": 0,
        "storetime_after_landmark_rows_excluded": 0,
        "storetime_at_or_before_landmark_rows_retained": 0,
        "error_rows_excluded": 0,
        "out_of_range_rows_excluded": 0,
        "gcs_verbal_airway_rows_excluded": 0,
    }

    for chunk in read_columns(
        f,
        ["icustay_id", "itemid", "charttime", "storetime", "valuenum", "value", "error"],
        chunksize=600_000,
    ):
        c = lower_columns(chunk)
        if "storetime" not in c.columns:
            raise RuntimeError("CHARTEVENTS storetime column is unavailable; registered sensitivity cannot be run")
        c["icustay_id"] = pd.to_numeric(c["icustay_id"], errors="coerce")
        c = c[c["icustay_id"].isin(stays)].copy()
        if c.empty:
            continue
        c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
        c = c[c["itemid"].isin(all_ids)].copy()
        if c.empty:
            continue
        counters["candidate_rows"] += int(len(c))

        if "error" in c.columns:
            ok = base_mod.numeric_zero_mask(c["error"])
            counters["error_rows_excluded"] += int((~ok).sum())
            c = c[ok].copy()

        c["charttime"] = parse_datetime(c["charttime"])
        c["storetime"] = parse_datetime(c["storetime"])
        c["valuenum"] = pd.to_numeric(c["valuenum"], errors="coerce")
        c = c.dropna(subset=["icustay_id", "itemid", "charttime", "valuenum"]).copy()
        if c.empty:
            continue
        c["icustay_id"] = c["icustay_id"].astype("int64")
        c["itemid"] = c["itemid"].astype(int)
        c = c.merge(lookup, on="icustay_id", how="inner")
        c = c[
            (c["charttime"] <= c["landmark_time"])
            & (c["charttime"] >= c["landmark_time"] - pd.to_timedelta(base_mod.VITAL_LOOKBACK_H, unit="h"))
        ].copy()
        if c.empty:
            continue

        counters["in_window_rows_before_storetime_filter"] += int(len(c))
        missing_store = c["storetime"].isna()
        late_store = c["storetime"].notna() & c["storetime"].gt(c["landmark_time"])
        keep_store = c["storetime"].notna() & c["storetime"].le(c["landmark_time"])
        counters["missing_storetime_rows_excluded"] += int(missing_store.sum())
        counters["storetime_after_landmark_rows_excluded"] += int(late_store.sum())
        counters["storetime_at_or_before_landmark_rows_retained"] += int(keep_store.sum())
        c = c[keep_store].copy()
        if c.empty:
            continue

        feature = []
        value = []
        valid = []
        for row in c.itertuples(index=False):
            itemid = int(row.itemid)
            v = float(row.valuenum)
            if itemid in vital_map:
                name = vital_map[itemid]
                good = bool(base_mod.valid_vital(name, pd.Series([v])).iloc[0])
                feature.append(name)
                value.append(v)
                valid.append(good)
            elif itemid in base_mod.TEMP_C_IDS:
                feature.append("temperature_c")
                value.append(v)
                valid.append(bool(10 < v < 50))
            elif itemid in base_mod.TEMP_F_IDS:
                feature.append("temperature_c")
                value.append((v - 32.0) / 1.8)
                valid.append(bool(70 < v < 120))
            elif itemid in gcs_map:
                name = gcs_map[itemid]
                bounds = {"gcs_eye": (1, 4), "gcs_verbal": (1, 5), "gcs_motor": (1, 6)}
                lo, hi = bounds[name]
                airway_coded = name == "gcs_verbal" and base_mod.is_gcs_verbal_airway_value(
                    getattr(row, "value", "")
                )
                if airway_coded:
                    counters["gcs_verbal_airway_rows_excluded"] += 1
                feature.append(name)
                value.append(v)
                valid.append(bool((lo <= v <= hi) and not airway_coded))
            else:
                raise RuntimeError(f"Unexpected CHARTEVENTS item {itemid}")

        c["feature"] = feature
        c["clean_value"] = value
        c["valid"] = valid
        counters["out_of_range_rows_excluded"] += int((~c["valid"]).sum())
        c = c[c["valid"]].copy()
        if not c.empty:
            rows.append(c[["icustay_id", "feature", "charttime", "clean_value"]])

    data = (
        pd.concat(rows, ignore_index=True)
        if rows
        else pd.DataFrame(columns=["icustay_id", "feature", "charttime", "clean_value"])
    )
    if not data.empty:
        data = (
            data.groupby(["icustay_id", "feature", "charttime"], as_index=False)["clean_value"]
            .mean()
        )

    denom = int(counters["in_window_rows_before_storetime_filter"])
    counters["missing_storetime_fraction_in_window"] = (
        float(counters["missing_storetime_rows_excluded"] / denom) if denom else None
    )
    counters["late_storetime_fraction_in_window"] = (
        float(counters["storetime_after_landmark_rows_excluded"] / denom) if denom else None
    )
    counters["retained_fraction_in_window"] = (
        float(counters["storetime_at_or_before_landmark_rows_retained"] / denom) if denom else None
    )
    return data, counters


def changed_count(a: pd.Series, b: pd.Series) -> int:
    aa = pd.to_numeric(a, errors="coerce")
    bb = pd.to_numeric(b, errors="coerce")
    both_na = aa.isna() & bb.isna()
    one_na = aa.isna() ^ bb.isna()
    unequal = (~both_na & ~one_na) & ~np.isclose(aa.fillna(0), bb.fillna(0), rtol=0, atol=1e-12)
    return int((one_na | unequal).sum())


def main() -> None:
    ap = argparse.ArgumentParser(description="Prepare registered H6 CHARTEVENTS storetime sensitivity structured features without predictive performance.")
    ap.add_argument("--root", required=True)
    ap.add_argument("--local-root", required=True)
    ap.add_argument("--expected-counts", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    require_osf_registration()
    root = base_mod.resolve_root(args.root)
    local_root = Path(args.local_root).expanduser().resolve()
    expected_path = Path(args.expected_counts).expanduser().resolve()
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    pop, unique = base_mod.read_population(local_root, expected)

    update_progress(current=1, total=5, phase="h6_chartevents_storetime", message="Loading unchanged demographics", unit="stage")
    demographics, demographic_report = base_mod.load_demographics(root, unique)

    update_progress(current=2, total=5, phase="h6_chartevents_storetime", message="Scanning CHARTEVENTS with registered storetime availability rule", unit="stage")
    char_data, char_report = scan_chartevents_storetime(root, unique)

    update_progress(current=3, total=5, phase="h6_chartevents_storetime", message="Loading unchanged laboratory and urine features", unit="stage")
    lab_data, lab_report = base_mod.scan_labevents(root, unique)
    urine, urine_report = base_mod.scan_urine(root, unique)

    update_progress(current=4, total=5, phase="h6_chartevents_storetime", message="Aggregating timing-matched structured features", unit="stage")
    feat = base_mod.aggregate_features(unique, demographics, char_data, lab_data, urine)
    feature_cols = [c for c in feat.columns if c != "icustay_id"]
    if len(feature_cols) != 34:
        raise RuntimeError(f"Storetime sensitivity expected 34 structured features, found {len(feature_cols)}")

    outcome_reports = {}
    for outcome in OUTCOMES:
        g = pop[pop["outcome"].eq(outcome)].copy()
        outdir = local_root / outcome
        sensitivity = g[["case_id", "subject_id", "icustay_id", "label", "has_note"]].merge(
            feat, on="icustay_id", how="left", validate="one_to_one"
        )
        if len(sensitivity) != len(g):
            raise RuntimeError(f"{outcome}: storetime sensitivity merge changed row count")
        sensitivity_path = outdir / "h6_chartevents_storetime_structured_features_v2_1_local.csv"
        sensitivity.to_csv(sensitivity_path, index=False)

        primary_path = outdir / "enhanced_structured_features_v2_1_local.csv"
        primary = pd.read_csv(primary_path, low_memory=False)
        primary["case_id"] = primary["case_id"].astype(str)
        sensitivity["case_id"] = sensitivity["case_id"].astype(str)
        primary = primary.set_index("case_id").reindex(sensitivity["case_id"]).reset_index()
        if len(primary) != len(sensitivity):
            raise RuntimeError(f"{outcome}: primary/storetime row alignment mismatch")

        per_feature_changed = {name: changed_count(primary[name], sensitivity[name]) for name in CHAR_FEATURES}
        any_changed = np.zeros(len(sensitivity), dtype=bool)
        for name in CHAR_FEATURES:
            aa = pd.to_numeric(primary[name], errors="coerce")
            bb = pd.to_numeric(sensitivity[name], errors="coerce")
            both_na = aa.isna() & bb.isna()
            one_na = aa.isna() ^ bb.isna()
            unequal = (~both_na & ~one_na) & ~np.isclose(aa.fillna(0), bb.fillna(0), rtol=0, atol=1e-12)
            any_changed |= (one_na | unequal).to_numpy()

        outcome_reports[outcome] = {
            "rows": int(len(sensitivity)),
            "cases": int(pd.to_numeric(sensitivity["label"], errors="raise").sum()),
            "controls": int(len(sensitivity) - pd.to_numeric(sensitivity["label"], errors="raise").sum()),
            "rows_with_any_chartevent_feature_changed_vs_primary": int(any_changed.sum()),
            "fraction_rows_with_any_chartevent_feature_changed_vs_primary": float(any_changed.mean()),
            "per_chartevent_feature_changed_rows": per_feature_changed,
            "primary_structured_sha256": sha256_file(primary_path),
            "storetime_structured_sha256": sha256_file(sensitivity_path),
            "local_storetime_structured_file": str(sensitivity_path),
        }

    update_progress(current=5, total=5, phase="done", message="Completed H6 CHARTEVENTS storetime structured-feature preparation", unit="stage")
    report = {
        "analysis": "Registered v2.1 H6 CHARTEVENTS storetime sensitivity preparation",
        "status": "completed",
        "registration_id": "ahxn9",
        "doi": "10.17605/OSF.IO/AHXN9",
        "predictive_performance_computed": False,
        "semantic_inference_run": False,
        "contains_patient_identifiers": False,
        "contains_row_level_data": False,
        "rule": {
            "charttime_within_original_lookback": True,
            "require_nonmissing_storetime": True,
            "require_storetime_at_or_before_landmark": True,
            "missing_storetime_rows_excluded": True,
        },
        "chartevents_availability": char_report,
        "demographics": demographic_report,
        "labevents_unchanged_primary_rule": lab_report,
        "urine_unchanged_primary_rule": urine_report,
        "outcomes": outcome_reports,
        "expected_count_contract_sha256": sha256_file(expected_path),
        "guardrails": [
            "No outcome labels were used to choose or tune the timing rule.",
            "No predictive model was fit or scored.",
            "Only CHARTEVENTS availability timing changes; cohort labels, laboratory timing, urine timing, treatment/context features, notes, semantics, and split assignments remain frozen.",
            "Rows with missing CHARTEVENTS storetime are excluded from this sensitivity, as prespecified.",
            "Row-level timing and feature files remain local; shared artifact is aggregate only.",
        ],
    }
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
