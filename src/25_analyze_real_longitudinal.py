from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


TIME_ORDER = ["12_24h", "6_12h", "0_6h"]


def aggregate_values(construct: str, values: list[float]) -> dict[str, float]:
    if not values:
        return {"extreme": np.nan, "mean": np.nan, "top2": np.nan}
    vals = np.asarray(values, dtype=float)
    if construct == "reassuring_stability":
        extreme = float(np.min(vals))
        chosen = np.sort(vals)[: min(2, len(vals))]
    else:
        extreme = float(np.max(vals))
        chosen = np.sort(vals)[-min(2, len(vals)):]
    return {
        "extreme": extreme,
        "mean": float(np.mean(vals)),
        "top2": float(np.mean(chosen)),
    }



def spearman_without_scipy(a: pd.Series, b: pd.Series) -> float:
    """Spearman rho via rank transformation + Pearson correlation; no SciPy required."""
    x = pd.to_numeric(a, errors="coerce")
    y = pd.to_numeric(b, errors="coerce")
    valid = x.notna() & y.notna()
    x = x[valid]
    y = y[valid]
    if len(x) < 3:
        return float("nan")
    xr = x.rank(method="average")
    yr = y.rank(method="average")
    if xr.nunique() < 2 or yr.nunique() < 2:
        return float("nan")
    return float(xr.corr(yr, method="pearson"))


def bootstrap_mean_ci(values: np.ndarray, seed: int, n_boot: int = 2000) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) < 2:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    means = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        sample = rng.choice(values, size=len(values), replace=True)
        means[i] = sample.mean()
    return float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Analyze same-admission real-MIMIC semantic trajectories without note text."
    )
    ap.add_argument("--results", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--seed", type=int, default=20260920)
    args = ap.parse_args()

    src = Path(args.results).expanduser().resolve()
    out = Path(args.output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    rows = []
    with src.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("status") != "ok":
                continue
            meta = rec.get("metadata", {})
            admission_group = meta.get("admission_group")
            if not admission_group:
                raise RuntimeError(
                    "Results are missing metadata.admission_group. "
                    "Use cases from src/24_build_real_longitudinal_pilot.py."
                )
            answers = rec.get("response", {}).get("answers", {})
            for construct, answer in answers.items():
                if not isinstance(answer, dict):
                    continue
                values = answer.get("chunk_values")
                if not isinstance(values, list):
                    continue
                agg = aggregate_values(construct, values)
                for method, probability in agg.items():
                    rows.append(
                        {
                            "case_id": rec.get("case_id"),
                            "admission_group": admission_group,
                            "event_type": meta.get("event_type"),
                            "time_bin": meta.get("time_bin"),
                            "note_category": meta.get("note_category"),
                            "dbsource": meta.get("dbsource"),
                            "note_tokens": meta.get("note_tokens"),
                            "chunks_evaluated": meta.get("chunks_evaluated"),
                            "construct": construct,
                            "aggregation": method,
                            "probability": probability,
                        }
                    )

    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("No chunk-level probabilities could be parsed.")

    # Safe long-format derivative: no note text and no source patient identifiers.
    df.to_csv(out / "probabilities_by_aggregation.csv", index=False)

    paired_rows = []
    for (event_type, construct, aggregation), g in df.groupby(
        ["event_type", "construct", "aggregation"]
    ):
        wide = g.pivot_table(
            index="admission_group",
            columns="time_bin",
            values="probability",
            aggfunc="first",
        )
        if not set(TIME_ORDER).issubset(wide.columns):
            continue
        wide = wide.dropna(subset=TIME_ORDER)
        if wide.empty:
            continue

        early = wide["12_24h"].to_numpy(dtype=float)
        middle = wide["6_12h"].to_numpy(dtype=float)
        late = wide["0_6h"].to_numpy(dtype=float)
        delta = late - early
        ci_lo, ci_hi = bootstrap_mean_ci(
            delta,
            seed=args.seed + sum(ord(c) for c in str(event_type) + str(construct) + str(aggregation)),
        )

        paired_rows.append(
            {
                "event_type": event_type,
                "construct": construct,
                "aggregation": aggregation,
                "n_complete_admissions": len(wide),
                "mean_12_24h": float(np.mean(early)),
                "mean_6_12h": float(np.mean(middle)),
                "mean_0_6h": float(np.mean(late)),
                "median_12_24h": float(np.median(early)),
                "median_6_12h": float(np.median(middle)),
                "median_0_6h": float(np.median(late)),
                "mean_delta_0_6_vs_12_24": float(np.mean(delta)),
                "mean_delta_ci95_low": ci_lo,
                "mean_delta_ci95_high": ci_hi,
                "median_delta_0_6_vs_12_24": float(np.median(delta)),
                "pct_increased_0_6_vs_12_24": float(100.0 * np.mean(delta > 0)),
                "pct_monotonic_toward_event": float(
                    100.0 * np.mean((early <= middle) & (middle <= late))
                ),
            }
        )

    paired = pd.DataFrame(paired_rows)
    paired.to_csv(out / "paired_trajectory_summary.csv", index=False)

    length_rows = []
    for (construct, aggregation), g in df.groupby(["construct", "aggregation"]):
        sub = g[["probability", "note_tokens", "chunks_evaluated"]].dropna()
        if len(sub) < 3:
            continue
        length_rows.append(
            {
                "construct": construct,
                "aggregation": aggregation,
                "n": len(sub),
                "spearman_probability_note_tokens": spearman_without_scipy(
                    sub["probability"], sub["note_tokens"]
                ),
                "spearman_probability_chunks": spearman_without_scipy(
                    sub["probability"], sub["chunks_evaluated"]
                ),
            }
        )
    pd.DataFrame(length_rows).to_csv(out / "length_sensitivity.csv", index=False)

    category_rows = []
    for (event_type, construct, aggregation, category), g in df.groupby(
        ["event_type", "construct", "aggregation", "note_category"]
    ):
        category_rows.append(
            {
                "event_type": event_type,
                "construct": construct,
                "aggregation": aggregation,
                "note_category": category,
                "n": len(g),
                "mean_probability": float(g["probability"].mean()),
                "median_probability": float(g["probability"].median()),
            }
        )
    pd.DataFrame(category_rows).to_csv(out / "note_category_summary.csv", index=False)

    summary = {
        "cases": int(df["case_id"].nunique()),
        "admission_groups": int(df["admission_group"].nunique()),
        "constructs": int(df["construct"].nunique()),
        "aggregation_methods": sorted(df["aggregation"].unique().tolist()),
        "contains_note_text": False,
        "contains_source_patient_identifiers": False,
        "paired_analysis": True,
        "primary_interpretation": (
            "Use paired_trajectory_summary.csv. A credible temporal signal should be directionally "
            "similar under extreme, mean, and top2 pooling and should not be strongly explained by "
            "note length or number of chunks."
        ),
    }
    (out / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
