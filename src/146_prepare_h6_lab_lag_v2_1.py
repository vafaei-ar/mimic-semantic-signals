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
LAGS = (1, 2)
LAB_FEATURES = (
    "lactate_last", "creatinine_last", "bun_last", "wbc_last",
    "hemoglobin_last", "platelets_last", "sodium_last", "potassium_last",
    "bicarbonate_last", "chloride_last", "glucose_last",
    "bilirubin_total_last", "inr_last", "ph_last",
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


def scan_labevents_lags(root: Path, unique: pd.DataFrame) -> tuple[dict[int, pd.DataFrame], dict]:
    f = find_file(module_path(root, "mimiciii"), ["LABEVENTS.csv.gz", "LABEVENTS.csv"])
    if f is None:
        raise FileNotFoundError("LABEVENTS not found")

    lab_map = base_mod.build_item_map(base_mod.LAB_IDS)
    hadms = set(unique["hadm_id"].tolist())
    lookup = unique[["icustay_id", "hadm_id", "landmark_time"]]
    rows_by_lag = {lag: [] for lag in LAGS}
    counters = {
        "candidate_rows": 0,
        "in_original_lookback_valid_rows": 0,
        "out_of_range_rows_excluded": 0,
        "eligible_rows_by_lag": {str(lag): 0 for lag in LAGS},
        "rows_lost_vs_primary_by_lag": {str(lag): 0 for lag in LAGS},
    }

    for chunk in read_columns(
        f,
        ["hadm_id", "itemid", "charttime", "valuenum"],
        chunksize=600_000,
    ):
        c = lower_columns(chunk)
        c["hadm_id"] = pd.to_numeric(c["hadm_id"], errors="coerce")
        c = c[c["hadm_id"].isin(hadms)].copy()
        if c.empty:
            continue
        c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
        c = c[c["itemid"].isin(lab_map)].copy()
        if c.empty:
            continue
        counters["candidate_rows"] += int(len(c))

        c["charttime"] = parse_datetime(c["charttime"])
        c["valuenum"] = pd.to_numeric(c["valuenum"], errors="coerce")
        c = c.dropna(subset=["hadm_id", "itemid", "charttime", "valuenum"]).copy()
        if c.empty:
            continue
        c["hadm_id"] = c["hadm_id"].astype("int64")
        c["itemid"] = c["itemid"].astype(int)
        c = c.merge(lookup, on="hadm_id", how="inner")
        c = c[
            (c["charttime"] <= c["landmark_time"])
            & (
                c["charttime"]
                >= c["landmark_time"] - pd.to_timedelta(base_mod.LAB_LOOKBACK_H, unit="h")
            )
        ].copy()
        if c.empty:
            continue

        c["feature"] = c["itemid"].map(lab_map)
        valid_parts = []
        for feature_name, g in c.groupby("feature", sort=False):
            good = base_mod.valid_lab(feature_name, g["valuenum"])
            counters["out_of_range_rows_excluded"] += int((~good).sum())
            valid_parts.append(g[good].copy())
        if not valid_parts:
            continue
        q = pd.concat(valid_parts, ignore_index=True)
        if q.empty:
            continue

        counters["in_original_lookback_valid_rows"] += int(len(q))
        for lag in LAGS:
            eligible = q[
                q["charttime"] + pd.to_timedelta(lag, unit="h") <= q["landmark_time"]
            ].copy()
            counters["eligible_rows_by_lag"][str(lag)] += int(len(eligible))
            if not eligible.empty:
                rows_by_lag[lag].append(
                    eligible[["icustay_id", "feature", "charttime", "valuenum"]]
                    .rename(columns={"valuenum": "clean_value"})
                )

    data_by_lag = {}
    primary_n = int(counters["in_original_lookback_valid_rows"])
    for lag in LAGS:
        data = (
            pd.concat(rows_by_lag[lag], ignore_index=True)
            if rows_by_lag[lag]
            else pd.DataFrame(columns=["icustay_id", "feature", "charttime", "clean_value"])
        )
        if not data.empty:
            data = (
                data.groupby(["icustay_id", "feature", "charttime"], as_index=False)["clean_value"]
                .mean()
            )
        data_by_lag[lag] = data
        eligible_n = int(counters["eligible_rows_by_lag"][str(lag)])
        lost = primary_n - eligible_n
        counters["rows_lost_vs_primary_by_lag"][str(lag)] = int(lost)
        counters.setdefault("retained_fraction_by_lag", {})[str(lag)] = (
            float(eligible_n / primary_n) if primary_n else None
        )
        counters.setdefault("lost_fraction_by_lag", {})[str(lag)] = (
            float(lost / primary_n) if primary_n else None
        )
    return data_by_lag, counters


def changed_mask(a: pd.Series, b: pd.Series) -> np.ndarray:
    aa = pd.to_numeric(a, errors="coerce")
    bb = pd.to_numeric(b, errors="coerce")
    both_na = aa.isna() & bb.isna()
    one_na = aa.isna() ^ bb.isna()
    unequal = (~both_na & ~one_na) & ~np.isclose(
        aa.fillna(0), bb.fillna(0), rtol=0, atol=1e-12
    )
    return (one_na | unequal).to_numpy()


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Prepare registered H6 1-hour and 2-hour laboratory-lag structured features without predictive performance."
    )
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

    update_progress(current=1, total=5, phase="h6_lab_lag", message="Loading unchanged demographics and CHARTEVENTS", unit="stage")
    demographics, demographic_report = base_mod.load_demographics(root, unique)
    char_data, char_report = base_mod.scan_chartevents(root, unique)

    update_progress(current=2, total=5, phase="h6_lab_lag", message="Scanning LABEVENTS under frozen 1-hour and 2-hour availability lags", unit="stage")
    lab_by_lag, lab_report = scan_labevents_lags(root, unique)

    update_progress(current=3, total=5, phase="h6_lab_lag", message="Loading unchanged urine features", unit="stage")
    urine, urine_report = base_mod.scan_urine(root, unique)

    update_progress(current=4, total=5, phase="h6_lab_lag", message="Aggregating lag-matched structured feature blocks", unit="stage")
    outcome_reports = {}
    for outcome in OUTCOMES:
        g = pop[pop["outcome"].eq(outcome)].copy()
        outdir = local_root / outcome
        primary_path = outdir / "enhanced_structured_features_v2_1_local.csv"
        primary = pd.read_csv(primary_path, low_memory=False)
        primary["case_id"] = primary["case_id"].astype(str)

        outcome_reports[outcome] = {
            "rows": int(len(g)),
            "cases": int(pd.to_numeric(g["label"], errors="raise").sum()),
            "controls": int(len(g) - pd.to_numeric(g["label"], errors="raise").sum()),
            "primary_structured_sha256": sha256_file(primary_path),
            "lags": {},
        }

        for lag in LAGS:
            feat = base_mod.aggregate_features(
                unique, demographics, char_data, lab_by_lag[lag], urine
            )
            feature_cols = [c for c in feat.columns if c != "icustay_id"]
            if len(feature_cols) != 34:
                raise RuntimeError(
                    f"{outcome}: {lag}h lag expected 34 structured features, found {len(feature_cols)}"
                )
            sensitivity = g[
                ["case_id", "subject_id", "icustay_id", "label", "has_note"]
            ].merge(feat, on="icustay_id", how="left", validate="one_to_one")
            if len(sensitivity) != len(g):
                raise RuntimeError(f"{outcome}: {lag}h lab-lag merge changed row count")
            sensitivity["case_id"] = sensitivity["case_id"].astype(str)
            path = outdir / f"h6_lab_lag_{lag}h_structured_features_v2_1_local.csv"
            sensitivity.to_csv(path, index=False)

            aligned_primary = (
                primary.set_index("case_id")
                .reindex(sensitivity["case_id"])
                .reset_index()
            )
            if len(aligned_primary) != len(sensitivity):
                raise RuntimeError(f"{outcome}: {lag}h primary/lag row alignment mismatch")

            any_changed = np.zeros(len(sensitivity), dtype=bool)
            per_feature_changed = {}
            for name in LAB_FEATURES:
                mask = changed_mask(aligned_primary[name], sensitivity[name])
                any_changed |= mask
                per_feature_changed[name] = int(mask.sum())

            outcome_reports[outcome]["lags"][str(lag)] = {
                "rows_with_any_lab_feature_changed_vs_primary": int(any_changed.sum()),
                "fraction_rows_with_any_lab_feature_changed_vs_primary": float(any_changed.mean()),
                "per_lab_feature_changed_rows": per_feature_changed,
                "structured_sha256": sha256_file(path),
                "local_structured_file": str(path),
            }

    update_progress(current=5, total=5, phase="done", message="Completed H6 laboratory-lag structured-feature preparation", unit="stage")
    report = {
        "analysis": "Registered v2.1 H6 laboratory-result lag sensitivity preparation",
        "status": "completed",
        "registration_id": "ahxn9",
        "doi": "10.17605/OSF.IO/AHXN9",
        "lags_hours": [1, 2],
        "predictive_performance_computed": False,
        "semantic_inference_run": False,
        "contains_patient_identifiers": False,
        "contains_row_level_data": False,
        "rule": {
            "effective_availability": "charttime + fixed lag",
            "eligible_if_effective_availability_at_or_before_landmark": True,
            "original_lab_lookback_hours": float(base_mod.LAB_LOOKBACK_H),
            "item_mappings_unchanged": True,
            "other_structured_feature_timing_unchanged": True,
        },
        "labevents_availability": lab_report,
        "demographics_unchanged_primary_rule": demographic_report,
        "chartevents_unchanged_primary_rule": char_report,
        "urine_unchanged_primary_rule": urine_report,
        "outcomes": outcome_reports,
        "expected_count_contract_sha256": sha256_file(expected_path),
        "guardrails": [
            "No outcome labels were used to choose or tune the 1-hour or 2-hour lag values.",
            "No predictive model was fit or scored.",
            "Only LABEVENTS effective availability changes; cohorts, CHARTEVENTS, urine, treatment/context features, notes, semantics, and split assignments remain frozen.",
            "All registered lab item mappings and the original 24-hour charttime lookback remain unchanged.",
            "Row-level timing and feature files remain local; shared artifact is aggregate only.",
        ],
    }
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
