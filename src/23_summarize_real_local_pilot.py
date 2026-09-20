from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def time_order(value: str) -> int:
    return {"12_24h": 0, "6_12h": 1, "0_6h": 2}.get(str(value), 99)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    src = Path(args.results).expanduser().resolve()
    out = Path(args.output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    rows = []
    case_meta = []
    with src.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("status") != "ok":
                continue
            meta = rec.get("metadata", {})
            case_meta.append(
                {
                    "case_id": rec.get("case_id"),
                    "event_type": meta.get("event_type"),
                    "time_bin": meta.get("time_bin"),
                    "note_category": meta.get("note_category"),
                    "dbsource": meta.get("dbsource"),
                    "hours_before_event": meta.get("hours_before_event"),
                    "note_tokens": meta.get("note_tokens"),
                    "chunks_evaluated": meta.get("chunks_evaluated"),
                }
            )
            answers = rec.get("response", {}).get("answers", {})
            for construct, answer in answers.items():
                p = answer.get("noul") if isinstance(answer, dict) else None
                if isinstance(p, (int, float)):
                    rows.append(
                        {
                            "case_id": rec.get("case_id"),
                            "construct": construct,
                            "probability": float(p),
                            "event_type": meta.get("event_type"),
                            "time_bin": meta.get("time_bin"),
                            "note_category": meta.get("note_category"),
                            "dbsource": meta.get("dbsource"),
                            "hours_before_event": meta.get("hours_before_event"),
                            "note_tokens": meta.get("note_tokens"),
                            "chunks_evaluated": meta.get("chunks_evaluated"),
                        }
                    )

    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("No parsed real-note probabilities found.")

    # No note text or patient identifiers are present in any exported summary.
    overall = (
        df.groupby(["construct", "event_type", "time_bin"])
        .agg(
            n=("probability", "size"),
            mean_probability=("probability", "mean"),
            median_probability=("probability", "median"),
            p25_probability=("probability", lambda x: x.quantile(0.25)),
            p75_probability=("probability", lambda x: x.quantile(0.75)),
            pct_ge_050=("probability", lambda x: 100.0 * (x >= 0.50).mean()),
            pct_ge_075=("probability", lambda x: 100.0 * (x >= 0.75).mean()),
        )
        .reset_index()
    )
    overall["time_order"] = overall["time_bin"].map(time_order)
    overall = overall.sort_values(
        ["construct", "event_type", "time_order"]
    ).drop(columns=["time_order"])
    overall.to_csv(out / "semantic_probability_by_event_time.csv", index=False)

    by_category = (
        df.groupby(["construct", "event_type", "time_bin", "note_category"])
        .agg(
            n=("probability", "size"),
            mean_probability=("probability", "mean"),
            median_probability=("probability", "median"),
        )
        .reset_index()
    )
    by_category.to_csv(
        out / "semantic_probability_by_note_category.csv",
        index=False,
    )

    by_dbsource = (
        df.groupby(["construct", "event_type", "time_bin", "dbsource"])
        .agg(
            n=("probability", "size"),
            mean_probability=("probability", "mean"),
            median_probability=("probability", "median"),
        )
        .reset_index()
    )
    by_dbsource.to_csv(
        out / "semantic_probability_by_dbsource.csv",
        index=False,
    )

    wide = df.pivot(index="case_id", columns="construct", values="probability")
    wide.corr(method="spearman").to_csv(out / "semantic_probability_spearman.csv")

    meta_df = pd.DataFrame(case_meta).drop_duplicates("case_id")
    note_length_summary = {
        "median_note_tokens": float(meta_df["note_tokens"].median()),
        "p25_note_tokens": float(meta_df["note_tokens"].quantile(0.25)),
        "p75_note_tokens": float(meta_df["note_tokens"].quantile(0.75)),
        "median_chunks_evaluated": float(meta_df["chunks_evaluated"].median()),
        "max_chunks_evaluated": int(meta_df["chunks_evaluated"].max()),
    }

    summary = {
        "cases": int(df["case_id"].nunique()),
        "predictions": int(len(df)),
        "constructs": int(df["construct"].nunique()),
        "event_types": sorted(df["event_type"].dropna().astype(str).unique().tolist()),
        "time_bins": sorted(
            df["time_bin"].dropna().astype(str).unique().tolist(),
            key=time_order,
        ),
        "contains_note_text": False,
        "contains_patient_identifiers": False,
        "exploratory_only": True,
        "note_length": note_length_summary,
        "warning": (
            "Event-only pilot. Do not interpret probabilities as predictive performance. "
            "Controls and structured physiology are required for the main analysis."
        ),
    }
    (out / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
