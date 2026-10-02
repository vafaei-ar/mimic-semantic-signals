from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from runrelay_progress import update_progress


PRIMARY = "invasive_ventilation"
EXPLICIT = "invasive_ventilation_explicit_evidence_sensitivity"
BROAD = "invasive_ventilation_any_support_sensitivity"


def as_bool(s: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(s):
        return s.fillna(False).astype(bool)
    numeric = pd.to_numeric(s, errors="coerce")
    if numeric.notna().all():
        return numeric.ne(0)
    return s.fillna("").astype(str).str.strip().str.lower().isin({"true", "1", "yes"})


def load_index(base: Path, name: str) -> pd.DataFrame:
    path = base / name / "population_index_local.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    d = pd.read_csv(path, low_memory=False)
    required = {"subject_id", "hadm_id", "icustay_id", "label", "has_note", "note_time", "category"}
    missing = required - set(d.columns)
    if missing:
        raise RuntimeError(f"{name}: missing required columns {sorted(missing)}")
    forbidden = {"text", "note_text", "clinical_note"}
    present_forbidden = forbidden & set(d.columns)
    if present_forbidden:
        raise RuntimeError(f"{name}: population index unexpectedly contains note text columns {sorted(present_forbidden)}")
    for col in ["subject_id", "hadm_id", "icustay_id", "label"]:
        d[col] = pd.to_numeric(d[col], errors="raise").astype("int64")
    d["has_note"] = as_bool(d["has_note"])
    if d["icustay_id"].duplicated().any():
        raise RuntimeError(f"{name}: duplicate ICU stay rows")
    if not set(d["label"].unique()).issubset({0, 1}):
        raise RuntimeError(f"{name}: non-binary labels")
    return d


def summary(d: pd.DataFrame) -> dict:
    cases = d[d["label"].eq(1)]
    controls = d[d["label"].eq(0)]
    return {
        "rows": int(len(d)),
        "unique_patients": int(d["subject_id"].nunique()),
        "cases": int(len(cases)),
        "controls": int(len(controls)),
        "note_available_rows": int(d["has_note"].sum()),
        "case_note_rows": int(cases["has_note"].sum()),
        "control_note_rows": int(controls["has_note"].sum()),
        "prevalence": float(d["label"].mean()) if len(d) else None,
    }


def identity_frame(d: pd.DataFrame) -> pd.DataFrame:
    cols = ["subject_id", "hadm_id", "icustay_id", "label", "has_note", "note_time", "category"]
    q = d[cols].copy()
    q["note_time"] = q["note_time"].fillna("").astype(str)
    q["category"] = q["category"].fillna("").astype(str)
    return q.sort_values("icustay_id").reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Audit registered H6 ventilation endpoint-sensitivity cohort inputs.")
    ap.add_argument("--base", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    base = Path(args.base).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    update_progress(current=1, total=3, phase="load", message="Loading frozen primary and endpoint-sensitivity ventilation indices", unit="stage")
    primary = load_index(base, PRIMARY)
    explicit = load_index(base, EXPLICIT)
    broad = load_index(base, BROAD)

    update_progress(current=2, total=3, phase="verify", message="Verifying registered endpoint-sensitivity cohort relationships", unit="stage")

    primary_identity = identity_frame(primary)
    explicit_identity = identity_frame(explicit)
    explicit_identical = primary_identity.equals(explicit_identity)
    if not explicit_identical:
        raise RuntimeError("Registered explicit-intubation sensitivity is not empirically identical to the primary cohort")

    primary_controls = set(primary.loc[primary["label"].eq(0), "icustay_id"].astype(int))
    broad_controls = set(broad.loc[broad["label"].eq(0), "icustay_id"].astype(int))
    if primary_controls != broad_controls:
        raise RuntimeError("Broad respiratory-support sensitivity changed the primary ventilation control set")

    primary_cases = set(primary.loc[primary["label"].eq(1), "icustay_id"].astype(int))
    broad_cases = set(broad.loc[broad["label"].eq(1), "icustay_id"].astype(int))
    if not primary_cases.issubset(broad_cases):
        raise RuntimeError("A primary ventilation case is missing from the broad respiratory-support case set")

    primary_rows = set(primary["icustay_id"].astype(int))
    broad_rows = set(broad["icustay_id"].astype(int))
    if not primary_rows.issubset(broad_rows):
        raise RuntimeError("Broad respiratory-support cohort unexpectedly drops a primary cohort row")

    added_rows = broad_rows - primary_rows
    added = broad[broad["icustay_id"].isin(added_rows)].copy()
    if len(added) and not added["label"].eq(1).all():
        raise RuntimeError("Broad respiratory-support cohort added non-case rows")

    report = {
        "analysis": "Registered v2.1 H6 ventilation endpoint-sensitivity input audit",
        "status": "completed",
        "registration_id": "ahxn9",
        "doi": "10.17605/OSF.IO/AHXN9",
        "predictive_performance_computed": False,
        "contains_note_text": False,
        "contains_patient_identifiers": False,
        "contains_row_level_data": False,
        "primary": summary(primary),
        "explicit_intubation_evidence": summary(explicit),
        "broad_respiratory_support": summary(broad),
        "relationship_checks": {
            "explicit_empirically_identical_to_primary": True,
            "broad_control_set_identical_to_primary": True,
            "primary_cases_subset_of_broad_cases": True,
            "primary_rows_subset_of_broad_rows": True,
            "broad_added_rows_all_cases": True,
            "broad_added_case_rows": int(len(added_rows)),
            "broad_total_case_increase": int(len(broad_cases) - len(primary_cases)),
        },
        "interpretation": [
            "The explicit-intubation sensitivity requires no separate predictive rerun when its rows, labels, note identities, and controls are identical to the primary cohort.",
            "The broad respiratory-support cohort is the meaningful registered ventilation endpoint sensitivity and requires its own downstream feature/context/text pipeline because it adds case rows.",
        ],
        "guardrails": [
            "No model was fit or scored.",
            "No note text or patient-level rows are shared.",
            "The audit does not alter the registered endpoint definitions.",
        ],
    }

    update_progress(current=3, total=3, phase="done", message="Completed H6 ventilation endpoint-sensitivity input audit", unit="stage")
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
