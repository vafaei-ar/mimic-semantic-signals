from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from common import safe_write_csv


def _read(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    out = Path(args.output)

    pre = _read(out / "pre_event_coverage.csv")
    note = _read(out / "note_timing_summary.csv")
    dis = _read(out / "discharge_followup.csv")
    card = _read(out / "cardiac_linkage.csv")

    candidates = []

    event_n = 0
    cov24 = 0.0
    if not pre.empty and "total_events" in pre:
        p24 = pre[pre.get("window_hours", pd.Series(dtype=float)) == 24]
        if not p24.empty:
            event_n = int(p24["total_events"].max())
            cov24 = float(p24["coverage_pct"].max())
    chart_pct = float(note["charttime_available_pct"].iloc[0]) if (not note.empty and "charttime_available_pct" in note) else 0.0

    semantic_ready = event_n >= 500 and cov24 >= 30 and chart_pct >= 50
    candidates.append({
        "candidate":"A_semantic_vital_signs",
        "primary_feasibility_measure":f"max_event_n={event_n}; best_24h_note_coverage={cov24:.1f}%; timed_notes={chart_pct:.1f}%",
        "ready_for_small_semantic_pilot":semantic_ready,
        "interpretation":"Strong if timed notes reliably precede hard deterioration events.",
    })
    candidates.append({
        "candidate":"B_hidden_clinician_concern",
        "primary_feasibility_measure":f"max_event_n={event_n}; best_24h_note_coverage={cov24:.1f}%; timed_notes={chart_pct:.1f}%",
        "ready_for_small_semantic_pilot":semantic_ready,
        "interpretation":"Uses the same temporal substrate as A, then residualizes narrative concern against structured physiology.",
    })

    linked_summaries = 0
    return30 = 0
    if not dis.empty and "discharge_summaries_linked_to_admissions" in dis:
        linked_summaries = int(dis["discharge_summaries_linked_to_admissions"].iloc[0])
        return30 = int(dis.get("hospital_readmission_30d_n", pd.Series([0])).iloc[0])
    candidates.append({
        "candidate":"C_unresolved_care_at_discharge",
        "primary_feasibility_measure":f"linked_discharge_summaries={linked_summaries}; 30d_readmissions={return30}",
        "ready_for_small_semantic_pilot":linked_summaries >= 5000 and return30 >= 500,
        "interpretation":"Feasible if enough summaries have observable post-discharge outcomes; novelty must come from the semantic construct, not readmission prediction.",
    })

    cardiac_overlap = 0
    if not card.empty and "dataset" in card:
        target = card[card["dataset"] == "ECG__AND__ECHO__AND__CORE"]
        if not target.empty:
            cardiac_overlap = int(target["unique_subjects"].iloc[0])
    candidates.append({
        "candidate":"D_cardiac_narrative_measurement_discordance",
        "primary_feasibility_measure":f"ECG+echo+core_subject_overlap={cardiac_overlap}",
        "ready_for_small_semantic_pilot":cardiac_overlap >= 2000,
        "interpretation":"Potentially strong if ECG/echo objective measurements and narrative interpretations overlap at useful scale.",
    })

    df = pd.DataFrame(candidates)
    safe_write_csv(df, out / "candidate_feasibility.csv")

    lines = [
        "# MIMIC semantic-signals feasibility report",
        "",
        "This report is a data-feasibility screen, not a scientific ranking and not a model-performance result.",
        "",
    ]
    for row in candidates:
        lines += [
            f"## {row['candidate']}",
            f"- Measure: {row['primary_feasibility_measure']}",
            f"- Ready for small semantic pilot: {row['ready_for_small_semantic_pilot']}",
            f"- Interpretation: {row['interpretation']}",
            "",
        ]
    (out / "feasibility_report.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
