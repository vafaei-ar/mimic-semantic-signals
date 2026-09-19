from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def extract_probability(response: dict, name: str) -> float | None:
    container = response.get("answers")
    if not isinstance(container, dict):
        container = response.get("judgments")
    if not isinstance(container, dict):
        return None

    obj = container.get(name)
    if not isinstance(obj, dict):
        return None

    for key in ("noul", "probability", "probability_yes", "yes_probability"):
        value = obj.get(key)
        if isinstance(value, (int, float)):
            return float(value)

    probs = obj.get("probabilities")
    if isinstance(probs, dict):
        for key in ("yes", "true", "1", True):
            if key in probs and isinstance(probs[key], (int, float)):
                return float(probs[key])

    value = obj.get("value")
    confidence = obj.get("confidence")
    if isinstance(value, bool) and isinstance(confidence, (int, float)):
        return float(confidence if value else 1 - confidence)

    return None


def auroc(y: np.ndarray, p: np.ndarray) -> float:
    y = np.asarray(y, dtype=int)
    p = np.asarray(p, dtype=float)
    n1 = int((y == 1).sum())
    n0 = int((y == 0).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")

    ranks = pd.Series(p).rank(method="average").to_numpy()
    rank_sum_positive = float(ranks[y == 1].sum())
    return (
        rank_sum_positive - n1 * (n1 + 1) / 2
    ) / (n1 * n0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    ap.add_argument("--output-prefix", required=True)
    args = ap.parse_args()

    path = Path(args.results).expanduser().resolve()
    prefix = Path(args.output_prefix).expanduser().resolve()
    prefix.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("status") != "ok":
                continue
            response = rec.get("response", {})
            gold = rec.get("gold", {}).get("constructs", {})
            state = rec.get("state", {})
            for construct, label in gold.items():
                if label is None:
                    continue
                prob = extract_probability(response, construct)
                if prob is None:
                    continue
                rows.append(
                    {
                        "case_id": rec.get("case_id"),
                        "construct": construct,
                        "gold": int(label),
                        "probability": float(prob),
                        "event_type": rec.get("gold", {}).get("event_type"),
                        "discordant": rec.get("gold", {}).get("discordant"),
                        "hours_before_event": state.get("hours_before_event"),
                        "note_category": state.get("note_category"),
                    }
                )

    long = pd.DataFrame(rows)
    long.to_csv(prefix.with_suffix(".predictions.csv"), index=False)

    metrics = []
    if not long.empty:
        for construct, g in long.groupby("construct"):
            y = g["gold"].to_numpy(dtype=int)
            p = g["probability"].to_numpy(dtype=float)
            metrics.append(
                {
                    "construct": construct,
                    "n": len(g),
                    "prevalence": float(np.mean(y)),
                    "mean_probability": float(np.mean(p)),
                    "mean_probability_positive": float(np.mean(p[y == 1]))
                    if np.any(y == 1)
                    else np.nan,
                    "mean_probability_negative": float(np.mean(p[y == 0]))
                    if np.any(y == 0)
                    else np.nan,
                    "brier": float(np.mean((p - y) ** 2)),
                    "auroc": auroc(y, p),
                }
            )

    metrics_df = pd.DataFrame(metrics)
    metrics_df.to_csv(prefix.with_suffix(".metrics.csv"), index=False)

    summary = {
        "parsed_predictions": int(len(long)),
        "constructs_evaluated": int(long["construct"].nunique())
        if not long.empty
        else 0,
        "metrics_file": str(prefix.with_suffix(".metrics.csv")),
        "predictions_file": str(prefix.with_suffix(".predictions.csv")),
    }
    prefix.with_suffix(".summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
