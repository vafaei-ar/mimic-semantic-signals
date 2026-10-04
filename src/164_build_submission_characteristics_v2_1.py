from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


OUTCOMES = {
    "invasive_ventilation": "Invasive ventilation",
    "renal_replacement_therapy": "Renal replacement therapy",
    "icu_death": "ICU death",
}
FEATURES = ("age_at_icu_years", "map_last", "lactate_last", "creatinine_last")


def summarize_numeric(s: pd.Series) -> dict:
    x = pd.to_numeric(s, errors="coerce").dropna().astype(float)
    if x.empty:
        return {"n_nonmissing": 0, "median": None, "q25": None, "q75": None}
    return {
        "n_nonmissing": int(len(x)),
        "median": float(x.median()),
        "q25": float(x.quantile(0.25)),
        "q75": float(x.quantile(0.75)),
    }


def summarize_note_availability(d: pd.DataFrame) -> dict:
    has_note = pd.to_numeric(d["has_note"], errors="raise").astype(int)
    y = pd.to_numeric(d["label"], errors="raise").astype(int)
    out = {}
    for name, mask in {
        "overall": np.ones(len(d), dtype=bool),
        "cases": y.eq(1).to_numpy(),
        "controls": y.eq(0).to_numpy(),
    }.items():
        h = has_note.to_numpy()[mask]
        out[name] = {
            "n": int(len(h)),
            "note_available_n": int(h.sum()),
            "note_available_pct": float(100.0 * h.mean()) if len(h) else None,
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Aggregate Paper 1 cohort characteristics for Table 1.")
    ap.add_argument("--base", default="data/real_mimic_local/population_landmark12_v2_1")
    ap.add_argument("--output", default="outputs/manuscript/paper1_table1_characteristics_v2_1.json")
    args = ap.parse_args()

    base = Path(args.base).resolve()
    report = {
        "analysis": "Paper 1 frozen confirmatory cohort characteristics",
        "status": "completed",
        "source": "MetaVision",
        "descriptive_only": True,
        "model_fitting_performed": False,
        "outcomes": {},
        "guardrails": [
            "Only aggregate descriptive summaries are shared.",
            "The three confirmatory cohorts are restricted to MetaVision.",
            "ICU length of stay is descriptive only and is not a predictor.",
            "Continuous summaries use available values without imputation.",
        ],
    }

    for outcome, label in OUTCOMES.items():
        outdir = base / outcome
        index = pd.read_csv(outdir / "population_index_local.csv", low_memory=False)
        features = pd.read_csv(outdir / "enhanced_structured_features_v2_1_local.csv", low_memory=False)

        index["case_id"] = index["case_id"].astype(str)
        features["case_id"] = features["case_id"].astype(str)

        index["dbsource"] = index["dbsource"].fillna("unknown").astype(str).str.strip().str.lower()
        index = index[index["dbsource"].eq("metavision")].copy()
        if index.empty:
            raise RuntimeError(f"{outcome}: no MetaVision rows")

        keep = index[[
            "case_id", "label", "has_note", "landmark_time", "outtime"
        ]].merge(
            features[["case_id", "sex", *FEATURES]],
            on="case_id",
            how="left",
            validate="one_to_one",
        )
        if len(keep) != len(index):
            raise RuntimeError(f"{outcome}: row count changed after feature merge")

        y = pd.to_numeric(keep["label"], errors="raise").astype(int)
        if y.sum() <= 0 or y.sum() >= len(y):
            raise RuntimeError(f"{outcome}: degenerate outcome")

        landmark = pd.to_datetime(keep["landmark_time"], errors="raise")
        outtime = pd.to_datetime(keep["outtime"], errors="raise")
        icu_intime = landmark - pd.to_timedelta(12, unit="h")
        los_days = (outtime - icu_intime).dt.total_seconds() / 86400.0
        if (los_days <= 0).any():
            raise RuntimeError(f"{outcome}: non-positive ICU LOS")

        sex = keep["sex"].fillna("UNKNOWN").astype(str).str.strip().str.upper()
        male_n = int(sex.eq("M").sum())
        female_n = int(sex.eq("F").sum())
        unknown_n = int((~sex.isin(["M", "F"])).sum())

        numeric = {
            "age_years": summarize_numeric(keep["age_at_icu_years"]),
            "map_mmhg": summarize_numeric(keep["map_last"]),
            "lactate_mmol_l": summarize_numeric(keep["lactate_last"]),
            "creatinine_mg_dl": summarize_numeric(keep["creatinine_last"]),
            "icu_length_of_stay_days": summarize_numeric(los_days),
        }

        report["outcomes"][outcome] = {
            "label": label,
            "n": int(len(keep)),
            "cases": int(y.sum()),
            "controls": int(len(y) - y.sum()),
            "case_pct": float(100.0 * y.mean()),
            "sex": {
                "male_n": male_n,
                "male_pct": float(100.0 * male_n / len(keep)),
                "female_n": female_n,
                "female_pct": float(100.0 * female_n / len(keep)),
                "unknown_n": unknown_n,
            },
            **numeric,
            "note_availability": summarize_note_availability(keep),
        }

    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
