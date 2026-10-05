from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from registration_gate import require_osf_registration
from runrelay_progress import update_progress

BASE = Path("data/real_mimic_local/population_landmark12_v2_1")
ATTESTATION = Path("docs/registration/exploratory_extension_osf_upload_attestation_2026-10-05.md")
ALERT_RATES = (0.02, 0.05, 0.10, 0.20)
BOOTSTRAP_REPLICATES = 2000
BOOTSTRAP_SEED = 20261005

OUTCOME_SPECS = {
    "ventilation": {
        "outcome_dir": "invasive_ventilation",
        "report": Path("outputs/multitask_benchmark/h1_openjev_v2_1_ventilation.json"),
        "pred": "h1_openjev_predictions_v2_1_local.csv",
        "detectable_delta_auroc": 0.0233,
    },
    "rrt": {
        "outcome_dir": "renal_replacement_therapy",
        "report": Path("outputs/multitask_benchmark/h2_openjev_v2_1_rrt.json"),
        "pred": "h2_openjev_predictions_v2_1_local.csv",
        "detectable_delta_auroc": 0.0113,
    },
    "death_metavision": {
        "outcome_dir": "icu_death",
        "report": Path("outputs/multitask_benchmark/h3_openjev_v2_1_death.json"),
        "pred": "h3_openjev_predictions_v2_1_local.csv",
        "detectable_delta_auroc": 0.0241,
    },
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def percentile_ci(values: list[float | None]) -> dict:
    arr = np.asarray([float(v) for v in values if v is not None and np.isfinite(float(v))], dtype=float)
    if arr.size == 0:
        return {"valid_replicates": 0, "ci95_percentile": None}
    lo, hi = np.quantile(arr, [0.025, 0.975])
    return {
        "valid_replicates": int(arr.size),
        "ci95_percentile": [float(lo), float(hi)],
    }


def case_rank(case_ids: np.ndarray) -> np.ndarray:
    # Deterministic rank equivalent to ascending string case_id tie-breaking.
    order = np.argsort(case_ids.astype(str), kind="mergesort")
    rank = np.empty(len(order), dtype=np.int64)
    rank[order] = np.arange(len(order), dtype=np.int64)
    return rank


def rank_order(risk: np.ndarray, rank: np.ndarray) -> np.ndarray:
    # Primary key: risk descending. Secondary: frozen case_id ascending.
    # Final occurrence key only resolves duplicated patient-cluster bootstrap copies.
    occurrence = np.arange(len(risk), dtype=np.int64)
    return np.lexsort((occurrence, rank, -risk))


def alert_metrics(
    y: np.ndarray,
    pb: np.ndarray,
    pa: np.ndarray,
    rank: np.ndarray,
) -> dict[str, dict]:
    n = int(len(y))
    events_total = int(y.sum())
    if events_total <= 0:
        raise RuntimeError("Alert metrics require at least one positive event")

    ob = rank_order(pb, rank)
    oa = rank_order(pa, rank)
    out: dict[str, dict] = {}

    for rate in ALERT_RATES:
        k = int(math.ceil(rate * n))
        k = max(1, min(k, n))
        base_mask = np.zeros(n, dtype=bool)
        aug_mask = np.zeros(n, dtype=bool)
        base_mask[ob[:k]] = True
        aug_mask[oa[:k]] = True

        base_events = int(y[base_mask].sum())
        aug_events = int(y[aug_mask].sum())
        moved_in = aug_mask & ~base_mask
        moved_out = base_mask & ~aug_mask
        moved_in_events = int(y[moved_in].sum())
        moved_out_events = int(y[moved_out].sum())

        def model_block(caught: int) -> dict:
            return {
                "alerts": k,
                "alert_rate_actual": float(k / n),
                "events_caught": caught,
                "sensitivity": float(caught / events_total),
                "ppv": float(caught / k),
                "events_caught_per_1000_stays": float(caught / n * 1000.0),
                "alerts_per_true_event": None if caught == 0 else float(k / caught),
            }

        out[f"{rate:.2f}"] = {
            "n": n,
            "events_total": events_total,
            "alert_budget_requested": float(rate),
            "comparator": model_block(base_events),
            "augmented": model_block(aug_events),
            "paired_reclassification": {
                "alerts_moved_in": int(moved_in.sum()),
                "alerts_moved_out": int(moved_out.sum()),
                "alerts_moved_in_per_1000_stays": float(moved_in.sum() / n * 1000.0),
                "alerts_moved_out_per_1000_stays": float(moved_out.sum() / n * 1000.0),
                "events_moved_in": moved_in_events,
                "events_moved_out": moved_out_events,
                "events_moved_in_per_1000_stays": float(moved_in_events / n * 1000.0),
                "events_moved_out_per_1000_stays": float(moved_out_events / n * 1000.0),
                "net_events_caught": int(aug_events - base_events),
                "net_events_caught_per_1000_stays": float((aug_events - base_events) / n * 1000.0),
                "delta_sensitivity": float((aug_events - base_events) / events_total),
                "delta_ppv": float((aug_events - base_events) / k),
                "delta_alerts_per_true_event": (
                    None
                    if base_events == 0 or aug_events == 0
                    else float(k / aug_events - k / base_events)
                ),
            },
        }
    return out


def patient_rows(subject_id: np.ndarray) -> tuple[np.ndarray, list[np.ndarray]]:
    unique = np.unique(subject_id)
    rows = [np.flatnonzero(subject_id == sid) for sid in unique]
    return unique, rows


def bootstrap_alerts(
    y: np.ndarray,
    pb: np.ndarray,
    pa: np.ndarray,
    subject_id: np.ndarray,
    case_id: np.ndarray,
    *,
    progress_offset: int,
    progress_total: int,
    outcome_name: str,
) -> dict:
    unique, rows_by_patient = patient_rows(subject_id)
    sid_to_pos = {sid: i for i, sid in enumerate(unique)}
    rng = np.random.default_rng(BOOTSTRAP_SEED)

    keys = [f"{r:.2f}" for r in ALERT_RATES]
    store: dict[str, dict[str, list]] = {}
    for key in keys:
        store[key] = {
            "comparator_sensitivity": [],
            "augmented_sensitivity": [],
            "delta_sensitivity": [],
            "comparator_ppv": [],
            "augmented_ppv": [],
            "delta_ppv": [],
            "comparator_events_caught_per_1000_stays": [],
            "augmented_events_caught_per_1000_stays": [],
            "net_events_caught_per_1000_stays": [],
            "alerts_moved_in_per_1000_stays": [],
            "alerts_moved_out_per_1000_stays": [],
            "events_moved_in_per_1000_stays": [],
            "events_moved_out_per_1000_stays": [],
            "comparator_alerts_per_true_event": [],
            "augmented_alerts_per_true_event": [],
            "delta_alerts_per_true_event": [],
        }

    valid = 0
    attempts = 0
    max_attempts = BOOTSTRAP_REPLICATES * 2
    while valid < BOOTSTRAP_REPLICATES:
        attempts += 1
        if attempts > max_attempts:
            raise RuntimeError("Exceeded bootstrap attempt limit")
        sampled = rng.choice(unique, size=len(unique), replace=True)
        idx = np.concatenate([rows_by_patient[sid_to_pos[sid]] for sid in sampled])
        yy = y[idx]
        if yy.sum() == 0:
            continue
        bb = pb[idx]
        aa = pa[idx]
        cc = case_id[idx].astype(str)
        rr = case_rank(cc)
        res = alert_metrics(yy, bb, aa, rr)

        for key in keys:
            block = res[key]
            pair = block["paired_reclassification"]
            base = block["comparator"]
            aug = block["augmented"]
            store[key]["comparator_sensitivity"].append(base["sensitivity"])
            store[key]["augmented_sensitivity"].append(aug["sensitivity"])
            store[key]["delta_sensitivity"].append(pair["delta_sensitivity"])
            store[key]["comparator_ppv"].append(base["ppv"])
            store[key]["augmented_ppv"].append(aug["ppv"])
            store[key]["delta_ppv"].append(pair["delta_ppv"])
            store[key]["comparator_events_caught_per_1000_stays"].append(base["events_caught_per_1000_stays"])
            store[key]["augmented_events_caught_per_1000_stays"].append(aug["events_caught_per_1000_stays"])
            store[key]["net_events_caught_per_1000_stays"].append(pair["net_events_caught_per_1000_stays"])
            store[key]["alerts_moved_in_per_1000_stays"].append(pair["alerts_moved_in_per_1000_stays"])
            store[key]["alerts_moved_out_per_1000_stays"].append(pair["alerts_moved_out_per_1000_stays"])
            store[key]["events_moved_in_per_1000_stays"].append(pair["events_moved_in_per_1000_stays"])
            store[key]["events_moved_out_per_1000_stays"].append(pair["events_moved_out_per_1000_stays"])
            store[key]["comparator_alerts_per_true_event"].append(base["alerts_per_true_event"])
            store[key]["augmented_alerts_per_true_event"].append(aug["alerts_per_true_event"])
            store[key]["delta_alerts_per_true_event"].append(pair["delta_alerts_per_true_event"])

        valid += 1
        if valid == 1 or valid % 25 == 0 or valid == BOOTSTRAP_REPLICATES:
            update_progress(
                current=progress_offset + valid,
                total=progress_total,
                phase="extension_t0_fixed_alert_bootstrap",
                message=f"{outcome_name}: conditional fixed-prediction bootstrap {valid}/{BOOTSTRAP_REPLICATES}",
                unit="replicate",
            )

    summary = {}
    for key in keys:
        summary[key] = {metric: percentile_ci(vals) for metric, vals in store[key].items()}
    return {
        "valid_replicates": BOOTSTRAP_REPLICATES,
        "attempts": attempts,
        "bootstrap_unit": "source_patient",
        "predictions_refit": False,
        "interpretation": "Conditional on the already-fitted frozen primary-partition models.",
        "seed": BOOTSTRAP_SEED,
        "interval_type": "two-sided 95% percentile",
        "metrics": summary,
    }


def five_repeat_ranges(repeats: list[dict]) -> dict:
    keys = [f"{r:.2f}" for r in ALERT_RATES]
    out = {}
    for key in keys:
        vals = {
            "delta_sensitivity": [],
            "delta_ppv": [],
            "net_events_caught_per_1000_stays": [],
            "alerts_moved_in_per_1000_stays": [],
            "events_moved_in_per_1000_stays": [],
            "events_moved_out_per_1000_stays": [],
        }
        for rep in repeats:
            pair = rep["alert_metrics"][key]["paired_reclassification"]
            for metric in vals:
                vals[metric].append(float(pair[metric]))
        out[key] = {
            metric: {
                "values": values,
                "range": [float(min(values)), float(max(values))],
            }
            for metric, values in vals.items()
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Paper 1 extension Tier 0 fixed-alert, DCA, and compatible-limit analyses.")
    ap.add_argument("--output", default="outputs/multitask_benchmark/extension_t0_v2_1.json")
    args = ap.parse_args()

    require_osf_registration()
    if not ATTESTATION.exists():
        raise RuntimeError("Extension OSF upload attestation is missing; refusing label-reading analysis")

    root = Path(".").resolve()
    out = {
        "analysis": "Paper 1 exploratory extension Tier 0",
        "status": "completed",
        "extension_status": "post-registration exploratory",
        "parent_registration": "ahxn9",
        "extension_osf_project": "wmyb2",
        "protocol": "docs/registration/exploratory_extension_protocol_v2_1_2026-10-04.md",
        "osf_upload_attestation": str(ATTESTATION),
        "t0_1_fixed_alert_burden": {
            "alert_budgets": list(ALERT_RATES),
            "tie_break": "predicted risk descending, then frozen case_id ascending",
            "bootstrap_replicates": BOOTSTRAP_REPLICATES,
            "bootstrap_type": "patient-cluster resampling of frozen primary-partition OOF predictions; conditional on fitted models",
        },
        "outcomes": {},
        "guardrails": [
            "No model fitting is performed by this Tier 0 task.",
            "Only frozen registered OOF predictions and completed registered aggregate reports are read.",
            "No row-level predictions are declared or shared as artifacts.",
            "All output is aggregate.",
        ],
    }

    total_progress = BOOTSTRAP_REPLICATES * len(OUTCOME_SPECS)
    progress_offset = 0

    for outcome_key, spec in OUTCOME_SPECS.items():
        report_path = root / spec["report"]
        pred_path = root / BASE / spec["outcome_dir"] / spec["pred"]
        if not report_path.exists():
            raise RuntimeError(f"Missing registered aggregate report: {report_path}")
        if not pred_path.exists():
            raise RuntimeError(f"Missing frozen OOF predictions: {pred_path}")

        report = json.loads(report_path.read_text(encoding="utf-8"))
        pred = pd.read_csv(pred_path, low_memory=False)
        required = {"case_id", "subject_id", "label"}
        required |= {f"comparator_repeat_{i}" for i in range(1, 6)}
        required |= {f"augmented_openjev_repeat_{i}" for i in range(1, 6)}
        missing = required - set(pred.columns)
        if missing:
            raise RuntimeError(f"{outcome_key}: prediction file missing {sorted(missing)}")
        if pred["case_id"].duplicated().any():
            raise RuntimeError(f"{outcome_key}: duplicate case_id in prediction file")

        y = pd.to_numeric(pred["label"], errors="raise").astype(int).to_numpy()
        groups = pd.to_numeric(pred["subject_id"], errors="raise").to_numpy()
        cases = pred["case_id"].astype(str).to_numpy()
        rank = case_rank(cases)

        expected_n = int(report["n"])
        expected_cases = int(report["cases"])
        if len(y) != expected_n or int(y.sum()) != expected_cases:
            raise RuntimeError(
                f"{outcome_key}: prediction population mismatch "
                f"n={len(y)}/{expected_n}, cases={int(y.sum())}/{expected_cases}"
            )

        repeats = []
        for ri in range(1, 6):
            pb = pd.to_numeric(pred[f"comparator_repeat_{ri}"], errors="raise").to_numpy(dtype=float)
            pa = pd.to_numeric(pred[f"augmented_openjev_repeat_{ri}"], errors="raise").to_numpy(dtype=float)
            if not np.isfinite(pb).all() or not np.isfinite(pa).all():
                raise RuntimeError(f"{outcome_key}: non-finite predictions in repeat {ri}")
            repeats.append({
                "repeat": ri,
                "alert_metrics": alert_metrics(y, pb, pa, rank),
            })

        primary_pb = pd.to_numeric(pred["comparator_repeat_1"], errors="raise").to_numpy(dtype=float)
        primary_pa = pd.to_numeric(pred["augmented_openjev_repeat_1"], errors="raise").to_numpy(dtype=float)
        boot = bootstrap_alerts(
            y,
            primary_pb,
            primary_pa,
            groups,
            cases,
            progress_offset=progress_offset,
            progress_total=total_progress,
            outcome_name=outcome_key,
        )
        progress_offset += BOOTSTRAP_REPLICATES

        ci = report["primary_refit_bootstrap"]["delta_auroc_ci95"]
        observed = float(report["primary_refit_bootstrap"]["delta_auroc_observed"])
        t03 = {
            "observed_delta_auroc": observed,
            "ci95": [float(ci[0]), float(ci[1])],
            "upper_95_percent_confidence_limit": float(ci[1]),
            "prespecified_detectable_magnitude": float(spec["detectable_delta_auroc"]),
            "wording_guardrail": "Report the upper 95% confidence limit; do not claim equivalence or that a benefit was ruled out.",
        }

        out["outcomes"][outcome_key] = {
            "n": int(len(y)),
            "cases": int(y.sum()),
            "t0_1": {
                "primary_repeat": repeats[0],
                "all_five_repeats": repeats,
                "five_partition_ranges": five_repeat_ranges(repeats),
                "conditional_patient_cluster_bootstrap": boot,
            },
            "t0_2_registered_decision_curve": report["decision_curve"],
            "t0_3_compatible_upper_limit": t03,
            "source_hashes": {
                "prediction_csv_sha256": sha256_file(pred_path),
                "registered_report_sha256": sha256_file(report_path),
            },
        }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    update_progress(
        current=total_progress,
        total=total_progress,
        phase="extension_t0_complete",
        message="Tier 0 aggregate analysis complete",
        unit="replicate",
    )
    print(json.dumps({
        "status": "completed",
        "output": str(output),
        "outcomes": list(out["outcomes"]),
        "bootstrap_replicates_per_outcome": BOOTSTRAP_REPLICATES,
    }, indent=2))


if __name__ == "__main__":
    main()
