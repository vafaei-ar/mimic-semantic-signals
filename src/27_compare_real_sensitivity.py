from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


KEYS = ["event_type", "construct", "aggregation"]


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Compare paired semantic trajectories between an original real-MIMIC "
            "analysis and a sensitivity analysis such as explicit-event-term filtering."
        )
    )
    ap.add_argument("--original", required=True)
    ap.add_argument("--sensitivity", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    original_path = Path(args.original).expanduser().resolve()
    sensitivity_path = Path(args.sensitivity).expanduser().resolve()
    out = Path(args.output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    original = pd.read_csv(original_path)
    sensitivity = pd.read_csv(sensitivity_path)

    required = set(KEYS + [
        "n_complete_admissions",
        "mean_12_24h",
        "mean_6_12h",
        "mean_0_6h",
        "mean_delta_0_6_vs_12_24",
        "mean_delta_ci95_low",
        "mean_delta_ci95_high",
        "pct_increased_0_6_vs_12_24",
        "pct_monotonic_toward_event",
    ])
    for name, df in [("original", original), ("sensitivity", sensitivity)]:
        missing = sorted(required - set(df.columns))
        if missing:
            raise RuntimeError(f"{name} table is missing required columns: {missing}")

    keep = KEYS + sorted(required - set(KEYS))
    merged = original[keep].merge(
        sensitivity[keep],
        on=KEYS,
        how="inner",
        suffixes=("_original", "_sensitivity"),
    )

    merged["n_retained_pct"] = (
        100.0
        * merged["n_complete_admissions_sensitivity"]
        / merged["n_complete_admissions_original"]
    )
    merged["delta_change_after_filter"] = (
        merged["mean_delta_0_6_vs_12_24_sensitivity"]
        - merged["mean_delta_0_6_vs_12_24_original"]
    )
    merged["same_delta_direction"] = (
        merged["mean_delta_0_6_vs_12_24_original"]
        * merged["mean_delta_0_6_vs_12_24_sensitivity"]
        > 0
    )
    merged["sensitivity_ci_excludes_zero"] = (
        (merged["mean_delta_ci95_low_sensitivity"] > 0)
        | (merged["mean_delta_ci95_high_sensitivity"] < 0)
    )

    merged.to_csv(out / "trajectory_sensitivity_comparison.csv", index=False)

    # Compact clinically aligned rows for rapid review.
    aligned = merged[
        (
            (merged["event_type"] == "vasopressor_initiation")
            & merged["construct"].isin(
                [
                    "overall_clinician_concern",
                    "worsening_trajectory",
                    "hemodynamic_concern",
                    "poor_treatment_response",
                    "escalation_considered",
                ]
            )
        )
        | (
            (merged["event_type"] == "intubation_mv_procedure")
            & merged["construct"].isin(
                [
                    "overall_clinician_concern",
                    "worsening_trajectory",
                    "respiratory_concern",
                    "poor_treatment_response",
                    "escalation_considered",
                ]
            )
        )
        | (
            (merged["event_type"] == "in_hospital_death")
            & merged["construct"].isin(
                [
                    "overall_clinician_concern",
                    "worsening_trajectory",
                    "reassuring_stability",
                ]
            )
        )
    ].copy()
    aligned.to_csv(out / "clinically_aligned_comparison.csv", index=False)

    summary_rows = []
    for event_type, g in merged.groupby("event_type"):
        summary_rows.append(
            {
                "event_type": event_type,
                "rows_compared": int(len(g)),
                "median_n_retained_pct": float(g["n_retained_pct"].median()),
                "pct_same_delta_direction": float(100.0 * g["same_delta_direction"].mean()),
                "rows_sensitivity_ci_excludes_zero": int(
                    g["sensitivity_ci_excludes_zero"].sum()
                ),
            }
        )

    summary = {
        "original": str(original_path),
        "sensitivity": str(sensitivity_path),
        "rows_compared": int(len(merged)),
        "events": summary_rows,
        "contains_note_text": False,
        "contains_source_patient_identifiers": False,
        "interpretation": (
            "A robust signal should retain the same direction after filtering, remain "
            "similar across mean/top2/extreme pooling, and preferably retain a 95% CI "
            "that excludes zero despite the smaller sensitivity cohort."
        ),
    }
    (out / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
