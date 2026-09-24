from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from common import find_file, lower_columns, module_path, parse_datetime, read_columns, resolve_root
from runrelay_progress import update_progress


LANDMARK_H = 12.0
VITAL_LOOKBACK_H = 6.0
LAB_LOOKBACK_H = 24.0
URINE_LOOKBACK_H = 6.0

VITAL_IDS = {
    "heart_rate": {211, 220045},
    "sbp": {51, 442, 455, 6701, 220179, 220050},
    "dbp": {8368, 8440, 8441, 8555, 220180, 220051},
    "map": {456, 52, 6702, 443, 220052, 220181, 225312},
    "resp_rate": {615, 618, 220210, 224690},
    "spo2": {646, 220277},
}
TEMP_C_IDS = {676, 223762}
TEMP_F_IDS = {678, 223761}
GCS_IDS = {
    "gcs_eye": {184, 220739},
    "gcs_verbal": {723, 223900},
    "gcs_motor": {454, 223901},
}
GCS_VERBAL_AIRWAY_VALUES = {"1.0 et/trach", "no response-ett"}

LAB_IDS = {
    "lactate": {50813},
    "creatinine": {50912},
    "bun": {51006},
    "wbc": {51300, 51301},
    "hemoglobin": {51222},
    "platelets": {51265},
    "sodium": {50983},
    "potassium": {50971},
    "bicarbonate": {50882},
    "chloride": {50902},
    "glucose": {50931},
    "bilirubin_total": {50885},
    "inr": {51237},
    "ph": {50820},
}

URINE_OUTPUT_IDS = {
    40055, 43175, 40069, 40094, 40715, 40473, 40085,
    40057, 40056, 40405, 40428, 40086, 40096, 40651,
    226559, 226560, 226561, 226584, 226563, 226564,
    226565, 226567, 226557, 226558, 227489,
}
GU_IRRIGANT_INPUT_ID = 227488

OUTCOMES = ("invasive_ventilation", "renal_replacement_therapy", "icu_death")


def read_population(local_root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    frames = []
    for outcome in OUTCOMES:
        path = local_root / outcome / "population_index_local.csv"
        d = pd.read_csv(path, low_memory=False)
        required = {
            "case_id", "subject_id", "hadm_id", "icustay_id", "label",
            "landmark_time", "has_note", "age_at_icu_years_uncapped", "first_careunit",
        }
        missing = required - set(d.columns)
        if missing:
            raise RuntimeError(f"{path}: missing columns {sorted(missing)}")
        d["outcome"] = outcome
        for c in ["subject_id", "hadm_id", "icustay_id"]:
            d[c] = pd.to_numeric(d[c], errors="raise").astype("int64")
        d["landmark_time"] = pd.to_datetime(d["landmark_time"], errors="raise")
        if (pd.to_numeric(d["age_at_icu_years_uncapped"], errors="coerce") < 18).any():
            raise RuntimeError(f"{outcome}: age < 18 present in v2.1 adult cohort")
        if d["first_careunit"].astype(str).str.strip().str.upper().eq("NICU").any():
            raise RuntimeError(f"{outcome}: NICU stay present in v2.1 adult cohort")
        frames.append(d)

    pop = pd.concat(frames, ignore_index=True)
    key = ["subject_id", "hadm_id", "icustay_id", "landmark_time"]
    unique = pop[key].drop_duplicates().copy()

    # If an ICU stay is shared across outcomes, its landmark identity must be identical.
    inconsistent = (
        unique.groupby("icustay_id")
        .agg(
            n_subject=("subject_id", "nunique"),
            n_hadm=("hadm_id", "nunique"),
            n_landmark=("landmark_time", "nunique"),
        )
    )
    if ((inconsistent > 1).any(axis=1)).any():
        raise RuntimeError("Inconsistent shared ICU-stay identity across corrected outcomes")

    unique = unique.drop_duplicates("icustay_id").copy()
    return pop, unique


def numeric_zero_mask(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").fillna(0).eq(0)


def build_item_map(groups: dict[str, set[int]]) -> dict[int, str]:
    out = {}
    for name, ids in groups.items():
        for itemid in ids:
            if itemid in out:
                raise RuntimeError(f"Duplicate item mapping for {itemid}")
            out[int(itemid)] = name
    return out


def valid_vital(feature: str, values: pd.Series) -> pd.Series:
    if feature == "heart_rate":
        return values.gt(0) & values.lt(300)
    if feature == "sbp":
        return values.gt(0) & values.lt(400)
    if feature in {"dbp", "map"}:
        return values.gt(0) & values.lt(300)
    if feature == "resp_rate":
        return values.gt(0) & values.lt(70)
    if feature == "spo2":
        return values.gt(0) & values.le(100)
    raise KeyError(feature)


def valid_lab(feature: str, values: pd.Series) -> pd.Series:
    upper = {
        "lactate": 50,
        "creatinine": 150,
        "bun": 300,
        "wbc": 1000,
        "hemoglobin": 50,
        "platelets": 10000,
        "sodium": 200,
        "potassium": 30,
        "bicarbonate": 10000,
        "chloride": 10000,
        "glucose": 10000,
        "bilirubin_total": 150,
        "inr": 50,
    }
    if feature == "ph":
        return values.gt(6.0) & values.lt(8.5)
    return values.gt(0) & values.lt(upper[feature])


def load_demographics(root: Path, unique: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    f = find_file(module_path(root, "mimiciii"), ["PATIENTS.csv.gz", "PATIENTS.csv"])
    if f is None:
        raise FileNotFoundError("PATIENTS not found")

    d = lower_columns(
        pd.read_csv(
            f,
            usecols=lambda c: c.lower() in {"subject_id", "gender", "dob"},
            low_memory=False,
        )
    )
    d["subject_id"] = pd.to_numeric(d["subject_id"], errors="coerce")
    d["dob"] = parse_datetime(d["dob"])
    d["gender"] = d["gender"].fillna("UNKNOWN").astype(str).str.strip().str.upper()
    d = d.dropna(subset=["subject_id", "dob"]).copy()
    d["subject_id"] = d["subject_id"].astype("int64")

    q = unique.merge(d[["subject_id", "dob", "gender"]], on="subject_id", how="left")
    q["icu_intime"] = q["landmark_time"] - pd.to_timedelta(LANDMARK_H, unit="h")
    # Use Python date arithmetic rather than pandas nanosecond timedeltas:
    # MIMIC-III deidentification can shift DOBs for the oldest patients far enough
    # back that a ~300-year subtraction overflows int64 nanoseconds.
    age_values = []
    for intime, dob in zip(q["icu_intime"], q["dob"]):
        if pd.isna(intime) or pd.isna(dob):
            age_values.append(np.nan)
        else:
            delta_days = (intime.to_pydatetime().date() - dob.to_pydatetime().date()).days
            age_values.append(delta_days / 365.2425)
    age = pd.Series(age_values, index=q.index, dtype=float)
    q["age_at_icu_years"] = age.clip(lower=0, upper=90)
    q["sex"] = q["gender"].where(q["gender"].isin(["M", "F"]), "UNKNOWN")

    report = {
        "age_nonmissing_fraction": float(q["age_at_icu_years"].notna().mean()),
        "sex_counts": {str(k): int(v) for k, v in q["sex"].value_counts(dropna=False).to_dict().items()},
        "age_capped_at_90_n": int((age > 90).sum()),
    }
    return q[["icustay_id", "age_at_icu_years", "sex"]], report


def scan_chartevents(root: Path, unique: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    f = find_file(module_path(root, "mimiciii"), ["CHARTEVENTS.csv.gz", "CHARTEVENTS.csv"])
    if f is None:
        raise FileNotFoundError("CHARTEVENTS not found")

    vital_map = build_item_map(VITAL_IDS)
    gcs_map = build_item_map(GCS_IDS)
    all_ids = set(vital_map) | TEMP_C_IDS | TEMP_F_IDS | set(gcs_map)
    stays = set(unique["icustay_id"].tolist())
    lookup = unique[["icustay_id", "landmark_time"]]

    rows = []
    counters = {
        "candidate_rows": 0,
        "error_rows_excluded": 0,
        "out_of_range_rows_excluded": 0,
        "gcs_verbal_airway_rows_excluded": 0,
    }

    for chunk in read_columns(
        f,
        ["icustay_id", "itemid", "charttime", "valuenum", "value", "error"],
        chunksize=600_000,
    ):
        c = lower_columns(chunk)
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
            ok = numeric_zero_mask(c["error"])
            counters["error_rows_excluded"] += int((~ok).sum())
            c = c[ok].copy()

        c["charttime"] = parse_datetime(c["charttime"])
        c["valuenum"] = pd.to_numeric(c["valuenum"], errors="coerce")
        c = c.dropna(subset=["icustay_id", "itemid", "charttime", "valuenum"]).copy()
        if c.empty:
            continue
        c["icustay_id"] = c["icustay_id"].astype("int64")
        c["itemid"] = c["itemid"].astype(int)
        c = c.merge(lookup, on="icustay_id", how="inner")
        c = c[
            (c["charttime"] <= c["landmark_time"])
            & (
                c["charttime"]
                >= c["landmark_time"] - pd.to_timedelta(VITAL_LOOKBACK_H, unit="h")
            )
        ].copy()
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
                good = bool(valid_vital(name, pd.Series([v])).iloc[0])
                feature.append(name)
                value.append(v)
                valid.append(good)
            elif itemid in TEMP_C_IDS:
                feature.append("temperature_c")
                value.append(v)
                valid.append(bool(10 < v < 50))
            elif itemid in TEMP_F_IDS:
                feature.append("temperature_c")
                value.append((v - 32.0) / 1.8)
                valid.append(bool(70 < v < 120))
            elif itemid in gcs_map:
                name = gcs_map[itemid]
                bounds = {"gcs_eye": (1, 4), "gcs_verbal": (1, 5), "gcs_motor": (1, 6)}
                lo, hi = bounds[name]
                raw_value = str(getattr(row, "value", "") or "").strip().lower()
                airway_coded = name == "gcs_verbal" and raw_value in GCS_VERBAL_AIRWAY_VALUES
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
    return data, counters


def scan_labevents(root: Path, unique: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    f = find_file(module_path(root, "mimiciii"), ["LABEVENTS.csv.gz", "LABEVENTS.csv"])
    if f is None:
        raise FileNotFoundError("LABEVENTS not found")

    lab_map = build_item_map(LAB_IDS)
    hadms = set(unique["hadm_id"].tolist())
    lookup = unique[["icustay_id", "hadm_id", "landmark_time"]]
    rows = []
    counters = {"candidate_rows": 0, "out_of_range_rows_excluded": 0}

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
                >= c["landmark_time"] - pd.to_timedelta(LAB_LOOKBACK_H, unit="h")
            )
        ].copy()
        if c.empty:
            continue
        c["feature"] = c["itemid"].map(lab_map)
        valid_parts = []
        for feature_name, g in c.groupby("feature", sort=False):
            good = valid_lab(feature_name, g["valuenum"])
            counters["out_of_range_rows_excluded"] += int((~good).sum())
            valid_parts.append(g[good].copy())
        if valid_parts:
            q = pd.concat(valid_parts, ignore_index=True)
            if not q.empty:
                rows.append(q[["icustay_id", "feature", "charttime", "valuenum"]].rename(columns={"valuenum": "clean_value"}))

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
    return data, counters


def scan_urine(root: Path, unique: pd.DataFrame) -> tuple[pd.Series, dict]:
    f = find_file(module_path(root, "mimiciii"), ["OUTPUTEVENTS.csv.gz", "OUTPUTEVENTS.csv"])
    if f is None:
        raise FileNotFoundError("OUTPUTEVENTS not found")

    all_ids = set(URINE_OUTPUT_IDS) | {GU_IRRIGANT_INPUT_ID}
    stays = set(unique["icustay_id"].tolist())
    lookup = unique[["icustay_id", "landmark_time"]]
    rows = []
    counters = {
        "candidate_rows": 0,
        "error_rows_excluded": 0,
        "value_ge_5000_excluded": 0,
    }

    for chunk in read_columns(
        f,
        ["icustay_id", "itemid", "charttime", "value", "iserror"],
        chunksize=600_000,
    ):
        c = lower_columns(chunk)
        c["icustay_id"] = pd.to_numeric(c["icustay_id"], errors="coerce")
        c = c[c["icustay_id"].isin(stays)].copy()
        if c.empty:
            continue
        c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
        c = c[c["itemid"].isin(all_ids)].copy()
        if c.empty:
            continue
        counters["candidate_rows"] += int(len(c))

        if "iserror" in c.columns:
            ok = numeric_zero_mask(c["iserror"])
            counters["error_rows_excluded"] += int((~ok).sum())
            c = c[ok].copy()

        c["charttime"] = parse_datetime(c["charttime"])
        c["value_num"] = pd.to_numeric(c["value"], errors="coerce")
        c = c.dropna(subset=["icustay_id", "itemid", "charttime", "value_num"]).copy()
        if c.empty:
            continue
        c["icustay_id"] = c["icustay_id"].astype("int64")
        c["itemid"] = c["itemid"].astype(int)
        c = c.merge(lookup, on="icustay_id", how="inner")
        c = c[
            (c["charttime"] <= c["landmark_time"])
            & (
                c["charttime"]
                >= c["landmark_time"] - pd.to_timedelta(URINE_LOOKBACK_H, unit="h")
            )
        ].copy()
        if c.empty:
            continue
        good = c["value_num"] < 5000
        counters["value_ge_5000_excluded"] += int((~good).sum())
        c = c[good].copy()
        if c.empty:
            continue
        c["net_ml"] = c["value_num"]
        irrig = c["itemid"].eq(GU_IRRIGANT_INPUT_ID)
        c.loc[irrig, "net_ml"] = -c.loc[irrig, "value_num"]
        rows.append(c[["icustay_id", "net_ml"]])

    if not rows:
        return pd.Series(dtype=float), counters
    data = pd.concat(rows, ignore_index=True)
    return data.groupby("icustay_id")["net_ml"].sum(), counters


def aggregate_features(
    unique: pd.DataFrame,
    demographics: pd.DataFrame,
    char_data: pd.DataFrame,
    lab_data: pd.DataFrame,
    urine: pd.Series,
) -> pd.DataFrame:
    feat = unique[["icustay_id"]].copy()
    feat = feat.merge(demographics, on="icustay_id", how="left")

    dynamic_vitals = ["heart_rate", "sbp", "dbp", "map", "resp_rate", "spo2", "temperature_c"]
    for name in dynamic_vitals:
        x = char_data[char_data["feature"].eq(name)].sort_values(["icustay_id", "charttime"])
        if x.empty:
            last = pd.Series(dtype=float)
            delta = pd.Series(dtype=float)
        else:
            g = x.groupby("icustay_id")["clean_value"]
            last = g.last()
            first = g.first()
            n_times = x.groupby("icustay_id")["charttime"].nunique()
            delta = (last - first).where(n_times >= 2, np.nan)
        feat = feat.merge(last.rename(f"{name}_last"), left_on="icustay_id", right_index=True, how="left")
        feat = feat.merge(delta.rename(f"{name}_delta"), left_on="icustay_id", right_index=True, how="left")

    for name in ["gcs_eye", "gcs_verbal", "gcs_motor"]:
        x = char_data[char_data["feature"].eq(name)].sort_values(["icustay_id", "charttime"])
        last = x.groupby("icustay_id")["clean_value"].last() if not x.empty else pd.Series(dtype=float)
        feat = feat.merge(last.rename(f"{name}_last"), left_on="icustay_id", right_index=True, how="left")

    for name in LAB_IDS:
        x = lab_data[lab_data["feature"].eq(name)].sort_values(["icustay_id", "charttime"])
        last = x.groupby("icustay_id")["clean_value"].last() if not x.empty else pd.Series(dtype=float)
        feat = feat.merge(last.rename(f"{name}_last"), left_on="icustay_id", right_index=True, how="left")

    feat = feat.merge(
        urine.rename("urine_output_6h_net_ml"),
        left_on="icustay_id",
        right_index=True,
        how="left",
    )
    return feat


def main() -> None:
    ap = argparse.ArgumentParser(description="Build enhanced structured baseline features for corrected adult v2.1 landmark cohorts.")
    ap.add_argument("--root", required=True)
    ap.add_argument("--local-root", required=True)
    ap.add_argument("--manifest", required=True)
    args = ap.parse_args()

    root = resolve_root(args.root)
    local_root = Path(args.local_root).expanduser().resolve()
    manifest = Path(args.manifest).expanduser().resolve()
    manifest.parent.mkdir(parents=True, exist_ok=True)

    pop, unique = read_population(local_root)

    update_progress(current=1, total=6, phase="demographics", message="Extracting age and sex for corrected v2 ICU stays", unit="stage")
    demographics, demographic_report = load_demographics(root, unique)

    update_progress(current=2, total=6, phase="bedside", message="Scanning frozen six-hour bedside physiology and GCS mappings", unit="stage")
    char_data, char_report = scan_chartevents(root, unique)

    update_progress(current=3, total=6, phase="labs", message="Scanning frozen 24-hour blood laboratory mappings", unit="stage")
    lab_data, lab_report = scan_labevents(root, unique)

    update_progress(current=4, total=6, phase="urine", message="Scanning frozen six-hour urine-output mappings", unit="stage")
    urine, urine_report = scan_urine(root, unique)

    update_progress(current=5, total=6, phase="aggregate", message="Aggregating enhanced structured features and local outcome files", unit="stage")
    feat = aggregate_features(unique, demographics, char_data, lab_data, urine)

    feature_cols = [c for c in feat.columns if c != "icustay_id"]
    expected_features = [
        "age_at_icu_years", "sex",
        "heart_rate_last", "heart_rate_delta",
        "sbp_last", "sbp_delta",
        "dbp_last", "dbp_delta",
        "map_last", "map_delta",
        "resp_rate_last", "resp_rate_delta",
        "spo2_last", "spo2_delta",
        "temperature_c_last", "temperature_c_delta",
        "gcs_eye_last", "gcs_verbal_last", "gcs_motor_last",
        "lactate_last", "creatinine_last", "bun_last", "wbc_last",
        "hemoglobin_last", "platelets_last", "sodium_last", "potassium_last",
        "bicarbonate_last", "chloride_last", "glucose_last",
        "bilirubin_total_last", "inr_last", "ph_last",
        "urine_output_6h_net_ml",
    ]
    if feature_cols != expected_features:
        raise RuntimeError(f"Feature order mismatch: {feature_cols}")

    outcome_reports = {}
    for outcome in OUTCOMES:
        g = pop[pop["outcome"].eq(outcome)].copy()
        outdir = local_root / outcome
        keep = g[["case_id", "subject_id", "icustay_id", "label", "has_note"]].merge(
            feat, on="icustay_id", how="left"
        )
        if len(keep) != len(g):
            raise RuntimeError(f"{outcome}: feature merge changed row count")
        keep.to_csv(outdir / "enhanced_structured_features_v2_1_local.csv", index=False)

        numeric_cols = [c for c in feature_cols if c != "sex"]
        clinical_numeric_cols = [c for c in numeric_cols if c != "age_at_icu_years"]
        nonmissing = {c: float(keep[c].notna().mean()) for c in feature_cols}
        outcome_reports[outcome] = {
            "rows": int(len(keep)),
            "feature_count": int(len(feature_cols)),
            "numeric_feature_missing_fraction": float(keep[numeric_cols].isna().mean().mean()),
            "clinical_numeric_feature_missing_fraction": float(
                keep[clinical_numeric_cols].isna().mean().mean()
            ),
            "rows_with_all_clinical_numeric_features_missing": int(
                keep[clinical_numeric_cols].isna().all(axis=1).sum()
            ),
            "per_feature_nonmissing_fraction": nonmissing,
            "local_feature_file": str(outdir / "enhanced_structured_features_v2_1_local.csv"),
        }

    update_progress(current=6, total=6, phase="done", message="Completed enhanced structured v2.1 feature extraction", unit="stage")

    report = {
        "analysis": "Enhanced structured baseline feature extraction v2.1",
        "mapping_freeze": "docs/enhanced_structured_baseline_mapping_freeze_v2.md",
        "mapping_addendum": "docs/enhanced_structured_baseline_mapping_addendum_v2_1.md",
        "local_only": True,
        "contains_patient_identifiers": False,
        "contains_row_level_data": False,
        "predictive_model_fitted": False,
        "semantic_or_text_inference_performed": False,
        "landmark_hours": LANDMARK_H,
        "vital_lookback_hours": VITAL_LOOKBACK_H,
        "lab_lookback_hours": LAB_LOOKBACK_H,
        "urine_lookback_hours": URINE_LOOKBACK_H,
        "feature_names": feature_cols,
        "unique_icu_stays_processed": int(len(feat)),
        "demographics": demographic_report,
        "chartevents_diagnostics": char_report,
        "labevents_diagnostics": lab_report,
        "urine_output_diagnostics": urine_report,
        "outcomes": outcome_reports,
        "guardrails": [
            "No predictive model was fit or scored.",
            "No dbsource feature is present.",
            "No outcome-conditioned feature selection was performed.",
            "All row-level features remain local and are not declared as artifacts.",
        ],
    }
    manifest.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
