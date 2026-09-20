from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def extract_probability(response: dict, name: str) -> float | None:
    answers = response.get("answers")
    if not isinstance(answers, dict):
        return None
    obj = answers.get(name)
    if not isinstance(obj, dict):
        return None
    value = obj.get("noul")
    return float(value) if isinstance(value, (int, float)) else None


def auc(y: np.ndarray, p: np.ndarray) -> float:
    y = np.asarray(y, dtype=int)
    p = np.asarray(p, dtype=float)
    if len(np.unique(y)) < 2:
        return float("nan")
    ranks = pd.Series(p).rank(method="average").to_numpy()
    n1 = int((y == 1).sum())
    n0 = int((y == 0).sum())
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def brier(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.mean((np.asarray(p, dtype=float) - np.asarray(y, dtype=float)) ** 2))


def time_bin(hours: float | None) -> str:
    if hours is None or pd.isna(hours):
        return "unknown"
    if hours <= 6:
        return "0_6h"
    if hours <= 12:
        return "6_12h"
    return "12_24h"


def metric_row(g: pd.DataFrame) -> dict:
    y = g["gold"].to_numpy(dtype=int)
    p = g["probability"].to_numpy(dtype=float)
    return {
        "n": len(g),
        "prevalence": float(y.mean()) if len(y) else np.nan,
        "mean_probability": float(p.mean()) if len(p) else np.nan,
        "mean_probability_positive": float(p[y == 1].mean()) if np.any(y == 1) else np.nan,
        "mean_probability_negative": float(p[y == 0].mean()) if np.any(y == 0) else np.nan,
        "auroc": auc(y, p),
        "brier": brier(y, p),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    path = Path(args.results).expanduser().resolve()
    out = Path(args.output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    records = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("status") != "ok":
                continue
            metadata = rec.get("metadata", {})
            gold = rec.get("gold", {})
            answers = rec.get("response", {})
            for construct, label in gold.get("constructs", {}).items():
                if label is None:
                    continue
                prob = extract_probability(answers, construct)
                if prob is None:
                    continue
                hours = metadata.get("hours_before_event")
                records.append(
                    {
                        "case_id": rec.get("case_id"),
                        "construct": construct,
                        "gold": int(label),
                        "probability": float(prob),
                        "event_type": gold.get("event_type"),
                        "anchor_type": gold.get("anchor_type"),
                        "discordant": gold.get("discordant"),
                        "note_category": metadata.get("note_category"),
                        "hours_before_event": hours,
                        "time_bin": time_bin(hours),
                    }
                )

    df = pd.DataFrame(records)
    df.to_csv(out / "predictions_long.csv", index=False)

    overall = []
    for construct, g in df.groupby("construct"):
        row = {"construct": construct, **metric_row(g)}
        overall.append(row)
    pd.DataFrame(overall).to_csv(out / "metrics_overall.csv", index=False)

    for field, filename in [
        ("event_type", "metrics_by_event.csv"),
        ("discordant", "metrics_by_discordance.csv"),
        ("time_bin", "metrics_by_time.csv"),
        ("note_category", "metrics_by_note_category.csv"),
    ]:
        rows = []
        if field in df.columns:
            for (construct, value), g in df.groupby(["construct", field], dropna=False):
                rows.append(
                    {
                        "construct": construct,
                        field: value,
                        **metric_row(g),
                    }
                )
        pd.DataFrame(rows).to_csv(out / filename, index=False)

    wide = df.pivot(index="case_id", columns="construct", values="probability")
    wide.corr(method="spearman").to_csv(out / "probability_spearman.csv")

    summary = {
        "cases": int(df["case_id"].nunique()) if not df.empty else 0,
        "predictions": int(len(df)),
        "constructs": int(df["construct"].nunique()) if not df.empty else 0,
        "state_metadata_available": bool(
            not df.empty
            and df["note_category"].notna().any()
            and df["hours_before_event"].notna().any()
        ),
    }
    (out / "analysis_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
